// Shared helpers for the bacon-unity hooks. Every hook must fail open: an exception never blocks the user's work.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';

export async function readInput() {
  let raw = '';
  for await (const chunk of process.stdin) raw += chunk;
  try {
    const v = JSON.parse(raw || '{}');
    return v && typeof v === 'object' && !Array.isArray(v) ? v : {};
  } catch { return {}; }
}

export function norm(p) {
  return path.resolve(p).replace(/\\/g, '/');
}

const HOME_VARS = new Set(['HOME', 'USERPROFILE']);

function envVar(v) {
  return process.env[v] ?? (HOME_VARS.has(v.toUpperCase()) ? os.homedir() : undefined);
}

/** Machine paths (~/.claude/bacon-machine.json, made by /setup-machine). BACON_MACHINE overrides the file, for tests. */
export function machineFile() {
  return norm(process.env.BACON_MACHINE || `${os.homedir()}/.claude/bacon-machine.json`);
}

export function loadMachine() {
  try {
    const v = JSON.parse(fs.readFileSync(machineFile(), 'utf8').replace(/^﻿/, ''));
    return v && typeof v === 'object' && !Array.isArray(v) ? v : {};
  } catch { return null; }
}

export function expandPath(p) {
  if (!p) return p;
  const m = loadMachine() || {};
  let s = p.replace(/<([a-z][\w-]*)>/g, (t, k) => (typeof m[k] === 'string' && m[k] ? m[k] : t))
           .replace(/%([^%]+)%/g, (m, v) => envVar(v) ?? m)
           .replace(/\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?/g, (m, v) => envVar(v) ?? m);
  if (s.startsWith('~')) s = os.homedir() + s.slice(1);
  return norm(s);
}

const SKIP_DIRS = new Set(['Library', 'Temp', 'Logs', 'obj', 'Packages', 'Assets', 'ProjectSettings', 'UserSettings', '.git', 'node_modules']);

function isUnityRoot(d) {
  return fs.existsSync(`${d}/ProjectSettings/ProjectVersion.txt`) && fs.existsSync(`${d}/Assets`);
}

/** undefined = no profile file; null = file exists but is not valid JSON; object = profile. */
function profileAt(d) {
  const p = `${d}/.claude/bacon-profile.json`;
  if (!fs.existsSync(p)) return undefined;
  try {
    const v = JSON.parse(fs.readFileSync(p, 'utf8').replace(/^﻿/, ''));
    return v && typeof v === 'object' ? v : null;
  } catch { return null; }
}

function childDirs(d) {
  try {
    return fs.readdirSync(d, { withFileTypes: true })
      .filter(e => e.isDirectory() && !SKIP_DIRS.has(e.name) && !e.name.startsWith('.'))
      .map(e => `${d}/${e.name}`);
  } catch { return []; }
}

function result(unity, profDir, prof) {
  const root = unity || profDir;
  return {
    root,                          // Unity project root: path rules (Library/, Packages/, globs) are relative to it
    docRoot: profDir || root,      // folder holding the profile and the docs (may be a repo root above the Unity folder)
    profile: prof || null,
    profileError: prof === null ? `${profDir}/.claude/bacon-profile.json` : null,
    isUnity: !!root,
  };
}

/**
 * Finds the Unity project (and its bacon profile) that `start` belongs to.
 * Walks up: the nearest Unity root wins for path rules; the profile comes from that root or the nearest ancestor.
 * scanDown (session start only): when nothing is found above, look two levels down (Claude launched at a repo root).
 * BACON_PROFILE (path to a profile json) overrides the search, for tests and migrations.
 */
export function findProject(start, { scanDown = false } = {}) {
  if (process.env.BACON_PROFILE) {
    const pp = norm(process.env.BACON_PROFILE);
    const root = process.env.BACON_PROJECT_ROOT ? norm(process.env.BACON_PROJECT_ROOT) : path.dirname(path.dirname(pp)).replace(/\\/g, '/');
    try { return { root, docRoot: root, profile: JSON.parse(fs.readFileSync(pp, 'utf8')), profileError: null, isUnity: true }; } catch { /* fall through */ }
  }
  let d = norm(start || process.cwd());
  let unity = null;
  for (;;) {
    const prof = profileAt(d);
    if (!unity && isUnityRoot(d)) unity = d;
    if (prof !== undefined) return result(unity, d, prof);
    const up = path.dirname(d).replace(/\\/g, '/');
    if (up === d) break;
    d = up;
  }
  if (unity || !scanDown) return result(unity, null, undefined);
  const base = norm(start || process.cwd());
  for (const c1 of childDirs(base)) {
    for (const c of [c1, ...childDirs(c1)]) {
      const prof = profileAt(c);
      if (prof !== undefined) return result(isUnityRoot(c) ? c : unityBelow(c), c, prof);
      if (!unity && isUnityRoot(c)) unity = c;
    }
  }
  return result(unity, null, undefined);
}

function unityBelow(d) {
  for (const c of childDirs(d)) if (isUnityRoot(c)) return c;
  return d;
}

export function globToRegex(glob) {
  let re = '';
  for (let i = 0; i < glob.length; i++) {
    const ch = glob[i];
    if (ch === '*' && glob[i + 1] === '*') {
      i++;
      if (glob[i + 1] === '/') { re += '(?:.*/)?'; i++; } else re += '.*';
    }
    else if (ch === '*') re += '[^/]*';
    else if (ch === '?') re += '[^/]';
    else re += ch.replace(/[.+^${}()|[\]\\]/g, '\\$&');
  }
  return new RegExp(`^${re}$`, 'i');
}

export function matchesAny(rel, globs) {
  return (globs || []).find(g => globToRegex(g).test(rel)) || null;
}

export function relTo(root, file) {
  if (!root) return null;
  const r = path.relative(root, norm(file)).replace(/\\/g, '/');
  return r.startsWith('..') || path.isAbsolute(r) ? null : r;
}

function stateDir() {
  const dir = `${os.homedir()}/.claude/bacon-state`.replace(/\\/g, '/');
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

export function stateFile(sessionId) {
  return `${stateDir()}/${(sessionId || 'default').replace(/[^\w-]/g, '_')}.json`;
}

export function readState(sessionId) {
  try {
    const st = JSON.parse(fs.readFileSync(stateFile(sessionId), 'utf8'));
    return { ...st, edits: Array.isArray(st?.edits) ? st.edits : [] };
  } catch { return { edits: [] }; }
}

export function writeState(sessionId, state) {
  fs.writeFileSync(stateFile(sessionId), JSON.stringify(state));
}

/** Deletes per-session state files older than `days` (one file per session, never cleaned otherwise). Keeps skill-usage.tsv. */
export function pruneState(days = 30) {
  const dir = stateDir();
  const limit = Date.now() - days * 86400000;
  for (const f of fs.readdirSync(dir)) {
    if (!f.endsWith('.json')) continue;
    try { if (fs.statSync(`${dir}/${f}`).mtimeMs < limit) fs.unlinkSync(`${dir}/${f}`); } catch { /* ignore */ }
  }
}

export function docs(profile) {
  return { plan: 'PLAN_INGAME.md', mechanics: 'GAME_MECHANICS.md', changelog: 'CHANGELOG.md', ...(profile?.docs || {}) };
}

/** The changelog setting, with the documented default when a profile exists. */
export function changelogMode(profile) {
  return profile ? (profile.changelog || 'every-change') : null;
}

export function emit(obj) {
  process.stdout.write(JSON.stringify(obj));
}

export async function main(fn) {
  try { await fn(); } catch (e) {
    process.stderr.write(`[bacon-unity hook] ${e?.stack || e}\n`);
  }
  process.exit(0);
}
