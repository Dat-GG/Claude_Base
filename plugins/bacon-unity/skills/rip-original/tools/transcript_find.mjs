// Recover a file or command that only ever existed in an old Claude Code session (lost scratchpad scripts...).
//
//   node transcript_find.mjs "<regex>" [--project <substring of ~/.claude/projects folder>] [--full] [--out file]
//
// Scans ~/.claude/projects/*/**/*.jsonl (main sessions and <session>/subagents/*.jsonl) for Write / Edit / MultiEdit calls whose file path matches, and Bash / PowerShell
// commands that match (heredoc `cat > x.py <<'EOF'` is how most scratchpad scripts were written). Without --full it
// lists hits (file, line, time, tool, size); with --full it prints the whole content / command of each hit, oldest first.
// Edits are listed after the Write they modify: apply them in order to get the final version.
// Proven 2026-10-21: recovered the 4 E2D Ghidra query scripts and the HMR IL2CPP literal tools.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import readline from 'node:readline';

const argv = process.argv.slice(2);
const opt = (k) => { const i = argv.indexOf(k); return i >= 0 ? argv.splice(i, 2)[1] : null; };
const full = argv.includes('--full'); if (full) argv.splice(argv.indexOf('--full'), 1);
const proj = opt('--project'); const outFile = opt('--out');
if (!argv[0]) { console.error('usage: node transcript_find.mjs "<regex>" [--project X] [--full] [--out file]'); process.exit(1); }
const re = new RegExp(argv[0], 'i');

const root = path.join(os.homedir(), '.claude', 'projects');
// every *.jsonl under a project folder: main sessions (<proj>/<id>.jsonl) and subagent runs
// (<proj>/<session>/subagents/*.jsonl, any depth)
const walk = (dir) => { let out = []; let ents = [];
  try { ents = fs.readdirSync(dir, { withFileTypes: true }); } catch { return out; }
  for (const e of ents) { const p = path.join(dir, e.name);
    if (e.isDirectory()) out = out.concat(walk(p)); else if (e.name.endsWith('.jsonl')) out.push(p); }
  return out; };
const files = fs.readdirSync(root).filter(d => !proj || d.toLowerCase().includes(proj.toLowerCase()))
  .flatMap(d => walk(path.join(root, d)));

const hits = [];
for (const f of files) {
  const rl = readline.createInterface({ input: fs.createReadStream(f), crlfDelay: Infinity });
  let n = 0;
  for await (const line of rl) {
    n++;
    if (!re.test(line)) continue;
    let o; try { o = JSON.parse(line); } catch { continue; }
    const content = o.message?.content; if (!Array.isArray(content)) continue;
    for (const c of content) {
      if (c.type !== 'tool_use') continue;
      const i = c.input || {};
      let body = null;
      if (['Write', 'Edit', 'MultiEdit'].includes(c.name) && re.test(i.file_path || ''))
        body = c.name === 'Write' ? `FILE ${i.file_path}\n${i.content}` :
          `EDIT ${i.file_path}\n` + (i.edits || [i]).map(e => `--- old\n${e.old_string}\n+++ new\n${e.new_string}`).join('\n');
      else if ((c.name === 'Bash' || c.name === 'PowerShell') && re.test(i.command || '')) body = i.command;
      if (body !== null) hits.push({ f: path.relative(root, f), n, t: o.timestamp, tool: c.name, body });
    }
  }
}
hits.sort((a, b) => String(a.t).localeCompare(String(b.t)));
let txt = '';
for (const h of hits) {
  txt += full ? `\n######## ${h.f}:${h.n} ${h.t} ${h.tool}\n${h.body}\n`
              : `${h.t} ${h.tool} ${h.f}:${h.n} (${h.body.length} chars) ${h.body.slice(0, 120).replace(/\s+/g, ' ')}\n`;
}
if (outFile) { fs.writeFileSync(outFile, txt); console.log(`${hits.length} hits -> ${outFile}`); } else process.stdout.write(txt || 'no hits\n');
