// Stop: remind once per batch when (a) C# changed and the console was not read after it (verify before reporting done),
// or (b) with changelog=every-change (the default), code / assets / scenes changed since the last CHANGELOG entry.
import { readInput, findProject, readState, writeState, docs, changelogMode, emit, main } from './common.mjs';

main(async () => {
  const input = await readInput();
  if (input.stop_hook_active) return;
  const st = readState(input.session_id);
  if (!st.root) return;
  const proj = findProject(st.root);
  if (!proj.profile) return;
  const reasons = [];
  if (st.csUnchecked) {
    st.csUnchecked = false;
    reasons.push('C# changed and the console was not read since: refresh, wait for compilation, read the console ' +
      '(0 errors) before reporting done (core.md "After script edits"). If it cannot be checked now (editor closed, ' +
      'user playing), say so in the report.');
  }
  const d = docs(proj.profile);
  const pending = st.edits.filter(r => !/\.md$/i.test(r) && !r.startsWith('.claude/'));
  if (pending.length && changelogMode(proj.profile) === 'every-change') {
    st.edits = [];
    reasons.push(`Changes since the last ${d.changelog} entry: ${pending.slice(0, 12).join(', ')}${pending.length > 12 ? ' …' : ''}. ` +
      `Profile changelog=every-change: add the entry now (/log-change format, with Kiểm tra). If the work is not finished or is waiting for ` +
      'the user\'s test, or the edits were temporary diagnostics already removed, say so in one line instead.');
  }
  if (!reasons.length) return;
  writeState(input.session_id, st);
  emit({ decision: 'block', reason: `bacon-unity: ${reasons.join(' ')} This reminder fires once per batch.` });
});
