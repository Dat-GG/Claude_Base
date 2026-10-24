---
name: log-change
description: Write a CHANGELOG.md entry in the studio format (date, type, root cause, change, Kiểm tra, Files) for the change just made, and sync the spec / plan references. Use after any code, asset, prefab, scene or tool change in a project on the bacon-unity standard, or when the user says "ghi changelog" / "chốt changelog".
---

# Log a change

1. Read `.claude/bacon-profile.json`: `docs.changelog` (file name) and `changelog`
   (`every-change` → write now; `after-user-test` → write only once the user confirmed the test, otherwise say the entry
   is pending; `on-request` → only when the user asked).
2. Read the top of the changelog (header + the newest 2–3 entries) to match the exact local style. Do not read the
   whole file.
3. Collect the facts from this session: what changed and why, the measured root cause (fixes), how it was verified,
   what was **not** verified, files touched (code, prefabs, scenes, assets, tools outside the repo), spec / plan
   sections updated.
4. Insert the entry under `## [Unreleased]`, **newest first**, in Vietnamese:

```markdown
#### YYYY-MM-DD — <Added|Changed|Fixed|Removed|Notes>: <title> (<user duyệt> when approved outside the plan)
- **Nguyên nhân** (fixes): measured root cause; reference to the original when relevant.
- **Fixed / Added / Changed** `<file>`: what and why.
- **Kiểm tra**: scenario + numbers; what was NOT tested and why.
- **Notes**: open points, dead ends ("đã thử X, không được vì Y"), corrections of an earlier wrong diagnosis.
- Files: `...` · Docs: `GAME_MECHANICS.md` (§…), `PLAN_*.md` (Phase …)
```

5. Several entries for the same day are fine; merge only when they are one topic.
6. If the change resolved a `[TODO]` or added a `[DEFAULT]`, check the spec was updated in the same change; if a plan
   step finished, mark it `✅ date` in the plan.
7. File larger than ~100 KB → propose moving released milestones to `CHANGELOG_ARCHIVE.md` (ask first).
8. Never commit; tell the user the entry is written (git is theirs).
