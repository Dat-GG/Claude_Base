---
name: add-lesson
description: Add a lesson learned in a project to the shared bacon-unity standard (the Claude_Base repo, key `standard`) so every later project knows it - pick the right place (core rule, module, skill step, hook), check for duplicates and conflicts, show the diff, apply after approval, bump the plugin version when needed. Use when the user says "ghi bài học này vào chuẩn chung", "update vào plugin", "để project sau biết", or asks to add / change a shared rule.
---

# Add a lesson to the shared standard

Standard repo: `<standard>`, plugin `<standard>/plugins/bacon-unity` (`PLG`). The user owns git there: never commit.
Machine paths: `<standard>`, `<projects>`, `<ghidra>` etc. are keys of `~/.claude/bacon-machine.json` (printed at session
start); read the file if a key is needed and not printed. Missing key / file → run /setup-machine or ask the user.
Projects import the standard through `@~/.claude/bacon-standard/...` (a junction to `<standard>/plugins/bacon-unity` made
by /setup-machine).

## 1. State the lesson
Write it as one rule + why, in English (standard files are English; the explanation to the user is Vietnamese):
- **Rule**: what to do / never do, concrete (names the API, menu, file, tool).
- **Paths**: never an absolute machine path. Write `<key>` / `<key>/sub/path` with a key of `~/.claude/bacon-machine.json`
  (`<projects>/E2D_Ripper/Tools/readdat.py`, `<ghidra>/support/analyzeHeadless.bat`). A new tool location needs a new key:
  tell the user to add it via /setup-machine.
- **Why**: the incident that taught it (project, date, what broke, cost). One or two lines.
- **Scope**: every Unity project? only one project type (clone-rip, legacy-rebuild…)? one tech (Spine, 3D, 2D physics)?
  only this project? If only this project → it belongs in the project's `CLAUDE.md` or memory, not the standard: say so and stop.

## 2. Pick the place
| The lesson is… | Goes to |
|---|---|
| a short always-on rule (code, Unity safety, workflow, MCP gotcha) | `PLG/standards/core.md`, in the matching section |
| about the Bacon base framework | `PLG/standards/bacon-framework.md` |
| about doc format (spec tags, plan blocks, changelog fields) | `PLG/standards/docs-format.md` (+ `PLG/templates/` if the template changes) |
| specific to a project type or tech | `PLG/modules/<name>.md`; create the module when missing (same shape as `clone-rip.md`) and list it in `README.md` and in `skills/new-project` step 2 |
| a step of a multi-step procedure (testing, importing art, handoff…) | the matching `PLG/skills/<name>/SKILL.md`, or a new skill when no procedure fits |
| a way to get information out of the original game (tool, command, trick, dead end) | `PLG/skills/rip-original/references/<file>.md`, as an entry in that file's format (status ✅ / 🧪 / ❌, cost 1–5, when / how / pitfalls / evidence), inserted in cost order; a cheaper proven method goes above the old one, which stays as fallback |
| a frame / video measurement technique | `PLG/skills/ref-video/` (SKILL.md, or the script when it needs a new subcommand) |
| must be enforced, not remembered (block, ask, auto-backup, reminder) | `PLG/hooks/*.mjs` + `hooks.json`; also add the rule text to `core.md` so Claude knows why it is blocked |

Prefer the lightest place: a rule line beats a skill step, a skill step beats a hook.

## 3. Check before writing
- Grep the whole plugin for the topic: is it already covered? Then sharpen the existing line, do not add a duplicate.
- Does it **contradict** an existing rule or a profile switch? Show both and ask which wins (or whether it should become a
  profile switch, documented in the "Profile keys" table of `skills/new-project/SKILL.md`, in
  `templates/bacon-profile.json`, and in `core.md` "Workflow profile" when it changes how Claude works every session).
- Keep the file's style: same section, same bullet density, no story-telling (the "why" is one clause in the rule, or one line).

## 4. Show, then apply
- Show the user the exact diff (file + lines) and the reason for the chosen place, in Vietnamese. Wait for OK.
- Apply. For hooks: test with simulated input
  (`BACON_PROFILE=<profile> BACON_PROJECT_ROOT=<unity project> node PLG/hooks/<hook>.mjs < input.json`), both the case
  that must trigger and one that must not.
- `claude plugin validate <standard>` passes.

## 5. Make it live
- `standards/` or `modules/` only: live in the next session (projects import them straight from the repo). Nothing else.
- `skills/`, `hooks/`, `templates/`: bump `version` in `PLG/.claude-plugin/plugin.json` (patch +1), then run
  `claude plugin marketplace update gg-snm` and `claude plugin update bacon-unity@gg-snm`; the change applies to new sessions.
- Add a bullet to `<standard>/CHANGELOG.md` under a `## <version> — <date>` heading (newest first;
  `<version>+` when only `standards/` / `modules/` changed): file — rule (source project).
- If the lesson came from a project memory, offer to delete that memory now that the standard carries it.
- Tell the user what changed and remind them the standard repo is theirs to commit.
