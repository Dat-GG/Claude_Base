// doctor.mjs - check / set up one machine for the bacon-unity standard.
//
// Purpose : find the tools and folders the docs refer to as <key> tokens, keep them in ~/.claude/bacon-machine.json,
//           link ~/.claude/bacon-standard to the standard repo, and report what is missing.
// Usage   : node doctor.mjs                    check: table of keys (saved value, detected value, status) + extras
//           node doctor.mjs write [--force]    save detected values for keys not saved yet (--force: replace all detected)
//           node doctor.mjs set key=value ...  save explicit values (key= with nothing removes the key)
//           node doctor.mjs link [--force]     junction ~/.claude/bacon-standard -> <standard>/plugins/bacon-unity
//           add --json for machine-readable output
// Inputs  : the file system (shallow searches of tool folders, drive roots, Program Files, Downloads), Unity Hub,
//           ~/.claude/plugins/known_marketplaces.json. BACON_MACHINE overrides the machine file path (tests).
// Outputs : ~/.claude/bacon-machine.json (a .bak of the previous file on every write), the junction. Never installs anything.
// Proven  : 2026-10-23 on the reference machine (all keys found).
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const HOME = os.homedir().replace(/\\/g, '/');
const MACHINE = (process.env.BACON_MACHINE || `${HOME}/.claude/bacon-machine.json`).replace(/\\/g, '/');
const LINK = `${HOME}/.claude/bacon-standard`;
const SKIP = new Set(['windows', '$recycle.bin', 'system volume information', 'node_modules', '.git', 'library', 'temp',
  'appdata', 'programdata', 'recovery', 'perflogs', 'msocache', 'config.msi']);

const exists = p => { try { return fs.existsSync(p); } catch { return false; } };
const drives = () => 'CDEFGHIJ'.split('').map(l => `${l}:`).filter(d => exists(`${d}/`));
const fwd = p => p && p.replace(/\\/g, '/');

/** Breadth-first search for a file or folder whose name matches `re`, `depth` levels below each root. */
function find(re, roots, depth, test = () => true) {
  const hits = [];
  let level = roots.filter(exists).map(fwd);
  for (let d = 0; d <= depth && level.length; d++) {
    const next = [];
    for (const dir of level) {
      let entries = [];
      try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { continue; }
      for (const e of entries) {
        const full = `${dir}/${e.name}`;
        if (re.test(e.name) && test(full)) hits.push(full);
        if (e.isDirectory() && !SKIP.has(e.name.toLowerCase()) && !e.name.startsWith('.')) next.push(full);
      }
    }
    level = next;
  }
  return hits;
}

const verKey = s => (s.match(/\d+/g) || []).map(n => n.padStart(6, '0')).join('.');
const newest = list => list.sort((a, b) => verKey(b).localeCompare(verKey(a)))[0] || '';

function run(cmd, args) {
  const r = spawnSync(cmd, args, { encoding: 'utf8', timeout: 20000, shell: false });
  return r.status === 0 ? (r.stdout || r.stderr || '').trim() : null;
}

function loadSaved() {
  try { return JSON.parse(fs.readFileSync(MACHINE, 'utf8').replace(/^\uFEFF/, '')); } catch { return {}; }
}

function standardRepo() {
  // 1. this script lives in the repo itself (not the plugin cache)
  const here = fwd(path.dirname(new URL(import.meta.url).pathname).replace(/^\/([A-Za-z]:)/, '$1'));
  const i = here.indexOf('/plugins/bacon-unity/');
  if (i > 0 && !here.includes('/.claude/plugins/cache/')) return here.slice(0, i);
  // 2. the local marketplace the plugin was installed from
  try {
    const km = JSON.parse(fs.readFileSync(`${HOME}/.claude/plugins/known_marketplaces.json`, 'utf8'));
    const p = km['gg-snm']?.source?.path || km['gg-snm']?.installLocation;
    if (p && exists(`${p}/plugins/bacon-unity`)) return fwd(p);
  } catch { /* ignore */ }
  return '';
}

function unityEditors() {
  const roots = ['C:/Program Files/Unity/Hub/Editor', ...drives().map(d => `${d}/Program Files/Unity/Hub/Editor`), ...drives().map(d => `${d}/Unity/Hub/Editor`)];
  try {
    const sec = JSON.parse(fs.readFileSync(`${process.env.APPDATA}/UnityHub/secondaryInstallPath.json`, 'utf8'));
    if (sec) roots.unshift(fwd(sec));
  } catch { /* ignore */ }
  return roots.find(r => exists(r)) || '';
}

function detect(saved) {
  const det = {};
  det.standard = standardRepo();
  const repo = saved.standard || det.standard;
  // studio root = nearest ancestor of the repo that holds a Project/ folder (the repo may sit in <studio>/Tools/...)
  det.studio = '';
  for (let d = repo && fwd(path.dirname(repo)); d && d !== fwd(path.dirname(d)); d = fwd(path.dirname(d)))
    if (exists(`${d}/Project`)) { det.studio = d; break; }
  const studio = saved.studio || det.studio;
  det.projects = studio && exists(`${studio}/Project`) ? `${studio}/Project` : '';
  det['tools-home'] = [...drives().filter(d => d !== 'C:').map(d => `${d}/Tools`), 'C:/Tools', `${HOME}/Tools`].find(exists) || '';
  const th = saved['tools-home'] || det['tools-home'];
  const toolRoots = [th, studio && `${studio}/Tools`, `${HOME}/Downloads`, ...drives().map(d => `${d}/`)].filter(Boolean);

  det.ghidra = newest(find(/^ghidra_[\d.]+.*PUBLIC$/i, toolRoots, 2, p => exists(`${p}/support/analyzeHeadless.bat`)));
  det['ghidra-projects'] = th && exists(`${th}/ghidra_projects`) ? `${th}/ghidra_projects` : '';
  det['unity-editors'] = unityEditors();
  const ue = saved['unity-editors'] || det['unity-editors'];
  let jdks = [];
  if (ue) for (const v of fs.readdirSync(ue)) {
    const j = `${ue}/${v}/Editor/Data/PlaybackEngines/AndroidPlayer/OpenJDK`;
    let rel = '';
    try { rel = fs.readFileSync(`${j}/release`, 'utf8'); } catch { continue; }
    const major = +((rel.match(/JAVA_VERSION="(\d+)/) || [])[1] || 0);
    if (major >= 17) jdks.push(j);
  }
  if (!jdks.length && process.env.JAVA_HOME && exists(`${process.env.JAVA_HOME}/bin/java.exe`)) jdks = [fwd(process.env.JAVA_HOME)];
  det.jdk17 = newest(jdks);
  det.il2cppdumper = fwd(path.dirname(find(/^Il2CppDumper\.exe$/i, toolRoots, 3)[0] || '.')).replace(/^\.$/, '');
  det.cpp2il = find(/^Cpp2IL\.exe$/i, toolRoots, 3)[0] || '';
  det.assetripper = newest(find(/^AssetRipper(\.GUI\.Free)?\.exe$/i, toolRoots, 4));
  det['luajit-decompiler'] = find(/^luajit-decompiler-v2\.exe$/i, toolRoots, 3)[0] || '';
  det.dotnet = [th && `${th}/dotnet`, 'C:/Program Files/dotnet', `${HOME}/.dotnet`].filter(Boolean).find(d => exists(`${d}/dotnet.exe`)) || '';
  det.ilspycmd = [th && `${th}/ilspycmd/ilspycmd.exe`, `${HOME}/.dotnet/tools/ilspycmd.exe`].filter(Boolean).find(exists) || '';
  det.ldplayer = [...drives().map(d => `${d}/LDPlayer/LDPlayer9`), 'C:/Program Files/LDPlayer/LDPlayer9'].find(d => exists(`${d}/adb.exe`)) || '';
  det['adb-device'] = 'emulator-5554';
  det.python = run('py', ['-V']) ? 'py -I' : (run('python', ['-V'])?.startsWith('Python 3') ? 'python -I' : '');
  det.ffmpeg = '';
  return det;
}

const REQUIRED = ['standard', 'studio', 'projects', 'python'];
const INSTALL = {
  ghidra: 'Ghidra 11.x: github.com/NationalSecurityAgency/ghidra/releases → unzip into <tools-home> (needs JDK 17+: the Unity 6 OpenJDK works)',
  'ghidra-projects': 'analyzed Ghidra projects (*.gpr + *.rep): copy <tools-home>/ghidra_projects from the old machine, or re-analyze (E2D: 465 s)',
  jdk17: 'install Unity 6 with Android support (its OpenJDK is JDK 17) or a JDK 17+ (adoptium.net)',
  il2cppdumper: 'github.com/Perfare/Il2CppDumper/releases → <tools-home>/Il2CppDumper, config.json "RequireAnyKey": false',
  cpp2il: 'github.com/SamboyCoding/Cpp2IL/releases → <tools-home>/Cpp2IL/Cpp2IL.exe',
  assetripper: 'github.com/AssetRipper/AssetRipper/releases (GUI Free, win x64)',
  'luajit-decompiler': 'only for Lua-scripted Unity (tolua / xLua): luajit-decompiler-v2 release exe → <tools-home>/luajit-decompiler-v2/',
  dotnet: 'dot.net/v1/dotnet-install.ps1 -Channel 10.0 -InstallDir <tools-home>/dotnet -NoPath',
  ilspycmd: 'DOTNET_ROOT=<dotnet> <dotnet>/dotnet.exe tool install ilspycmd --tool-path <tools-home>/ilspycmd',
  ldplayer: 'LDPlayer 9 (ldplayer.net); enable root + ADB in its settings',
  'unity-editors': 'Unity Hub + the editor versions of the projects',
  python: 'Python 3.12+ from python.org with the py launcher, then: py -m pip install -r <standard>/plugins/bacon-unity/skills/setup-machine/requirements.txt',
  standard: 'the standard repo (clone github.com/Dat-GG/Claude_Base), then: claude plugin marketplace add <repo> && claude plugin install bacon-unity@gg-snm',
  studio: 'the studio root folder (holds Project/, Tools/, downloaded xapks): set it with "set studio=<path>"',
  projects: 'the game projects folder: set it with "set projects=<path>"',
};

function linkState(saved) {
  const target = saved.standard ? `${saved.standard}/plugins/bacon-unity` : '';
  let real = '';
  try { real = fwd(fs.realpathSync(LINK)); } catch { /* missing */ }
  return { link: LINK, target, real, ok: !!real && !!target && real.toLowerCase() === fwd(fs.realpathSync(target)).toLowerCase() };
}

function extras(saved) {
  const py = (saved.python || 'py -I').split(' ');
  const libs = ['capstone', 'elftools', 'UnityPy', 'numpy', 'cv2', 'PIL', 'imageio', 'imageio_ffmpeg', 'texture2ddecoder', 'fitz'];
  const code = `import importlib\nfor m in ${JSON.stringify(libs)}:\n    try:\n        x = importlib.import_module(m); print(m, getattr(x, '__version__', getattr(x, 'VERSION', 'ok')))\n    except Exception as e: print(m, 'MISSING')`;
  const out = run(py[0], [...py.slice(1), '-c', code]);
  let installed = false;
  try { installed = fs.readFileSync(`${HOME}/.claude/plugins/installed_plugins.json`, 'utf8').includes('bacon-unity@gg-snm'); } catch { /* ignore */ }
  const userRules = saved.standard ? `${saved.standard}/user/CLAUDE.md` : '';
  let userMd = 'no ~/.claude/CLAUDE.md';
  try {
    const mine = fs.readFileSync(`${HOME}/.claude/CLAUDE.md`, 'utf8');
    userMd = userRules && exists(userRules) && fs.readFileSync(userRules, 'utf8') === mine ? 'same as <standard>/user/CLAUDE.md' : 'differs from <standard>/user/CLAUDE.md';
  } catch { /* missing */ }
  // optional CLI on PATH (npm shim = .cmd on Windows, so go through cmd); used only when a rip has a .codegraph/ index
  const cg = process.platform === 'win32' ? run('cmd', ['/d', '/c', 'codegraph --version']) : run('codegraph', ['--version']);
  return {
    node: process.version,
    codegraph: cg ? cg.split(/\r?\n/)[0] : 'not installed (optional: npm i -g @colbymchenry/codegraph, see engine-il2cpp.md › Lua 6)',
    python_libs: out ? out.split(/\r?\n/) : ['python not runnable'],
    plugin_installed: installed,
    user_claude_md: userMd,
    link: linkState(saved),
  };
}

function save(obj) {
  fs.mkdirSync(path.dirname(MACHINE), { recursive: true });
  if (exists(MACHINE)) fs.copyFileSync(MACHINE, `${MACHINE}.bak`);
  const sorted = Object.fromEntries(Object.keys(obj).sort().map(k => [k, obj[k]]));
  fs.writeFileSync(MACHINE, JSON.stringify(sorted, null, 2) + '\n');
}

function report(saved, det, json) {
  const keys = [...new Set([...Object.keys(det), ...Object.keys(saved)])];
  const rows = keys.map(k => {
    const s = saved[k] ?? '', d = det[k] ?? '';
    const val = s || d;
    const isPath = !['adb-device', 'python', 'ffmpeg'].includes(k);
    const ok = !val ? false : !isPath || exists(val);
    const status = !val ? (REQUIRED.includes(k) ? 'MISSING (required)' : (k === 'ffmpeg' ? 'ok (imageio)' : 'missing'))
      : !ok ? 'saved path not found' : s ? (d && d.toLowerCase() !== s.toLowerCase() ? `ok (also found ${d})` : 'ok') : 'detected, not saved';
    return { key: k, saved: s, detected: d, status, install: !ok && k !== 'ffmpeg' ? INSTALL[k] : undefined };
  });
  const ex = extras({ ...det, ...saved });
  if (json) return console.log(JSON.stringify({ machine_file: MACHINE, rows, ...ex }, null, 1));
  console.log(`Machine file: ${MACHINE}${exists(MACHINE) ? '' : ' (not created yet: run "write")'}\n`);
  for (const r of rows) console.log(`${r.key.padEnd(16)} ${(r.saved || r.detected || '-').padEnd(70)} ${r.status}`);
  console.log(`\nnode ${ex.node} · plugin installed: ${ex.plugin_installed} · ~/.claude/CLAUDE.md: ${ex.user_claude_md}`);
  console.log(`codegraph: ${ex.codegraph}`);
  console.log(`link ${ex.link.link} → ${ex.link.real || '(missing)'} ${ex.link.ok ? 'ok' : `(expected ${ex.link.target || '<standard>/plugins/bacon-unity'}: run "link")`}`);
  console.log(`python libs: ${ex.python_libs.join(' · ')}`);
  const todo = rows.filter(r => r.install);
  if (todo.length) {
    console.log('\nMissing (ask the user before installing anything):');
    for (const r of todo) console.log(`- ${r.key}: ${r.install}`);
  }
}

const args = process.argv.slice(2);
const json = args.includes('--json');
const force = args.includes('--force');
const cmd = args.find(a => !a.startsWith('--')) || 'check';
const saved = loadSaved();

if (cmd === 'check') report(saved, detect(saved), json);
else if (cmd === 'write') {
  const det = detect(saved);
  const next = { ...saved };
  for (const [k, v] of Object.entries(det)) if (v !== '' && (force || !(k in saved))) next[k] = v;
  for (const k of Object.keys(det)) if (!(k in next)) next[k] = '';
  save(next);
  report(next, det, json);
} else if (cmd === 'set') {
  const next = { ...saved };
  for (const kv of args.filter(a => a.includes('='))) {
    const [k, ...rest] = kv.split('=');
    const v = fwd(rest.join('='));
    if (v) next[k] = v; else delete next[k];
  }
  save(next);
  report(next, detect(next), json);
} else if (cmd === 'link') {
  const st = linkState(saved);
  if (!st.target || !exists(st.target)) { console.log(`no valid "standard" in ${MACHINE}: run "write" or "set standard=<repo>" first`); process.exit(2); }
  if (st.ok) { console.log(`ok: ${LINK} → ${st.real}`); process.exit(0); }
  if (exists(LINK) || st.real) {
    if (!force) { console.log(`${LINK} exists and points to ${st.real || '?'}: rerun with --force to replace it`); process.exit(2); }
    // "rmdir" on a junction removes the link only, never the target's files
    spawnSync('cmd', ['/c', 'rmdir', LINK.replace(/\//g, '\\')], { encoding: 'utf8' });
    if (exists(LINK)) { console.log(`could not remove ${LINK} (not a junction?): remove it by hand`); process.exit(2); }
  }
  fs.symlinkSync(st.target, LINK, 'junction');
  console.log(`linked ${LINK} → ${fwd(fs.realpathSync(LINK))}`);
} else {
  console.log('usage: node doctor.mjs [check|write [--force]|set key=value ...|link [--force]] [--json]');
  process.exit(2);
}
