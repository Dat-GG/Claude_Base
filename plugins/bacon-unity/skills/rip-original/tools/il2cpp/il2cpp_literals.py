"""Where is a string literal used in an IL2CPP game, without Il2CppDumper (works on metadata v39 / Unity 6).

  py -I <tools>/il2cpp/il2cpp_literals.py extract  <game.xapk | game.apk> --out DIR      -> DIR/global-metadata.dat, DIR/libil2cpp.so
  py -I <tools>/il2cpp/il2cpp_literals.py literals DIR/global-metadata.dat --out DIR     -> DIR/literals.tsv (index \\t repr)
  py -I <tools>/il2cpp/il2cpp_literals.py xref     DIR/libil2cpp.so DIR/literals.tsv --out DIR   -> DIR/refs.tsv (code VA \\t literal index)
  py -I <tools>/il2cpp/il2cpp_literals.py find     DIR "rate_us|not_now" [--window 0x800]       -> each use + literals used nearby
                                                                       (first 40 printed, all in DIR/find_last.txt)
  py -I <tools>/il2cpp/il2cpp_literals.py near     DIR 0x1b9c000 [--window 0x800]                -> literals used around a code address

How: literal slots in the writable data sections encode (5<<29)|(index<<1)|1; R_AARCH64_RELATIVE relocations whose
addend is a slot give the GOT entry; ADRP + LDR pairs in executable sections that hit a GOT entry are the uses.
Literals used close together belong to the same function, which identifies it (analytics event, save key, UI text...).
Recovered and generalized from the BC36 / Highway Moto Rush 1.4.1 session (2026-09-25: `xref.py`, `litmap.py`), where it
proved that "rate_us" / "not_now" were analytics parameters. Section offsets now come from the ELF (pyelftools).
arm64 only. Needs numpy, pyelftools.
"""
import argparse
import bisect
import io
import os
import re
import struct
import sys
import zipfile

import numpy as np

FIND_CAP = 40  # uses printed by `find`; the rest go to DIR/find_last.txt

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def cmd_extract(a):
    os.makedirs(a.out, exist_ok=True)
    found = {}

    def scan(z, label):
        for n in z.namelist():
            if n.endswith(".apk"):
                scan(zipfile.ZipFile(io.BytesIO(z.read(n))), n)
            elif n.endswith("global-metadata.dat") or (n.endswith("libil2cpp.so") and "arm64" in n):
                key = os.path.basename(n)
                open(os.path.join(a.out, key), "wb").write(z.read(n))
                found[key] = f"{label}!{n}"

    scan(zipfile.ZipFile(a.src), os.path.basename(a.src))
    for k, v in found.items():
        print(f"{k} <- {v}")
    if len(found) < 2:
        sys.exit("missing metadata or arm64 libil2cpp.so (split apk not inside? pull it from the device: pm path)")


def read_literals(path):
    d = open(path, "rb").read()
    magic, ver = struct.unpack_from("<Ii", d, 0)
    if magic != 0xFAB11BAF:
        sys.exit(f"not IL2CPP metadata (magic {magic:#x})")
    if ver >= 38:  # header = (offset, size, count) triples
        lo, lsz, lc, do, dsz = struct.unpack_from("<5I", d, 8)
        idx = list(struct.unpack_from("<%dI" % lc, d, lo)) + [dsz]
        lits = [d[do + idx[i]:do + idx[i + 1]].decode("utf-8", "replace") for i in range(lc)]
    else:  # header = (offset, size) pairs; table entries (length, dataIndex)
        lo, lsz, do, dsz = struct.unpack_from("<4I", d, 8)
        lits = []
        for i in range(lsz // 8):
            L, di = struct.unpack_from("<II", d, lo + i * 8)
            lits.append(d[do + di:do + di + L].decode("utf-8", "replace"))
    return ver, lits


def cmd_literals(a):
    ver, lits = read_literals(a.metadata)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "literals.tsv"), "w", encoding="utf-8") as f:
        for i, s in enumerate(lits):
            f.write("%d\t%r\n" % (i, s))
    print(f"metadata v{ver}: {len(lits)} literals -> {os.path.join(a.out, 'literals.tsv')}")


def load_literals(path):
    lits = []
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if line:
            lits.append(line.split("\t", 1)[1])
    return lits


def adrp_pages(w, pcs):
    isadrp = (w & 0x9F000000) == 0x90000000
    immlo = (w >> 29) & 3
    immhi = (w >> 5) & 0x7FFFF
    imm = (immhi.astype(np.int64) << 2) | immlo
    imm = np.where(imm & (1 << 20), imm - (1 << 21), imm)
    return isadrp, (pcs & ~0xFFF) + (imm << 12)


def cmd_xref(a):
    from elftools.elf.elffile import ELFFile
    from elftools.elf.constants import SH_FLAGS
    d = open(a.so, "rb").read()
    lits = load_literals(a.literals)
    elf = ELFFile(open(a.so, "rb"))
    code, data, rela = [], [], []
    for s in elf.iter_sections():
        if s["sh_size"] == 0 or s["sh_type"] == "SHT_NOBITS":
            continue
        fl = s["sh_flags"]
        if fl & SH_FLAGS.SHF_EXECINSTR:
            code.append((s["sh_offset"], s["sh_size"], s["sh_addr"], s.name))
        elif fl & SH_FLAGS.SHF_WRITE and s["sh_type"] == "SHT_PROGBITS":
            data.append((s["sh_offset"], s["sh_size"], s["sh_addr"], s.name))
        if s["sh_type"] == "SHT_RELA":
            rela.append((s["sh_offset"], s["sh_size"], s.name))
    print("code:", [c[3] for c in code], "data:", [x[3] for x in data], "rela:", [r[2] for r in rela])

    slots = {}
    for off, size, addr, _ in data:
        q = np.frombuffer(d, dtype="<u8", count=size // 8, offset=off)
        m = ((q >> np.uint64(29)) == 5) & ((q & np.uint64(1)) == 1)
        for i in np.nonzero(m)[0]:
            li = int((q[i] & np.uint64(0x1FFFFFFE)) >> np.uint64(1))
            if li < len(lits):
                slots[addr + int(i) * 8] = li
    got = {}
    keys = np.array(list(slots.keys()), dtype=np.uint64)
    for off, size, _ in rela:
        r = np.frombuffer(d, dtype="<u8", count=size // 24 * 3, offset=off).reshape(-1, 3)
        for i in np.nonzero(np.isin(r[:, 2], keys))[0]:
            got[int(r[i, 0])] = slots[int(r[i, 2])]
    pages = np.array(sorted({g & ~0xFFF for g in got}), dtype=np.int64)
    refs = []
    for off, size, addr, _ in code:
        w = np.frombuffer(d, dtype="<u4", count=size // 4, offset=off)
        pcs = addr + np.arange(len(w), dtype=np.int64) * 4
        isadrp, page = adrp_pages(w, pcs)
        for i in np.nonzero(isadrp & np.isin(page, pages))[0]:
            rd, pg = int(w[i] & 31), int(page[i])
            for j in range(1, 12):
                if i + j >= len(w):
                    break
                ins = int(w[i + j])
                if (ins & 0xFFC00000) == 0xF9400000 and ((ins >> 5) & 31) == rd:  # LDR Xt, [Xn, #imm]
                    ga = pg + ((ins >> 10) & 0xFFF) * 8
                    if ga in got:
                        refs.append((int(pcs[i]), got[ga]))
                    break
    refs.sort()
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "refs.tsv"), "w", encoding="utf-8") as f:
        for pc, li in refs:
            f.write("%#x\t%d\n" % (pc, li))
    print(f"slots {len(slots)}, got {len(got)}, uses {len(refs)} -> {os.path.join(a.out, 'refs.tsv')}")


def load_refs(dirp):
    refs = []
    for line in open(os.path.join(dirp, "refs.tsv"), encoding="utf-8"):
        pc, li = line.split("\t")
        refs.append((int(pc, 16), int(li)))
    return refs


def neighbours(refs, pcs, lits, pc, window):
    lo, hi = bisect.bisect_left(pcs, pc - window), bisect.bisect_right(pcs, pc + window)
    return sorted({lits[refs[k][1]][:70] for k in range(lo, hi)})


def cmd_find(a):
    try:
        rx = re.compile(a.regex, re.I)
    except re.error as ex:
        print(f"error: invalid regex {a.regex!r}: {ex}", file=sys.stderr)
        sys.exit(2)
    lits = load_literals(os.path.join(a.dir, "literals.tsv"))
    refs = load_refs(a.dir)
    pcs = [r[0] for r in refs]
    want = {i for i, s in enumerate(lits) if rx.search(s)}
    uses = [f"{pc:#x}  {lits[li][:60]}\n    near: {neighbours(refs, pcs, lits, pc, a.window)}" for pc, li in refs if li in want]
    print(f"{len(want)} literals match; {len(uses)} uses:")
    for u in uses[:FIND_CAP]:
        print(u)
    if len(uses) > FIND_CAP:
        # a broad regex can match thousands of uses: keep the context small, the full list on disk
        full = os.path.join(a.dir, "find_last.txt")
        with open(full, "w", encoding="utf-8") as f:
            f.write("\n".join(uses) + "\n")
        print(f"... {len(uses) - FIND_CAP} more uses -> {full} (narrow the regex or grep that file)")
    unused = [lits[i][:60] for i in sorted(want) if i not in {r[1] for r in refs}]
    if unused:
        print("matching literals with no code use found:", unused[:30])


def cmd_near(a):
    lits = load_literals(os.path.join(a.dir, "literals.tsv"))
    refs = load_refs(a.dir)
    pcs = [r[0] for r in refs]
    print(neighbours(refs, pcs, lits, int(a.addr, 16), a.window))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("extract"); s.add_argument("src"); s.add_argument("--out", required=True); s.set_defaults(fn=cmd_extract)
    s = sub.add_parser("literals"); s.add_argument("metadata"); s.add_argument("--out", required=True); s.set_defaults(fn=cmd_literals)
    s = sub.add_parser("xref"); s.add_argument("so"); s.add_argument("literals"); s.add_argument("--out", required=True); s.set_defaults(fn=cmd_xref)
    s = sub.add_parser("find"); s.add_argument("dir"); s.add_argument("regex"); s.add_argument("--window", type=lambda x: int(x, 0), default=0x800); s.set_defaults(fn=cmd_find)
    s = sub.add_parser("near"); s.add_argument("dir"); s.add_argument("addr"); s.add_argument("--window", type=lambda x: int(x, 0), default=0x800); s.set_defaults(fn=cmd_near)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
