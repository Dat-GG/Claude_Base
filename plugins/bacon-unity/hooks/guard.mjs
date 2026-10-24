// PreToolUse guard: Unity folders that must never be edited, vendor / framework folders from the profile,
// destructive shell commands on .meta / Library / Packages, and git commands that change the repo (git belongs to the user).
import path from 'node:path';
import { readInput, findProject, relTo, matchesAny, emit, main } from './common.mjs';

function decide(decision, reason) {
  emit({ hookSpecificOutput: { hookEventName: 'PreToolUse', permissionDecision: decision, permissionDecisionReason: reason } });
}

const NEVER = /^(Library|Temp|Logs|UserSettings|obj)\//i;

function checkFile(filePath) {
  const proj = findProject(path.dirname(filePath));
  if (!proj.isUnity) return;
  const rel = relTo(proj.root, filePath);
  if (!rel) return;
  const prof = proj.profile || {};
  if (NEVER.test(rel)) return decide('deny', `bacon-unity: ${rel} is Unity-generated (Library/Temp/Logs/UserSettings/obj). Never edit it.`);
  if (/^Packages\//i.test(rel) && !prof.allow_packages)
    return decide('ask', `bacon-unity: ${rel} is under Packages/. Edit it only when the user explicitly asked for this change.`);
  const prot = matchesAny(rel, prof.protected);
  if (prot) return decide('deny', `bacon-unity: ${rel} is protected by the project profile (${prot}): vendor / third-party code. Extend it from _Project instead; if the user really wants this edit, they remove the glob from .claude/bacon-profile.json "protected".`);
  if (/\.meta$/i.test(rel)) return decide('ask', `bacon-unity: editing a .meta file (${rel}) can break GUID references. Confirm this is intended.`);
  const ask = matchesAny(rel, prof.ask);
  if (ask) return decide('ask', `bacon-unity: ${rel} matches ${ask} (shared framework). Edits here need the user's approval.`);
}

const GIT_WRITE = new Set(['commit', 'push', 'merge', 'rebase', 'reset', 'revert', 'cherry-pick', 'am', 'pull', 'checkout',
  'switch', 'restore', 'clean', 'rm', 'mv', 'apply', 'filter-branch', 'filter-repo', 'gc', 'prune', 'update-ref',
  'init', 'clone', 'submodule', 'lfs', 'add', 'stage', 'notes', 'update-index', 'symbolic-ref', 'sparse-checkout',
  'replace', 'bisect', 'worktree', 'reflog', 'commit-tree', 'merge-file', 'read-tree']);

function gitWrite(sub, args) {
  const first = args[0] || '';
  if (args.some(a => a === '--help' || a === '-h')) return false;
  if (GIT_WRITE.has(sub)) {
    if (sub === 'lfs' && /^(ls-files|status|env|version|track)$/.test(first) && (first !== 'track' || args.length === 1)) return false;
    if (sub === 'submodule' && /^(status|summary)?$/.test(first)) return false;
    if (sub === 'worktree' && first === 'list') return false;
    if (sub === 'reflog' && !/^(expire|delete)$/.test(first)) return false;
    if (sub === 'notes' && /^(list|show)?$/.test(first)) return false;
    if (sub === 'sparse-checkout' && first === 'list') return false;
    if (sub === 'bisect' && /^(log|view|visualize)$/.test(first)) return false;
    return true;
  }
  if (sub === 'stash') return !/^(list|show)$/.test(first);
  if (sub === 'tag') return !(first === '' || /^(-l|--list|-n\d*|--contains|--points-at)$/.test(first));
  if (sub === 'branch') return args.some(a => /^(-[dDmMcCf]|--delete|--move|--copy|--force|--set-upstream-to|-u|--unset-upstream|--edit-description)$/.test(a))
    || (first !== '' && !first.startsWith('-'));
  if (sub === 'remote') return /^(add|remove|rm|rename|set-url|set-head|set-branches|prune|update)$/.test(first);
  if (sub === 'config') {
    if (/^(get|list)$/.test(first)) return false;
    if (/^(set|unset|rename-section|remove-section|edit)$/.test(first)) return true;
    if (args.some(a => /^(--get|--get-all|--get-regexp|--list|-l|--show-origin|--show-scope)$/.test(a))) return false;
    if (args.some(a => /^(--unset|--unset-all|--add|--replace-all|--edit|-e|--rename-section|--remove-section)$/.test(a))) return true;
    return args.filter(a => !a.startsWith('-')).length >= 2;
  }
  return false;
}

function splitArgs(s) {
  return (s.match(/"[^"]*"|'[^']*'|\S+/g) || []);
}

const unquote = w => w.replace(/^(["'])([\s\S]*)\1$/, '$2');
// "(git", "{git", "push)", "push>log.txt" → the bare word
const clean = w => unquote(w.replace(/^[({]+/, '').replace(/[)}]+$/, '').split(/(?<!^)[<>]/)[0]);

// Words allowed in front of the command itself: env assignments and wrappers that run their argument.
const PREFIX = /^(\w+=\S*|time|env|xargs|nohup|sudo|command|exec|&|call|start|cmd(\.exe)?|\/[ck]|-\S+)$/i;
const SHELL = /^(.*[\\/])?(bash|sh|zsh|pwsh|powershell|cmd)(\.exe)?$/i;
const SHELL_FLAG = /^(-c|-Command|-command|\/c|\/k)$/;

/** Removes heredoc bodies and shell comments, so text inside them is not read as a command. */
function stripNonCode(cmd) {
  const lines = cmd.split(/\r?\n/);
  const out = [];
  let end = null;
  for (const line of lines) {
    if (end !== null) { if (line.trim() === end) end = null; continue; }
    const m = line.match(/<<-?\s*(['"]?)([\w.-]+)\1/);
    if (m) end = m[2];
    out.push(line.replace(/(^|\s)#.*$/, '$1'));
  }
  return out.join('\n');
}

const DESTRUCTIVE = /^(rm|rmdir|del|erase|rd|mv|move|cp|copy|remove-item|ri|move-item|copy-item|set-content|add-content|out-file|new-item|clear-content|truncate|unlink|shred)$/i;
const RISKY_PATH = /(^|[\s"'=\\/])(Library|Packages)([\\/]|["'\s;)]|$)|\.meta(["'\s;)]|$)/i;

/**
 * Splits a command line at && || ; | newline, and at ` / $( that open a substitution, but never inside single quotes
 * (literal text there, e.g. a sed script) and not at ; | && inside double quotes. Quotes stay in the segments.
 */
function segments(cmd) {
  const out = [];
  let cur = '', sq = false, dq = false;
  for (let i = 0; i < cmd.length; i++) {
    const c = cmd[i], two = cmd.slice(i, i + 2);
    if (c === "'" && !dq) { sq = !sq; cur += c; continue; }
    if (c === '"' && !sq) { dq = !dq; cur += c; continue; }
    if (!sq && (c === '`' || two === '$(')) { out.push(cur); cur = ''; if (two === '$(') i++; continue; }
    if (!sq && !dq && (two === '&&' || two === '||')) { out.push(cur); cur = ''; i++; continue; }
    if (!sq && !dq && (c === ';' || c === '|' || c === '\n')) { out.push(cur); cur = ''; continue; }
    cur += c;
  }
  out.push(cur);
  return out;
}

/** Returns {decision, reason} for one command string (nested shells are checked recursively). */
function checkCommand(cmd, depth = 0) {
  if (!cmd || depth > 3) return null;
  let ask = null;
  // Each shell segment separately: "git status && git commit" must still be caught.
  for (const seg of segments(stripNonCode(cmd))) {
    const words = splitArgs(seg.trim());
    const bare = words.map(clean);
    // Nested shell: bash -c "git push", powershell -Command "...", cmd /c "..."
    for (let i = 0; i + 2 < words.length + 1; i++) {
      if (SHELL.test(bare[i]) && SHELL_FLAG.test(bare[i + 1] || '') && words[i + 2]) {
        const inner = checkCommand(unquote(words.slice(i + 2).join(' ')), depth + 1);
        if (inner?.decision === 'deny') return inner;
        ask = ask || inner;
      }
    }
    let head = 0;
    while (head < bare.length && PREFIX.test(bare[head]) && !/^git(\.exe)?$/i.test(bare[head])) head++;
    const word = bare[head] || '';
    if (/^(.*[\\/])?git(\.exe)?$/i.test(word)) {
      let i = head + 1;
      while (i < bare.length && bare[i].startsWith('-')) { i += /^(-C|-c|--git-dir|--work-tree|--namespace)$/.test(bare[i]) ? 2 : 1; }
      const sub = (bare[i] || '').toLowerCase();
      const args = bare.slice(i + 1);
      if (sub && gitWrite(sub, args))
        return { decision: 'deny', reason: `bacon-unity: "git ${sub}" changes the repository. The user manages git (commit / push / merge / branches) themselves. Read-only git (status, diff, log, show, blame) is fine; tell the user what to run instead.` };
    }
    if (/^(.*[\\/])?gh(\.exe)?$/i.test(word)) {
      let i = head + 1;
      while (i < bare.length && /^(-R|--repo|--hostname)$/.test(bare[i])) i += 2;
      const [area, verb] = [bare[i] || '', bare[i + 1] || ''];
      const writes = (/^(pr|release|repo|issue)$/.test(area) &&
          /^(create|merge|close|delete|edit|fork|rename|archive|ready|reopen|review|comment|upload|transfer|lock|unlock|pin|unpin)$/.test(verb))
        || (area === 'api' && bare.some((a, k) => (/^(-X|--method)$/.test(a) && !/^GET$/i.test(bare[k + 1] || '')) || /^(-f|-F|--field|--raw-field|--input)$/.test(a)));
      if (writes) return { decision: 'deny', reason: `bacon-unity: "gh ${area} ${verb}" changes the remote repository. The user manages git themselves.` };
    }
    // Shell commands that delete / overwrite .meta files or Library / Packages content: ask.
    const redirect = seg.match(/>>?\s*("[^"]+"|'[^']+'|\S+)/);
    const destructive = DESTRUCTIVE.test(word) || (/^sed$/i.test(word) && bare.some(a => /^-i/.test(a)));
    if (!ask && ((destructive && RISKY_PATH.test(seg)) || (redirect && RISKY_PATH.test(` ${unquote(redirect[1])} `))))
      ask = { decision: 'ask', reason: 'bacon-unity: this shell command deletes or overwrites .meta files or Library/Packages content. Confirm it is intended (a lost .meta breaks GUID references).' };
  }
  return ask;
}

main(async () => {
  const input = await readInput();
  const tool = input.tool_name || '';
  const ti = input.tool_input || {};
  if (tool === 'Bash' || tool === 'PowerShell') {
    const r = checkCommand(String(ti.command || ''));
    if (r) decide(r.decision, r.reason);
    return;
  }
  const fp = ti.file_path || ti.notebook_path;
  if (fp) checkFile(fp);
});
