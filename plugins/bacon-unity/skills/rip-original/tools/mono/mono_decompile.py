"""mono_decompile.py - Unity Mono build -> readable C# (ILSpy), one folder per game assembly.

Purpose : read the original's code bodies (constants, formulas, PlayerPrefs keys) from a Mono build.
Usage   : py -I <tools>/mono/mono_decompile.py <game.apk | game.xapk | folder> --out <dir> [--all] [--dll <name.dll> ...]
          --all  also decompile third-party plugin dlls (DOTween, Spine, ...), default = game assemblies only
          --dll  only these assemblies
Inputs  : apk / xapk / apks (nested splits read in place) or a folder containing assets/bin/Data/Managed or Managed/.
Output  : <out>/Managed/*.dll (every assembly, used as references), <out>/src/<Assembly>/**.cs (ILSpy project, one file
          per type), <out>/literals.tsv (assembly, string literal from the #US heap) for grep.
Needs   : .NET SDK + ilspycmd (see references/workspace.md): env ILSPYCMD / DOTNET_ROOT win, else keys `ilspycmd` /
          `dotnet` of ~/.claude/bacon-machine.json (tools/_machine.py); missing -> one-line error, exit 2.
Proven  : 2026-10-22 on a Unity 2022.3.62f3 Mono probe apk (armeabi-v7a): constants, initializers, method bodies,
          PlayerPrefs key recovered exactly (see references/engine-il2cpp.md "Mono builds").
"""
import io
import os
import re
import subprocess
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # tools/ (py -I: only the script dir)
sys.dont_write_bytecode = True   # no __pycache__ inside the plugin folder
import _machine  # noqa: E402

ENGINE_PREFIXES = ('unityengine', 'unity.', 'unityeditor', 'system', 'mscorlib', 'mono.', 'netstandard', 'microsoft.',
                   'boo.', 'unityscript', 'nunit', 'firebase', 'google.', 'applovin', 'facebook', 'gameanalytics',
                   'admob', 'ironsource', 'newtonsoft')
CORE_PREFIXES = ENGINE_PREFIXES[:8]   # engine + BCL: what --all still skips
MANAGED_RE = re.compile(r'(^|/)(assets/bin/data/)?managed/([^/]+\.dll)$', re.I)


def iter_zip(zf):
    for info in zf.infolist():
        name = info.filename
        if name.lower().endswith('.apk') and '/' not in name.strip('/'):
            f = zf.open(info) if info.compress_type == zipfile.ZIP_STORED else io.BytesIO(zf.read(info))
            yield from iter_zip(zipfile.ZipFile(f))
        else:
            m = MANAGED_RE.search(name)
            if m:
                yield m.group(3), lambda zf=zf, info=info: zf.read(info)


def iter_source(path):
    if os.path.isdir(path):
        for d, _, files in os.walk(path):
            for name in files:
                full = os.path.join(d, name)
                if name.lower().endswith(('.apk', '.xapk', '.apks')):
                    yield from iter_zip(zipfile.ZipFile(full))
                    continue
                m = MANAGED_RE.search(full.replace('\\', '/'))
                if m:
                    yield m.group(3), lambda full=full: open(full, 'rb').read()
    else:
        yield from iter_zip(zipfile.ZipFile(path))


def is_game_dll(name):
    low = name.lower()
    return low.startswith('assembly-csharp') or not low.startswith(ENGINE_PREFIXES)


def user_strings(dll_path):
    """#US heap of a .NET assembly: every string literal used by IL (ldstr), without a decompiler."""
    data = open(dll_path, 'rb').read()
    pe = struct_u32(data, 0x3c)
    nsec = struct_u16(data, pe + 6)
    opt = pe + 24
    magic = struct_u16(data, opt)
    dd = opt + (96 if magic == 0x10b else 112)
    cli_rva = struct_u32(data, dd + 14 * 8)
    secs = []
    sh = opt + struct_u16(data, pe + 20)
    for i in range(nsec):
        s = sh + i * 40
        secs.append((struct_u32(data, s + 12), struct_u32(data, s + 8), struct_u32(data, s + 20)))

    def off(rva):
        for va, size, raw in secs:
            if va <= rva < va + max(size, 1):
                return rva - va + raw
        raise ValueError('rva %x' % rva)

    meta = off(struct_u32(data, off(cli_rva) + 8))
    vlen = struct_u32(data, meta + 12)
    p = meta + 16 + vlen + 2
    nstreams = struct_u16(data, p)
    p += 2
    for _ in range(nstreams):
        soff, ssize = struct_u32(data, p), struct_u32(data, p + 4)
        name_end = data.index(b'\0', p + 8)
        name = data[p + 8:name_end].decode()
        p = (name_end + 4) & ~3
        if name == '#US':
            heap = data[meta + soff: meta + soff + ssize]
            out, i = [], 1
            while i < len(heap):
                b = heap[i]
                if b & 0x80 == 0:
                    n, i = b, i + 1
                elif b & 0xC0 == 0x80:
                    n, i = ((b & 0x3F) << 8) | heap[i + 1], i + 2
                else:
                    n, i = ((b & 0x1F) << 24) | (heap[i + 1] << 16) | (heap[i + 2] << 8) | heap[i + 3], i + 4
                if n == 0:
                    continue
                if n > 1:   # n == 1: empty string "" (only the trailing flag byte) - nothing to grep
                    out.append(heap[i:i + n - 1].decode('utf-16-le', 'replace'))
                i += n
            return out
    return []


def struct_u16(d, o):
    return d[o] | d[o + 1] << 8


def struct_u32(d, o):
    return d[o] | d[o + 1] << 8 | d[o + 2] << 16 | d[o + 3] << 24


def main():
    args = sys.argv[1:]
    if any(a in ('-h', '--help') for a in args):
        print(__doc__)
        return
    if not args or '--out' not in args:
        print(__doc__)
        sys.exit(2)
    out = args[args.index('--out') + 1]
    want_all = '--all' in args
    only = [args[i + 1].lower() for i, a in enumerate(args) if a == '--dll']
    src = args[0]
    if not os.path.exists(src):
        print('error: %s: no such file or folder' % src, file=sys.stderr)
        sys.exit(2)
    managed = os.path.join(out, 'Managed')
    found = []
    try:
        for name, read in iter_source(src):
            found.append((name, read()))
    except zipfile.BadZipFile as e:
        print('error: %s: not an apk / xapk / apks (zip) file or folder (%s)' % (src, e), file=sys.stderr)
        sys.exit(2)
    if not found:
        print('no Managed/*.dll found: not a Mono build (run detect_engine.py)')
        sys.exit(1)
    ilspy = _machine.require('ilspycmd', env='ILSPYCMD')   # before writing anything
    dotnet_root = _machine.require('dotnet', env='DOTNET_ROOT')
    os.makedirs(managed, exist_ok=True)   # only now: nothing is created for a non-Mono input
    names = []
    for name, data in found:
        if not data.startswith(b'MZ'):
            print('WARNING: %s does not start with MZ (encrypted assembly: find the loader key in libmono / a plugin)'
                  % name)
        with open(os.path.join(managed, name), 'wb') as f:
            f.write(data)
        names.append(name)
    if only:
        targets = [n for n in names if n.lower() in only]
    elif want_all:
        targets = [n for n in names if not n.lower().startswith(CORE_PREFIXES)]
    else:
        targets = [n for n in names if is_game_dll(n)]
    print('%d assemblies extracted; decompiling: %s' % (len(names), ', '.join(sorted(targets))))
    env = dict(os.environ, DOTNET_ROOT=dotnet_root, DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_NOLOGO='1')
    rows = []
    for name in sorted(targets):
        dst = os.path.join(out, 'src', name[:-4])
        os.makedirs(dst, exist_ok=True)
        cmd = [ilspy,os.path.join(managed, name), '-p', '-o', dst, '-r', managed]
        res = subprocess.run(cmd, env=env, capture_output=True, text=True)
        n_cs = sum(len([f for f in fs if f.endswith('.cs')]) for _, _, fs in os.walk(dst))
        status = 'ok' if res.returncode == 0 else 'FAILED (%d): %s' % (res.returncode, (res.stderr or res.stdout)[-400:])
        print('  %-40s %4d .cs  %s' % (name, n_cs, status))
        try:
            for s in user_strings(os.path.join(managed, name)):
                rows.append('%s\t%s' % (name, s.replace('\t', '\\t').replace('\n', '\\n')))
        except (ValueError, IndexError) as e:
            print('  (no #US heap read for %s: %s)' % (name, e))
    with open(os.path.join(out, 'literals.tsv'), 'w', encoding='utf-8') as f:
        f.write('assembly\tliteral\n' + '\n'.join(rows) + '\n')
    print('literals: %d -> %s' % (len(rows), os.path.join(out, 'literals.tsv')))
    print('source  : ' + os.path.join(out, 'src'))


if __name__ == '__main__':
    main()
