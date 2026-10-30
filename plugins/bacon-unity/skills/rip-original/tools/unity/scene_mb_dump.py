r"""Dump the serialized data of the original game's MonoBehaviours (scripts missing in the target project) under given
GameObjects of a ripped Unity scene. Reference only: used to read mission / order / UI values from GamePlay.unity.

Usage  : py -I <tools>/unity/scene_mb_dump.py --scene <scene.unity> --scripts <rip Assets/Scripts/Assembly-CSharp>
           [--depth N] [--out FILE] ROOT_PATH...
ROOT_PATH = GameObject path from a scene root, e.g. "****MISSIONS****/Mission 2" or "Canvas/Mobile Open".
Inputs : a ripped scene (text YAML), the rip's script folder (script GUID -> class name via the .cs.meta files).
Outputs: stdout, per GameObject (depth-first): path, components, and for every game-script MonoBehaviour its class + YAML
         fields; "!! not found: <path>" on stderr for a wrong ROOT_PATH. Over 150 lines (or with --out): the whole dump
         goes to the file (temp folder by default), stdout keeps the first 150 lines + the path.
Proven : UFD -> BC54 2026-10-16 (GamePlay.unity missions / orders / UI values).
Origin : <projects>/Urban_Food_Ripped/Tools/scene_mb_dump.py (copied 2026-10-22; 2026-10-30: output cap + --out added).
"""
import argparse
import os
import re
import sys
import tempfile
import time

PRINT_CAP = 150  # stdout lines; a longer dump goes to --out or a temp file

DOC_RE = re.compile(r"^--- !u!(\d+) &(-?\d+)", re.M)
FILEID_RE = re.compile(r"\{fileID: (-?\d+)")


def load_docs(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    docs = {}
    matches = list(DOC_RE.finditer(text))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        docs[m.group(2)] = (int(m.group(1)), text[m.end():end])
    return docs


def field(body, name):
    m = re.search(r"^\s*" + re.escape(name) + r": ?(.*)$", body, re.M)
    return m.group(1).strip() if m else None


def script_classes(scripts_root):
    out = {}
    for dirpath, _, files in os.walk(scripts_root):
        for f in files:
            if f.endswith(".cs.meta"):
                with open(os.path.join(dirpath, f), encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        if line.startswith("guid:"):
                            out[line.split()[1]] = f[:-8]
                            break
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scene", required=True)
    ap.add_argument("--scripts", required=True)
    ap.add_argument("--depth", type=int, default=99)
    ap.add_argument("--out", help="write the whole dump here (stdout gets only the summary line)")
    ap.add_argument("roots", nargs="+")
    a = ap.parse_args()

    docs = load_docs(a.scene)
    classes = script_classes(a.scripts)

    go_name, go_comps, tr_of_go, tr_children, tr_go = {}, {}, {}, {}, {}
    for fid, (cls, body) in docs.items():
        if cls == 1:  # GameObject
            name = field(body, "m_Name") or ""
            if len(name) >= 2 and name[0] == name[-1] and name[0] in "'\"":
                name = name[1:-1].replace("''", "'")  # YAML quotes names starting with * [ etc.
            go_name[fid] = name
            go_comps[fid] = re.findall(r"component: \{fileID: (-?\d+)\}", body)
        elif cls in (4, 224):  # Transform / RectTransform
            g = FILEID_RE.search(field(body, "m_GameObject") or "")
            if g:
                tr_of_go[g.group(1)] = fid
                tr_go[fid] = g.group(1)
            ch = body.split("m_Children:", 1)[1].split("m_Father", 1)[0] if "m_Children:" in body else ""
            tr_children[fid] = FILEID_RE.findall(ch)

    roots = [fid for fid, (cls, body) in docs.items() if cls in (4, 224) and "m_Father: {fileID: 0}" in body]

    def find(path):
        parts = path.split("/")
        level = roots
        cur = None
        for p in parts:
            cur = next((t for t in level if go_name.get(tr_go.get(t)) == p), None)
            if cur is None:
                return None
            level = tr_children.get(cur, [])
        return cur

    lines = []
    emit = lines.append

    def dump(tr, path, depth):
        go = tr_go[tr]
        names = []
        for c in go_comps.get(go, []):
            cls, body = docs.get(c, (None, ""))
            if cls == 114:
                guid = re.search(r"m_Script: \{fileID: -?\d+, guid: ([0-9a-f]+)", body)
                g = guid.group(1) if guid else "?"
                names.append(classes.get(g, "mb:" + g[:8]))
            else:
                names.append(str(cls))
        emit(f"\n## {path}  (go {go}, active {field(docs[go][1], 'm_IsActive')})  [{', '.join(names)}]")
        for c in go_comps.get(go, []):
            cls, body = docs.get(c, (None, ""))
            if cls != 114:
                continue
            guid = re.search(r"m_Script: \{fileID: -?\d+, guid: ([0-9a-f]+)", body)
            g = guid.group(1) if guid else "?"
            if g not in classes:
                continue
            emit(f"  -- {classes[g]} (&{c})")
            started = False
            for line in body.splitlines():
                if line.strip().startswith("m_EditorClassIdentifier"):
                    started = True
                    continue
                if started:
                    emit("   " + line)
        if depth <= 0:
            return
        for ch in tr_children.get(tr, []):
            if ch in tr_go:
                dump(ch, path + "/" + go_name.get(tr_go[ch], "?"), depth - 1)

    for r in a.roots:
        tr = find(r)
        if tr is None:
            print(f"!! not found: {r}", file=sys.stderr)
            continue
        dump(tr, r, a.depth)

    text = "\n".join(lines) + "\n"
    n = text.count("\n")
    if a.out or n > PRINT_CAP:
        # a whole subtree with every field easily runs to thousands of lines: full dump to a file, head on stdout
        out = a.out or os.path.join(tempfile.gettempdir(), f"scene_mb_dump_{int(time.time())}.txt")
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text)
        if not a.out:
            print("\n".join(text.splitlines()[:PRINT_CAP]))
        print(f"... {n} lines, {sum(1 for l in lines if l.startswith(chr(10) + '## '))} GameObjects -> {out}")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
