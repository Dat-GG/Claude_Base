// SessionStart: print the project's workflow profile and the plan's handoff block, so a cleared session resumes from the docs.
import fs from 'node:fs';
import os from 'node:os';
import { readInput, findProject, docs, changelogMode, pruneState, loadMachine, machineFile, main } from './common.mjs';

/** One line with this machine's tool / folder paths (keys are the <tokens> used in the docs), plus setup warnings. */
function machineLines() {
  const m = loadMachine();
  if (m === null) return [`Machine: ${machineFile()} missing or invalid → run /setup-machine (doc paths like <ghidra>, <projects> cannot be resolved).`];
  const keys = Object.keys(m).filter(k => typeof m[k] === 'string' && m[k]);
  const out = [`Machine paths (${machineFile()}; docs write them as <key>): ${keys.map(k => `${k}=${m[k]}`).join(' · ')}`];
  if (!fs.existsSync(`${os.homedir()}/.claude/bacon-standard/standards/core.md`))
    out.push('Setup: ~/.claude/bacon-standard is missing, so CLAUDE.md imports of the standard do not load → run /setup-machine.');
  return out;
}

const MAX_LINES = 40;

function handoffBlock(planPath) {
  if (!fs.existsSync(planPath)) return null;
  const lines = fs.readFileSync(planPath, 'utf8').replace(/^﻿/, '').split(/\r?\n/);
  const start = lines.findIndex(l => /^#{2,3}\s*▶/.test(l));
  if (start < 0) return null;
  const level = lines[start].match(/^#+/)[0].length;
  const out = [];
  let i = start;
  for (; i < lines.length; i++) {
    const h = lines[i].match(/^(#+)\s/);
    if (i > start && h && h[1].length <= level) break;
    out.push(lines[i]);
  }
  while (out.length && /^\s*(---)?\s*$/.test(out[out.length - 1])) out.pop();
  if (out.length > MAX_LINES) {
    const more = out.length - MAX_LINES;
    out.length = MAX_LINES;
    out.push(`… (${more} more lines: read the block in the plan; at the next /handoff trim it to ≤ ${MAX_LINES} lines)`);
  }
  return out.join('\n');
}

main(async () => {
  const input = await readInput();
  try { pruneState(); } catch { /* ignore */ }
  const proj = findProject(input.cwd || process.cwd(), { scanDown: true });
  if (!proj.isUnity) return;
  if (proj.profileError) {
    console.log(`[bacon-unity] ${proj.profileError} is not valid JSON: the profile (protected folders, changelog, save backup) is ignored until it is fixed.`);
    return;
  }
  if (!proj.profile) {
    console.log(`[bacon-unity] Unity project at ${proj.root} has no .claude/bacon-profile.json. ` +
      'Core rules still apply; run /new-project (adopt mode) to bring it onto the standard.');
    return;
  }
  const p = proj.profile;
  const d = docs(p);
  const lines = [
    `[bacon-unity] Project ${p.project || ''} at ${proj.root}${proj.docRoot !== proj.root ? ` (docs at ${proj.docRoot})` : ''}`,
    `Profile: type=${p.type} · modules=${(p.modules || []).join(', ') || '-'} · mcp=${p.mcp} · changelog=${changelogMode(p)} · self_test=${p.self_test || 'full'} · comments=${p.comment_language || 'en'}`,
    `Docs: ${d.mechanics} (rules) · ${d.plan} (plan + handoff) · ${d.changelog} (history)`,
    'Before Play / compile: check the active Unity instance and EditorApplication.isPlaying (the user may be playing).',
    ...machineLines(),
  ];
  const block = handoffBlock(`${proj.docRoot}/${d.plan}`);
  lines.push(block ? `\nHandoff from ${d.plan}:\n${block}` : `\nNo "## ▶ Trạng thái & bước tiếp theo" block in ${d.plan} yet: create it at the next /handoff.`);
  console.log(lines.join('\n'));
});
