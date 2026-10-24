# Project docs format

Every project keeps four files at the Unity project root. Names come from the profile `docs` key; defaults below
(`multi-game`: one spec per game, `docs.mechanics` is a pattern). Templates: `templates/` (`/new-project` copies them).

| File | Role | Changes when |
|---|---|---|
| `CLAUDE.md` | how to work here (English): imports + environment + architecture + reference sources | the setup or architecture changes |
| `GAME_MECHANICS.md` | living spec: **the rules** of the game, with sources | a rule is implemented, measured, or decided |
| `PLAN_*.md` | phases, decisions, open questions, **handoff block** | work advances, a decision is made |
| `CHANGELOG.md` | **history**: what changed, why, how it was verified | every change (per profile) |

Rules live in the spec, status in the plan, history in the changelog. Do not copy one into another; link with § numbers.

---

## `GAME_MECHANICS.md`

Structure:
- Intro: what the doc covers, how to use it, sources (abbreviations used below), tag legend.
- `## 0. Quyết định của dự án` — table `| D# | Quyết định | Nhãn |`: project choices that override the original.
- `# Phần A — Format data gốc` — how the source data is laid out (files, units, coordinates); the module may reshape it
  (`legacy-rebuild`: old → new asset & data map; `pack-reskin`: the pack's structure).
- `# Phần B — Luật chơi` — the rules, one `### B<n>.` per system, each heading tagged, each rule citing its source
  (file:line, symbol + address, video timestamp, data file).
- `# Phần C — Cách đối chiếu` — how to verify against the original (tools, baseline measurements).
- `# Phần D — Bug gốc không tái hiện` / `# Phần E — Quirk giữ lại cho đúng feel` — when relevant.

**Tags** (square brackets, greppable):

| Tag | Meaning |
|---|---|
| `[CONFIRMED]` | read from the original code, or measured on the original |
| `[DATA]` | read from the original data files |
| `[DEFAULT]` | our own choice (placeholder or decision); free to change, must be written down |
| `[TODO]` | unknown: verify **before** coding that part |

Modules add tags (`clone-rip`: `[LD?]` read from code, confirm on the device; `[SCENE]`, `[UI]` read from the rip's scenes /
UI; `legacy-rebuild`: `[OLD?]` read from legacy code, confirm by playing the legacy build). When a `[TODO]` is resolved, update the tag in the
same change.

## `PLAN_*.md`

Structure, top to bottom:
1. `# Plan: <project> — <current goal>` + one paragraph: goal and what matters most.
2. **`## ▶ Trạng thái & bước tiếp theo`** — the handoff block, rewritten (not appended) by `/handoff`:
   fields `Ngày`, `Đang ở`, `Vừa xong`, `Đang dở`, `Tiếp theo`, `Chờ user`, `Chưa test`, `Lưu ý` (traps for the next
   session) — same as the template and `/handoff`. Keep it under ~25 lines; details go to the changelog / plan sections.
3. `## Quyết định đã chốt` — table `| Q# | Quyết định | Ngày (người chốt) |`. Never renumber.
4. `## Câu hỏi còn mở` — numbered; move to Q# when answered.
5. `## Trước khi phát hành` — checklist of release blockers (debug defines, unlock flags, test tools, temporary assets).
6. `## Cách đảm bảo giống gốc` (clone / rebuild projects) — measurement method, feel checklist.
7. `## Cấu trúc code / asset` — folder tree.
8. `## Phase N — <name>` — numbered steps, `✅` + date when done, each phase ends with **Mốc:** (milestone, how it is checked).

## `CHANGELOG.md`

Header: one line on what the log tracks + the entry format. Then `## [Unreleased]`, newest entry first.
Milestones become `## [0.x.0] — YYYY-MM-DD — <title> (user đã test)` with a short summary above their entries.

Entry:

```markdown
#### YYYY-MM-DD — <Added|Changed|Fixed|Removed|Notes>: <title> (<user duyệt> if approved outside plan)
- **Nguyên nhân** (fixes): the measured root cause, with the original's reference when relevant.
- **Fixed / Added / Changed** `<file or asset>`: what changed and why.
- **Kiểm tra**: how it was verified (Play scenario, numbers, comparison with the original); what was NOT tested.
- **Notes**: open points, side findings, wrong earlier diagnosis (say it plainly).
- Files: `a.cs`, `b.prefab`, … · Docs: `GAME_MECHANICS.md` (B4c)
```

Rules:
- One entry per logical change; several small fixes of one topic may share an entry.
- `Kiểm tra` is mandatory for code / asset changes.
- Record dead ends that cost time ("đã thử X, không được vì Y") so they are not retried.
- When the file passes ~100 KB, move released milestones to `CHANGELOG_ARCHIVE.md` (keep `[Unreleased]` and the latest
  milestone).
