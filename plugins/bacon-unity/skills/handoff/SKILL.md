---
name: handoff
description: Close a work block so the next (cleared) session can resume from the docs - rewrite the plan's "▶ Trạng thái & bước tiếp theo" block, make sure the changelog and spec are consistent, list pending items. Use when the user says "chốt", "handoff", "t clear session", "bàn giao", or at the end of a long work block ("chốt changelog" alone is /log-change).
---

# Handoff

Goal: someone with only the repo docs (no chat history) can continue. The session-start hook prints this block next time.

1. Read `.claude/bacon-profile.json` (`docs.plan`, `docs.changelog`, `docs.mechanics`).
2. **Changelog**: every change of this block has an entry (run `/log-change` for missing ones, per the profile mode).
   Entries say what was not tested.
3. **Spec**: rules implemented or measured in this block are in the spec with the right tag; resolved `[TODO]`s are
   updated. List anything you could not sync.
4. **Plan**: finished steps marked `✅ date`; new decisions added to `Quyết định đã chốt` (Q#, date, who); new questions
   in `Câu hỏi còn mở`; new debug flags / test tools in `Trước khi phát hành`.
5. **Rewrite** (do not append to) the block right under the plan title:

```markdown
## ▶ Trạng thái & bước tiếp theo

- **Ngày:** YYYY-MM-DD
- **Đang ở:** Phase N bước M — <one line>
- **Vừa xong:** <2–5 bullets, with changelog dates>
- **Đang dở:** <what is half done, which files, what state it is in>
- **Tiếp theo:** <ordered next steps>
- **Chờ user:** <tests to run (where to tap, what to look at), art, decisions>
- **Chưa test:** <what was never verified>
- **Lưu ý:** <traps for the next session: editor state, temp files, flags left on>
```

   No block yet → create it right under the title paragraph. Keep it under ~25 lines; details belong in the changelog.
6. Project memory: save only non-obvious lessons or preferences learned in this block (not progress, which lives in
   the plan).
7. Tell the user, in Vietnamese, the 3–5 lines that matter and that the session can be cleared. Never commit.
