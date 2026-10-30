// PreToolUse on Skill + UserPromptSubmit: append one row per skill run to ~/.claude/bacon-state/skill-usage.tsv
// (date, time, project, skill, source = claude | user), to see which skills never fire. Prints nothing: on UserPromptSubmit stdout goes into the context.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { readInput, findProject, main } from './common.mjs';

const HEADER = 'date\ttime\tproject\tskill\tsource\n';

function skillOf(input) {
  if (input.hook_event_name === 'UserPromptSubmit') {
    const m = /^\s*\/([\w:.-]+)/.exec(String(input.prompt || ''));
    return m ? { skill: m[1], source: 'user' } : null;
  }
  const s = input.tool_input?.skill;
  return s ? { skill: String(s), source: 'claude' } : null;
}

main(async () => {
  const input = await readInput();
  const hit = skillOf(input);
  if (!hit) return;
  const cwd = input.cwd || process.cwd();
  const proj = findProject(cwd);
  const project = path.basename(proj.docRoot || proj.root || cwd);
  const d = new Date();
  const pad = n => String(n).padStart(2, '0');
  const row = [`${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`, `${pad(d.getHours())}:${pad(d.getMinutes())}`,
    project, hit.skill, hit.source].map(v => v.replace(/[\t\r\n]/g, ' ')).join('\t') + '\n';
  const dir = `${os.homedir()}/.claude/bacon-state`.replace(/\\/g, '/');
  fs.mkdirSync(dir, { recursive: true });
  const file = `${dir}/skill-usage.tsv`;
  fs.appendFileSync(file, fs.existsSync(file) ? row : HEADER + row);
});
