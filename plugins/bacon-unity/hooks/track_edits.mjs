// PostToolUse on file edits and Unity MCP write tools: remember what changed since the last CHANGELOG entry and whether
// C# changed without a console read after it (for the Stop reminder), and flag original identifiers written into code / data of clone projects (profile.forbidden_names).
import fs from 'node:fs';
import path from 'node:path';
import { readInput, findProject, relTo, readState, writeState, docs, expandPath, matchesAny, emit, main } from './common.mjs';

function newText(tool, ti) {
  if (tool === 'Write') return ti.content || '';
  if (tool === 'Edit') return ti.new_string || '';
  if (tool === 'MultiEdit') return (ti.edits || []).map(e => e.new_string || '').join('\n');
  if (tool === 'NotebookEdit') return ti.new_source || '';
  return '';
}

function forbiddenHits(profile, text) {
  const fb = profile?.forbidden_names;
  if (!fb?.file || !text) return [];
  const mapPath = expandPath(fb.file);
  if (!fs.existsSync(mapPath)) return [];
  const map = JSON.parse(fs.readFileSync(mapPath, 'utf8'));
  const minLen = fb.min_length || 6;
  const names = new Set();
  for (const sec of fb.sections || ['classes']) {
    const s = map[sec];
    if (s && typeof s === 'object' && !Array.isArray(s))
      for (const [k, v] of Object.entries(s)) if (typeof v === 'string' && k.length >= minLen && k !== v) names.add(k);
  }
  for (const a of fb.allow || []) names.delete(a);
  const hits = [];
  for (const n of names) if (new RegExp(`\\b${n.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`).test(text)) hits.push(`${n} → ${map[(fb.sections || ['classes']).find(sec => map[sec]?.[n])]?.[n]}`);
  return hits;
}

// Unity MCP calls that change scenes / prefabs / assets. Reads (get, list, find, screenshot…) are not changes.
const MCP_READ_ACTION = /^(get|list|find|search|read|info|status|state|ping|screenshot|capture|get_.*|list_.*|find_.*|load|open|validate|inspect|describe)$/i;
const CODE_WRITES = /SetDirty|SaveAssets|SaveScene|MarkSceneDirty|ApplyModifiedProperties|PrefabUtility\.(Save|Apply|Replace|Unpack)|AssetDatabase\.(Create|Delete|Move|Copy|Rename|Import|Refresh)|File\.(Write|Copy|Move|Delete|AppendAll)|Directory\.(Delete|Move)|PlayerSettings\.|EditorBuildSettings\./;

// execute_code that reads the console / compile state counts as the compile check after a C# edit (Stop gate).
const CONSOLE_READS = /LogEntries|isCompiling|CompilationPipeline|compilerMessages/;

function mcpChange(tool, ti) {
  const name = tool.split('__').pop();
  if (/execute_code$/.test(tool)) return CODE_WRITES.test(String(ti.code || '')) ? `[MCP] ${name}` : null;
  if (/execute_menu_item$/.test(tool) && /^Edit\/(Play|Pause|Step)/i.test(String(ti.menu_path || ti.menuPath || ''))) return null;
  const action = String(ti.action || '');
  if (action && MCP_READ_ACTION.test(action)) return null;
  return `[MCP] ${name}${action ? ` ${action}` : ''}`;
}

main(async () => {
  const input = await readInput();
  const tool = input.tool_name || '';
  const ti = input.tool_input || {};

  if (tool.startsWith('mcp__')) {
    if (/__read_console$/.test(tool) || (/execute_code$/.test(tool) && CONSOLE_READS.test(String(ti.code || '')))) {
      const st = readState(input.session_id);
      if (st.csUnchecked) { st.csUnchecked = false; writeState(input.session_id, st); }
      if (/__read_console$/.test(tool)) return;
    }
    const entry = mcpChange(tool, ti);
    if (!entry) return;
    const proj = findProject(input.cwd || process.cwd(), { scanDown: true });
    if (!proj.isUnity) return;
    const st = readState(input.session_id);
    if (!st.edits.includes(entry)) st.edits.push(entry);
    st.root = proj.root;
    writeState(input.session_id, st);
    return;
  }

  const fp = ti.file_path || ti.notebook_path;
  if (!fp) return;
  const proj = findProject(path.dirname(fp));
  if (!proj.isUnity) return;
  const rel = relTo(proj.root, fp);
  const docRel = relTo(proj.docRoot, fp);
  if (!rel && !docRel) return;

  const d = docs(proj.profile);
  const st = readState(input.session_id);
  if ((docRel || '').toLowerCase() === d.changelog.toLowerCase().replace(/\\/g, '/')) st.edits = [];
  else if (!st.edits.includes(rel || docRel)) st.edits.push(rel || docRel);
  if (rel && /\.cs$/i.test(rel)) st.csUnchecked = true;
  st.root = proj.root;
  writeState(input.session_id, st);

  if (rel && /^Assets\/.*\.(cs|json)$/i.test(rel) && !matchesAny(rel, proj.profile?.forbidden_names?.allow_paths)) {
    const hits = forbiddenHits(proj.profile, newText(tool, ti));
    if (hits.length)
      emit({ decision: 'block', reason: `bacon-unity: ${rel} now contains original identifiers (${hits.slice(0, 10).join(', ')}). ` +
        'Project rule: numbers match the original, names never do. Rename using the rename map (add an entry if missing); original names belong only in docs. ' +
        'False positive on a common word → add it to forbidden_names.allow; rip / import tools → forbidden_names.allow_paths.' });
  }
});
