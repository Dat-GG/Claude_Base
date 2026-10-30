"""detect_engine.py - identify the engine / backend of an Android game build without extracting it.

Purpose : first step of /rip-original: which engine, which version, encrypted or not, which reference to read next.
Usage   : py -I <tools>/detect_engine.py <game.apk | game.xapk | game.apks | folder> [--json]
          folder = an extracted apk, a folder holding base.apk + split_config.*.apk, or a flat folder with
          libil2cpp.so + global-metadata.dat (output of `il2cpp_literals.py extract`)
Inputs  : apk / xapk / apks (nested zips are read in place, nothing is written), or loose folders.
Output  : engine, evidence, versions, ABIs, biggest native libs, asset file types, next step (stdout; --json for machines).
Proven  : 2026-10-22 on E2D 2 (native), UFD / HMR / Fish Sort (IL2CPP), our own Unity builds (see tools/README.md).
"""
import io
import json
import os
import re
import struct
import sys
import zipfile
from collections import Counter

UNITY_VER_RE = re.compile(rb'(?<![\d.])((?:20\d\d|6000)\.\d{1,2}\.\d{1,3}[abfpx]\d{1,3})')
OBFUSCATOR_MARKS = [b'ConfusedByAttribute', b'BeeByte', b'Beebyte', b'ObfuscatedByGoliath', b'DotfuscatorAttribute',
                    b'Obfuscar', b'BabelObfuscatorAttribute', b'SmartAssembly', b'CodeGuard', b'Obfuscator']

REFS = {
    'unity-il2cpp': 'references/engine-il2cpp.md',
    'unity-mono': 'references/engine-il2cpp.md (section "Mono builds")',
    'cocos-js': 'references/engine-js.md',
    'cocos-lua': 'not in the playbook yet: decrypt (XXTEA key from the .so) + unluac / luajit-decompiler; then /add-lesson',
    'cocos2dx-cpp': 'references/engine-native-cpp.md',
    'native-cpp': 'references/engine-native-cpp.md',
    'godot': 'not in the playbook yet: GDRE Tools (gdsdecomp) recovers the project; ask the user before installing',
    'unreal': 'not in the playbook yet: FModel / UE Viewer for .pak assets, Ghidra for libUnreal.so; ask before installing',
    'flutter': 'not in the playbook yet: Dart AOT (libapp.so) -> blutter; assets are plain in flutter_assets/',
    'gamemaker': 'not in the playbook yet: UndertaleModTool on game.droid (YYC builds = native code -> Ghidra)',
    'defold': 'not in the playbook yet: game.arcd / game.arci archives; Lua sources are inside',
    'solar2d': 'not in the playbook yet: resource.car (Lua bytecode)',
    'adobe-air': 'not in the playbook yet: JPEXS decompiles the .swf (ActionScript)',
    'html5': 'plain JS / HTML in assets/www or assets/public: read it directly (references/engine-js.md for carving)',
    'react-native': 'not in the playbook yet: index.android.bundle (Hermes bytecode -> hermes-dec, else plain JS)',
    'xamarin': 'managed .NET: same as Unity Mono (ILSpy) once the assemblies are unpacked from assemblies.blob',
    'android-java': 'references/engine-js.md (custom containers); Java / Kotlin code -> jadx (not installed: ask)',
}


class Source:
    """Flat view over every file in the build: entries (container label, path, size) + read()."""

    def __init__(self, path):
        self.entries = []        # (container, member path, size)
        self._readers = {}       # container -> callable(member, n) -> bytes
        self._zips = []
        if os.path.isdir(path):
            self._add_dir(path)
        else:
            self._add_zip(os.path.basename(path), zipfile.ZipFile(path))

    def _add_zip(self, label, zf):
        self._zips.append(zf)
        inner = []
        for info in zf.infolist():
            if info.is_dir():
                continue
            low = info.filename.lower()
            if low.endswith('.apk') and '/' not in info.filename.strip('/'):
                inner.append(info)       # xapk / apks: split apks at the root
            else:
                self.entries.append((label, info.filename, info.file_size))
        self._readers[label] = lambda m, n, zf=zf: _zip_read(zf, m, n)
        for info in inner:
            # stored apks seek cheaply; deflated ones are loaded once into memory
            f = zf.open(info) if info.compress_type == zipfile.ZIP_STORED else io.BytesIO(zf.read(info))
            self._add_zip(info.filename, zipfile.ZipFile(f))

    def _add_dir(self, root):
        for d, _, files in os.walk(root):
            for name in files:
                full = os.path.join(d, name)
                if name.lower().endswith(('.apk', '.xapk', '.apks')):
                    self._add_zip(os.path.relpath(full, root), zipfile.ZipFile(full))
                    continue
                rel = os.path.relpath(full, root).replace('\\', '/')
                self.entries.append(('<dir>', rel, os.path.getsize(full)))
        self._readers['<dir>'] = lambda m, n, root=root: _file_read(os.path.join(root, m), n)

    def read(self, entry, n=None):
        container, member, _ = entry
        return self._readers[container](member, n)

    def find(self, pattern):
        rx = re.compile(pattern, re.I)
        return [e for e in self.entries if rx.search(e[1])]


def _zip_read(zf, member, n):
    with zf.open(member) as f:
        return f.read() if n is None else f.read(n)


def _file_read(path, n):
    with open(path, 'rb') as f:
        return f.read() if n is None else f.read(n)


def libname(entry):
    return entry[1].rsplit('/', 1)[-1].lower()


def ascii_preview(data):
    return ''.join(chr(b) if 32 <= b < 127 else '.' for b in data)


def has_mono_dlls(src):
    return bool(src.find(r'assets/bin/data/managed/assembly-csharp\.dll$'))


def detect(src):
    r = {'engines': [], 'evidence': [], 'details': {}, 'warnings': []}
    libs = src.find(r'^lib/[^/]+/[^/]+\.so$')
    libnames = {libname(e) for e in libs}
    abis = sorted({e[1].split('/')[1] for e in libs})
    r['details']['abis'] = abis
    # language / density splits carry no code
    r['details']['containers'] = sorted({e[0] for e in src.entries
                                         if not re.match(r'(split_)?config\.([a-z]{2}|[a-z]*dpi)\.apk$', e[0])})
    if abis and 'arm64-v8a' not in abis and not has_mono_dlls(src):
        r['warnings'].append('no arm64-v8a libs: tools here assume arm64 (capstone mode, il2cpp_literals.py); '
                              'armv7: engine-il2cpp.md > Lua-scripted Unity > 3')

    def has(*names):
        return [n for n in names if n in libnames]

    def add(engine, why):
        if engine not in r['engines']:
            r['engines'].append(engine)
        r['evidence'].append(why)

    # ---- Unity
    unity_data = src.find(r'^assets/bin/data/')
    # by file name anywhere too: flat folders (il2cpp_literals.py extract output, hand-pulled files)
    il2cpp_any = src.find(r'(^|/)libil2cpp\.so$')
    meta_any = src.find(r'(^|/)global-metadata\.dat$')
    if has('libunity.so') or unity_data or (il2cpp_any and meta_any):
        meta = src.find(r'assets/bin/data/managed/metadata/global-metadata\.dat$') or meta_any
        dlls = src.find(r'assets/bin/data/managed/[^/]+\.dll$')
        if has('libil2cpp.so') or il2cpp_any or meta:
            first = 'libunity.so' if has('libunity.so') else 'Unity data' if unity_data else 'loose files'
            add('unity-il2cpp', first + ' + ' + ('libil2cpp.so' if (has('libil2cpp.so') or il2cpp_any)
                                                  else 'global-metadata.dat')
                + (' + global-metadata.dat' if meta and (has('libil2cpp.so') or il2cpp_any) else ''))
            if meta:
                head = src.read(meta[0], 8)
                magic, ver = struct.unpack('<II', head)
                if magic == 0xFAB11BAF:
                    r['details']['il2cpp_metadata_version'] = ver
                else:
                    r['warnings'].append('global-metadata.dat magic is %s, not af1bb1fa: encrypted / custom metadata'
                                         % head[:4].hex())
            else:
                r['warnings'].append('libil2cpp.so but no global-metadata.dat in assets: metadata may be embedded / renamed')
        elif dlls or has('libmonobdwgc-2.0.so', 'libmono.so'):
            add('unity-mono', 'libunity.so + Managed/*.dll (no libil2cpp.so)')
            r['details']['managed_dlls'] = sorted('%s (%d KB)' % (e[1].rsplit('/', 1)[-1], e[2] // 1024)
                                                  for e in dlls if e[1].lower().rsplit('/', 1)[-1].startswith('assembly-'))
            for e in dlls:
                if e[1].lower().endswith('/assembly-csharp.dll'):
                    data = src.read(e)
                    marks = sorted({m.decode() for m in OBFUSCATOR_MARKS if m in data})
                    if marks:
                        r['warnings'].append('Assembly-CSharp.dll contains obfuscator markers: ' + ', '.join(marks))
                    if not data.startswith(b'MZ'):
                        r['warnings'].append('Assembly-CSharp.dll does not start with MZ: encrypted, needs the loader key')
        else:
            add('unity-il2cpp', 'libunity.so (backend libs not found in this file: check the arm64 split apk)')
        lua = has('libtolua.so', 'libxlua.so', 'libslua.so', 'libulua.so')
        if lua:
            r['warnings'].append('Lua-scripted Unity (%s): gameplay is Lua in bundles / TextAssets -> '
                                 'engine-il2cpp.md > Lua-scripted Unity' % ', '.join(lua))
        ver = None
        for pat in (r'assets/bin/data/globalgamemanagers$', r'assets/bin/data/data\.unity3d$',
                    r'assets/bin/data/level0$', r'assets/bin/data/unity default resources$'):
            for e in src.find(pat):
                m = UNITY_VER_RE.search(src.read(e, 1 << 16))
                if m:
                    ver = m.group(1).decode()
                    break
            if ver:
                break
        if ver:
            r['details']['unity_version'] = ver
        extra = []
        if src.find(r'assets/aa/(catalog\.json|catalog\.bin|settings\.json)$'):
            extra.append('Addressables (assets/aa)')
        if src.find(r'assets/yoo/'):
            extra.append('YooAsset (assets/yoo)')
        if src.find(r'assets/bin/data/data\.unity3d$'):
            extra.append('compressed data.unity3d')
        packs = {e[0] for e in src.entries if e[1].lower().startswith('assets/aa/')}
        base = {e[0] for e in unity_data}
        if packs - base:
            extra.append('Addressables in asset-pack apks: ' + ', '.join(sorted(packs - base)))
        if extra:
            r['details']['unity_content'] = extra

    # ---- Cocos family
    cocos_js = has('libcocos2djs.so', 'libcocos.so')
    cocos_lua = has('libcocos2dlua.so')
    # not libgame.so: Unity 6 builds ship one too (GameActivity)
    cocos_cpp = has('libcocos2dcpp.so') if not cocos_js and not cocos_lua else []
    luas = src.find(r'^assets/.*\.(lua|luac)$')
    jscs = src.find(r'^assets/.*\.jsc$')
    creator = src.find(r'^assets/(main\.js|project\.json|settings\.js|src/settings\.js|jsb-adapter/)')
    if cocos_lua or luas:
        add('cocos-lua', ' + '.join(cocos_lua + (['%d .lua/.luac files' % len(luas)] if luas else [])))
        if luas:
            head = src.read(luas[0], 16)
            kind = ('Lua bytecode' if head.startswith(b'\x1bLua') else 'LuaJIT bytecode' if head.startswith(b'\x1bLJ')
                    else 'plain Lua source' if all(9 <= b < 127 for b in head) else 'encrypted (custom header)')
            r['details']['lua_files'] = '%s; first bytes "%s" (%s)' % (kind, ascii_preview(head), luas[0][1])
    if cocos_js or jscs or creator:
        add('cocos-js', ' + '.join(cocos_js + (['%d .jsc (encrypted JS)' % len(jscs)] if jscs else [])
                                   + (['Creator files (%s)' % creator[0][1]] if creator else [])))
    if cocos_cpp and 'cocos-js' not in r['engines'] and 'cocos-lua' not in r['engines']:
        lib = [e for e in libs if libname(e) in cocos_cpp][0]
        data = src.read(lib)
        jsb, lua = data.count(b'jsb_'), data.count(b'lua_pushstring')
        if jsb > 20:
            add('cocos-js', '%s with %d jsb_ strings (JS binding)' % (lib[1], jsb))
            if src.find(r'^assets/.*\.dat$'):
                r['details']['cocos_note'] = 'encrypted assets/**.dat: carve from RAM (engine-js.md entry 3)'
        elif lua > 0:
            add('cocos-lua', '%s with Lua API strings' % lib[1])
        else:
            add('cocos2dx-cpp', '%s, no JS / Lua binding: game logic is C++' % lib[1])

    # ---- other engines
    if has('libgodot_android.so') or src.find(r'^assets/.*\.pck$') or src.find(r'^assets/project\.binary$'):
        add('godot', 'libgodot_android.so / .pck / project.binary')
        for e in src.find(r'^assets/.*\.pck$')[:1]:
            h = src.read(e, 24)
            if h[:4] == b'GDPC':
                fmt, major, minor, patch = struct.unpack('<4I', h[4:20])
                r['details']['godot'] = 'pck format %d, Godot %d.%d.%d' % (fmt, major, minor, patch)
        if src.find(r'\.gde$'):
            r['warnings'].append('.gde files: encrypted GDScript (key is in the engine .so)')
    if has('libue4.so', 'libunreal.so') or src.find(r'\.pak$') or src.find(r'^main\.\d+\..*\.obb$'):
        add('unreal', ', '.join(has('libue4.so', 'libunreal.so')) or '.pak files')
    if has('libflutter.so'):
        add('flutter', 'libflutter.so' + (' + libapp.so (Dart AOT)' if has('libapp.so') else ''))
    if has('libyoyo.so') or src.find(r'^assets/game\.droid$'):
        add('gamemaker', 'libyoyo.so / game.droid')
    if has('libdmengine.so') or src.find(r'game\.arcd$'):
        add('defold', 'libdmengine.so / game.arcd')
    if has('libcorona.so') or src.find(r'resource\.car$'):
        add('solar2d', 'libcorona.so / resource.car')
    if src.find(r'^assets/.*\.swf$') and has('libcore.so'):
        add('adobe-air', 'libCore.so + .swf')
    if src.find(r'^assets/index\.android\.bundle$'):
        add('react-native', 'assets/index.android.bundle')
        e = src.find(r'^assets/index\.android\.bundle$')[0]
        if src.read(e, 8) == bytes.fromhex('c61fbc03c103191f'):
            r['details']['react_native'] = 'Hermes bytecode'
    if has('libmonodroid.so', 'libmonosgen-2.0.so') and 'unity-mono' not in r['engines']:
        add('xamarin', 'libmonodroid.so (Xamarin / .NET MAUI)')
    if src.find(r'^assets/(www|public)/index\.html$') and not r['engines']:
        add('html5', 'assets/www|public/index.html (Cordova / Capacitor / WebView)')

    # ---- biggest native libs (the game code when nothing above matched)
    big = sorted(libs, key=lambda e: -e[2])
    seen, top = set(), []
    for e in big:
        if libname(e) not in seen:
            seen.add(libname(e))
            top.append('%s %.1f MB' % (e[1], e[2] / 1048576))
        if len(top) == 4:
            break
    r['details']['biggest_libs'] = top
    if not r['engines']:
        game = [e for e in big if e[2] > 2 << 20]
        if game:
            data = src.read(game[0])
            rtti = len(set(re.findall(rb'_ZTS\d+[A-Za-z_]\w*', data)))
            hints = [name for mark, name in ((b'b2World', 'Box2D'), (b'btDiscreteDynamicsWorld', 'Bullet'),
                                             (b'cocos2d', 'cocos2d symbols'), (b'SDL_', 'SDL')) if mark in data]
            add('native-cpp', '%s (%.1f MB), %d RTTI type names%s' % (
                game[0][1], game[0][2] / 1048576, rtti, (', ' + ', '.join(hints)) if hints else ''))
            if rtti < 30:
                r['warnings'].append('few RTTI names: stripped binary, Ghidra output will be mostly FUN_xxx')
        elif src.find(r'(^|/)classes\d*\.dex$'):
            add('android-java', 'only dex code, no big native lib')

    # ---- asset hints
    ext = Counter()
    for e in src.entries:
        p = e[1].lower()
        if p.startswith('assets/') and not p.startswith('assets/bin/data/') and '.' in p.rsplit('/', 1)[-1]:
            ext[p.rsplit('.', 1)[-1]] += 1
    r['details']['asset_types'] = ', '.join('%s %d' % kv for kv in ext.most_common(10))
    spine = [k for k in ('skel', 'atlas') if ext.get(k)]
    if spine:
        r['details']['spine_hint'] = 'loose .skel / .atlas files: Spine data (references/assets.md)'
    r['next'] = [REFS[e] for e in r['engines']] or ['unknown: run SKILL.md step 1 by hand and /add-lesson the result']
    return r


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # non-ASCII file names under `py -I` (HTDT 2026-10-29)
    except AttributeError:
        pass
    if any(a in ('-h', '--help') for a in sys.argv[1:]):
        print(__doc__)
        return
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) != 1:
        print(__doc__)
        sys.exit(2)
    path = args[0]
    if not os.path.exists(path):
        print('error: %s: no such file or folder' % path, file=sys.stderr)
        sys.exit(2)
    try:
        src = Source(path)
    except zipfile.BadZipFile as ex:
        print('error: %s: not an apk / xapk / apks (zip) file or folder (%s)' % (path, ex), file=sys.stderr)
        sys.exit(2)
    except OSError as ex:
        print('error: %s: %s' % (path, ex), file=sys.stderr)
        sys.exit(2)
    r = detect(src)
    if '--json' in sys.argv:
        print(json.dumps(r, indent=1, ensure_ascii=False))
        return
    w = 16  # label width; longer keys (il2cpp_metadata_version) just push the colon right
    print('%-*s: %s' % (w, 'Engine', ' + '.join(r['engines']) or 'unknown'))
    for e in r['evidence']:
        print('%-*s: %s' % (w, '  evidence', e))
    for k, v in r['details'].items():
        if v:
            print('%-*s: %s' % (w, k, ', '.join(v) if isinstance(v, list) else v))
    for x in r['warnings']:
        print('%-*s: %s' % (w, 'WARNING', x))
    for n in r['next']:
        print('%-*s: %s' % (w, 'Next', n))


if __name__ == '__main__':
    main()
