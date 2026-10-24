r"""Remap MonoBehaviour script references of ripped Unity YAML files (scene / prefab / asset) to the real scripts of the target project.

The rip references third-party code either through ripped DLLs ({fileID: <md4 id>, guid: <dll guid>}) or through ripped .cs files
({fileID: 11500000, guid: <cs guid>}). In the target project the same classes exist as .cs files of real packages / packs
(UGUI, TMP, Cinemachine, Animation Rigging, RCC Pro, Joystick Pack, Easy Minimap...) or as DLLs (DOTween).
Mapping key = namespace + class name. DLL fileIDs are MD4("s\0\0\0" + namespace + name)[0:4] as little-endian int32 (Unity rule).

Usage  : py -I <tools>/unity/rip_remap.py --rip <rip Assets> --target <target project root> [--dry] FILE...
         FILE = scene / prefab / asset YAML copied from the rip into the target project (edited in place).
Inputs : rip Assets (DLL .meta under RIP_DLL_DIRS, .cs + .meta under RIP_CS_DIRS), target Assets + Library/PackageCache.
Outputs: FILE rewritten in place (skipped with --dry); stdout per file "mapped N, unmapped M" + per class / dll ok / miss.
Proven : BC54 (Urban Food Delivery rebuild) 2026-10-16: restored 1,887 / 3,261 script refs in 2_Gameplay.unity (rest = game
         scripts, replaced by our code); also run on prefabs / SOs.
Origin : <projects>/Urban_Food_Ripped/Tools/rip_remap.py (copied 2026-10-22; rip sub-folders made constants).
"""
import argparse
import os
import re
import struct
import sys

# ---- PROJECT CONSTANTS: rip sub-folders (AssetRipper "Export Unity project" layout), relative to --rip ----
RIP_DLL_DIRS = ["Plugins"]                 # ripped DLL assemblies (+ .meta)
RIP_CS_DIRS = ["Scripts", "Plugins"]       # ripped .cs scripts (+ .meta)

# ---------------- MD4 (hashlib.md4 is often unavailable) ----------------
def _md4(data: bytes) -> bytes:
    def f(x, y, z): return (x & y) | (~x & z)
    def g(x, y, z): return (x & y) | (x & z) | (y & z)
    def h(x, y, z): return x ^ y ^ z
    def rol(v, s): v &= 0xFFFFFFFF; return ((v << s) | (v >> (32 - s))) & 0xFFFFFFFF
    msg = bytearray(data)
    ml = (8 * len(data)) & 0xFFFFFFFFFFFFFFFF
    msg.append(0x80)
    while len(msg) % 64 != 56:
        msg.append(0)
    msg += struct.pack("<Q", ml)
    a, b, c, d = 0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476
    for off in range(0, len(msg), 64):
        X = list(struct.unpack("<16I", msg[off:off + 64]))
        aa, bb, cc, dd = a, b, c, d
        for i in (0, 4, 8, 12):
            a = rol(a + f(b, c, d) + X[i], 3); d = rol(d + f(a, b, c) + X[i + 1], 7)
            c = rol(c + f(d, a, b) + X[i + 2], 11); b = rol(b + f(c, d, a) + X[i + 3], 19)
        for i in (0, 1, 2, 3):
            a = rol(a + g(b, c, d) + X[i] + 0x5A827999, 3); d = rol(d + g(a, b, c) + X[i + 4] + 0x5A827999, 5)
            c = rol(c + g(d, a, b) + X[i + 8] + 0x5A827999, 9); b = rol(b + g(c, d, a) + X[i + 12] + 0x5A827999, 13)
        for i in (0, 2, 1, 3):
            a = rol(a + h(b, c, d) + X[i] + 0x6ED9EBA1, 3); d = rol(d + h(a, b, c) + X[i + 8] + 0x6ED9EBA1, 9)
            c = rol(c + h(d, a, b) + X[i + 4] + 0x6ED9EBA1, 11); b = rol(b + h(c, d, a) + X[i + 12] + 0x6ED9EBA1, 15)
        a = (a + aa) & 0xFFFFFFFF; b = (b + bb) & 0xFFFFFFFF; c = (c + cc) & 0xFFFFFFFF; d = (d + dd) & 0xFFFFFFFF
    return struct.pack("<4I", a, b, c, d)


def script_file_id(namespace: str, name: str) -> int:
    return struct.unpack("<i", _md4(("s\0\0\0" + namespace + name).encode("utf-8"))[:4])[0]


# ---------------- indexing ----------------
NS_RE = re.compile(r"^\s*namespace\s+([A-Za-z0-9_.]+)", re.M)


def read_guid(meta_path):
    try:
        with open(meta_path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if line.startswith("guid:"):
                    return line.split()[1]
    except OSError:
        pass
    return None


def cs_namespace(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            m = NS_RE.search(fh.read())
            return m.group(1) if m else ""
    except OSError:
        return ""


def index_cs(roots):
    """(namespace, class) -> guid for every .cs (class = file name, Unity's MonoScript rule)."""
    idx = {}
    for root in roots:
        for dp, _, files in os.walk(root):
            for fn in files:
                if not fn.endswith(".cs"):
                    continue
                guid = read_guid(os.path.join(dp, fn + ".meta"))
                if guid:
                    idx.setdefault((cs_namespace(os.path.join(dp, fn)), fn[:-3]), guid)
    return idx


def index_dlls(roots):
    """dll file name -> guid."""
    idx = {}
    for root in roots:
        for dp, _, files in os.walk(root):
            for fn in files:
                if fn.endswith(".dll"):
                    guid = read_guid(os.path.join(dp, fn + ".meta"))
                    if guid:
                        idx[fn] = guid
    return idx


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rip", required=True)
    ap.add_argument("--target", required=True)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()

    target_assets = os.path.join(a.target, "Assets")
    pkg_cache = os.path.join(a.target, "Library", "PackageCache")
    tgt_cs = index_cs([target_assets, pkg_cache])
    tgt_dll = index_dlls([target_assets])
    by_fileid = {script_file_id(ns, cls): (ns, cls) for (ns, cls) in tgt_cs}

    # rip side: dll guid -> dll name; cs guid -> (namespace, class)
    rip_dll = {g: n for n, g in index_dlls([os.path.join(a.rip, d) for d in RIP_DLL_DIRS]).items()}
    rip_cs = {g: k for k, g in index_cs([os.path.join(a.rip, d) for d in RIP_CS_DIRS]).items()}

    ref_re = re.compile(r"m_Script: \{fileID: (-?\d+), guid: ([0-9a-f]{32}), type: 3\}")
    for path in a.files:
        with open(path, encoding="utf-8", errors="replace", newline="") as fh:
            text = fh.read()
        stats = {}

        def repl(m):
            fid, guid = int(m.group(1)), m.group(2)
            new = None
            if guid in rip_dll:
                dll = rip_dll[guid]
                if dll in tgt_dll:                       # same DLL in target (DOTween): fileID stays valid
                    new = (fid, tgt_dll[dll])
                elif fid in by_fileid:                   # DLL class -> package .cs
                    new = (11500000, tgt_cs[by_fileid[fid]])
                key = dll
            elif guid in rip_cs:
                ns, cls = rip_cs[guid]
                if (ns, cls) in tgt_cs:
                    new = (11500000, tgt_cs[(ns, cls)])
                key = (ns + "." if ns else "") + cls
            else:
                return m.group(0)
            stats.setdefault(key, [0, 0])[0 if new else 1] += 1
            if not new:
                return m.group(0)
            return "m_Script: {fileID: %d, guid: %s, type: 3}" % new

        out = ref_re.sub(repl, text)
        mapped = sum(v[0] for v in stats.values())
        left = sum(v[1] for v in stats.values())
        print("%s: mapped %d, unmapped %d" % (os.path.basename(path), mapped, left))
        for k, (ok, ko) in sorted(stats.items(), key=lambda kv: -sum(kv[1])):
            if ko and not ok:
                continue
            print("   %-60s ok %d miss %d" % (k, ok, ko))
        if not a.dry and out != text:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(out)


if __name__ == "__main__":
    sys.exit(main())
