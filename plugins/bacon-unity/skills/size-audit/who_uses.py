"""Who pulls an asset into the build: reverse GUID references (texture -> material -> prefab -> scene).

Usage:  py -I <path to>/who_uses.py <asset path or name substring> [...]   (run from the Unity project folder)
Part of the bacon-unity `/size-audit` skill.

Indexes every Unity YAML file under Assets once (guid -> files that reference it), then for each matching asset walks
the referencing files upwards (materials, prefabs, controllers, ScriptableObjects...) until it reaches a scene (`*`) or
a Resources folder (`*`). Text search only: it does not know whether the referencing GameObject is active, so a hit in
a scene still needs a look in Unity. Over 80 lines: the first 80 are printed, the whole tree goes to a temp file (path
printed). Written for the APK size audit (2026-10-27).
"""
import os
import re
import sys
import tempfile
import time
from collections import defaultdict

PRINT_CAP = 80  # stdout lines; a longer tree goes to a temp file

ROOT = 'Assets'
YAML_EXT = ('.unity', '.prefab', '.mat', '.asset', '.controller', '.overrideController', '.anim', '.spriteatlas',
            '.mask', '.playable', '.lighting', '.preset')
META_GUID = re.compile(r'^guid: ([0-9a-f]{32})', re.M)
REF_GUID = re.compile(rb'guid: ([0-9a-f]{32})')


def index():
    by_path, refs = {}, defaultdict(set)
    for d, _, files in os.walk(ROOT):
        for f in files:
            p = os.path.join(d, f)
            if f.endswith('.meta'):
                with open(p, encoding='utf-8', errors='ignore') as fh:
                    m = META_GUID.search(fh.read(2000))
                if m:
                    by_path[p[:-5].replace('\\', '/')] = m.group(1)
            elif f.endswith(YAML_EXT):
                with open(p, 'rb') as fh:
                    head = fh.read(16)
                    if not head.startswith(b'%YAML'):
                        continue  # binary-serialized asset (e.g. baked lighting data)
                    data = head + fh.read()
                for g in set(REF_GUID.findall(data)):
                    refs[g.decode()].add(p.replace('\\', '/'))
    return by_path, refs


def is_root(path):
    return path.endswith('.unity') or '/Resources/' in path


def walk(path, by_path, refs, out, depth=0, seen=None, max_depth=6):
    seen = seen if seen is not None else set()
    if path in seen or depth > max_depth:
        return
    seen.add(path)
    for ref in sorted(refs.get(by_path.get(path, ''), ())):
        if ref == path:
            continue
        out.append('  ' * (depth + 1) + ('* ' if is_root(ref) else '- ') + ref)
        if not ref.endswith('.unity'):
            walk(ref, by_path, refs, out, depth + 1, seen, max_depth)


def main():
    by_path, refs = index()
    lines = []
    for query in sys.argv[1:]:
        matches = [p for p in by_path if p == query or query.lower() in p.lower()]
        if not matches:
            lines.append('no asset matches ' + query)
        for m in matches[:10]:
            lines.append(m)
            walk(m, by_path, refs, lines)
    # a shared atlas / material can be referenced by hundreds of prefabs: keep the head here, the whole tree on disk
    print('\n'.join(lines[:PRINT_CAP]))
    if len(lines) > PRINT_CAP:
        full = os.path.join(tempfile.gettempdir(), 'who_uses_%d.txt' % int(time.time()))
        with open(full, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
        roots = sum(1 for l in lines if l.lstrip().startswith('* '))
        print('... %d lines (%d scene / Resources roots) -> %s' % (len(lines), roots, full))


if __name__ == '__main__':
    main()
