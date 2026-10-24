// Stop: with changelog=every-change (the default), remind once when code / assets / scenes changed since the last CHANGELOG entry.
import { readInput, findProject, readState, writeState, docs, changelogMode, emit, main } from './common.mjs';

main(async () => {
  const input = await readInput();
  if (input.stop_hook_active) return;
  const st = readState(input.session_id);
  if (!st.edits.length || !st.root) return;
  const proj = findProject(st.root);
  if (changelogMode(proj.profile) !== 'every-change') return;
  const d = docs(proj.profile);
  const pending = st.edits.filter(r => !/\.md$/i.test(r) && !r.startsWith('.claude/'));
  if (!pending.length) return;
  st.edits = [];
  writeState(input.session_id, st);
  emit({
    decision: 'block',
    reason: `bacon-unity: changes since the last ${d.changelog} entry: ${pending.slice(0, 12).join(', ')}${pending.length > 12 ? ' …' : ''}. ` +
      `Profile changelog=every-change: add the entry now (/log-change format, with Kiểm tra). If the work is not finished or is waiting for ` +
      'the user\'s test, or the edits were temporary diagnostics already removed, say so in one line instead. This reminder fires once per batch.',
  });
});
