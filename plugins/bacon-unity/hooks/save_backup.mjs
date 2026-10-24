// PreToolUse on the Unity MCP tools that can enter Play (manage_editor play, execute_code setting isPlaying,
// execute_menu_item Edit/Play): copy the dev save to ~/.claude/bacon-backups/<project>/ first.
// Second safety net under /playtest; keeps the 30 newest copies.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { readInput, findProject, expandPath, main } from './common.mjs';

function entersPlay(tool, ti) {
  if (/manage_editor$/.test(tool)) return String(ti.action || '').toLowerCase() === 'play';
  if (/execute_code$/.test(tool)) return /isPlaying\s*=\s*true|EnterPlaymode\s*\(/.test(String(ti.code || ''));
  if (/execute_menu_item$/.test(tool)) return /^Edit\/Play\b/i.test(String(ti.menu_path || ti.menuPath || ''));
  return false;
}

main(async () => {
  const input = await readInput();
  if (!entersPlay(input.tool_name || '', input.tool_input || {})) return;
  const proj = findProject(input.cwd || process.env.CLAUDE_PROJECT_DIR || process.cwd(), { scanDown: true });
  if (!proj.profile?.save_file) return;
  const save = expandPath(proj.profile.save_file);
  if (!fs.existsSync(save)) {
    process.stderr.write(`[bacon-unity] save_file not found, no backup before Play: ${save}\n`);
    return;
  }
  const base = path.basename(save);
  const dir = `${os.homedir()}/.claude/bacon-backups/${proj.profile.project || path.basename(proj.root)}`.replace(/\\/g, '/');
  fs.mkdirSync(dir, { recursive: true });
  const n = new Date();
  const p2 = (v, w = 2) => String(v).padStart(w, '0');
  const ts = `${n.getFullYear()}${p2(n.getMonth() + 1)}${p2(n.getDate())}-${p2(n.getHours())}${p2(n.getMinutes())}${p2(n.getSeconds())}${p2(n.getMilliseconds(), 3)}`;
  fs.copyFileSync(save, `${dir}/${ts}_${base}`);
  const files = fs.readdirSync(dir).filter(f => /^\d{8}-\d{6,9}_/.test(f) && f.endsWith(`_${base}`)).sort();
  for (const f of files.slice(0, Math.max(0, files.length - 30))) fs.unlinkSync(`${dir}/${f}`);
  fs.appendFileSync(`${dir}/backup.log`, `${ts} ${save} (${fs.statSync(save).size} B) before Play\n`);
});
