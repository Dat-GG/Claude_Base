---
name: new-project
description: Use when starting a new Unity game project, or bringing an existing project onto the bacon-unity standard - the user says "tạo project mới", "đưa project lên chuẩn", "chuyển project sang chuẩn".
---

# New / adopt project

Standard root: `<standard>/plugins/bacon-unity` (call it `STD`; `<standard>` and other `<key>` paths are keys of
`~/.claude/bacon-machine.json`, printed at session start). Templates in `STD/templates`, shared rules in `STD/standards`,
optional modules in `STD/modules`. Projects import the standard through `@~/.claude/bacon-standard/...` (a junction to
`<standard>/plugins/bacon-unity` made by /setup-machine), never through an absolute path.

## 0. The Bacon base project
- Normal case: the user creates the base project (with `Assets/_Project_Base`) and sends its path. Work in that project;
  never create, copy or assemble the base yourself. No path yet → ask for it and wait.
- Exception, only when the user asks for it (DF): port the base from another project. Then copy with `.meta` files, remove
  the source game's code from the base, and on an older Unity copy scripts / prefabs / art only (no scenes, TMP font
  assets or other newer-serialized assets; rebuild boot scenes, regenerate TMP atlases). List each change in the first
  changelog entry.

## 1. Detect
- Unity project root (folder with `ProjectSettings/ProjectVersion.txt`). Read the Unity version, render pipeline
  (`ProjectSettings/GraphicsSettings.asset`, URP assets), color space, `activeInputHandler`, scripting defines,
  `Packages/manifest.json` (Unity MCP package: `com.coplaydev.unity-mcp` → `coplay`, `com.ivanmurzak.unity.mcp` →
  `ivanmurzak`), vendor folders under `Assets/`, `_Project_Base` presence.
- Existing docs (`CLAUDE.md`, any spec / plan / changelog, `GamePlan/`, `Docs/`, `Mechanic.md`) and project memory.
- Existing `.claude/bacon-profile.json` → the project is already on the standard: only offer an update.

## 2. Ask (one AskUserQuestion round, Vietnamese, recommended option first)
- **Type** (one) — decides the type module:

  | `type` | When | Type module |
  |---|---|---|
  | `clone-rip` | rebuild a released third-party game from its APK / rip (BC46, BC54, BCA30) | `clone-rip` |
  | `legacy-rebuild` | rewrite one of our own older Unity projects (DF ← Fightinggame) | `legacy-rebuild` |
  | `pack-reskin` | an asset-store game pack / template is the game, re-skinned (P09, BC23T) | `pack-reskin` |
  | `original` | own design, no reference game (BCA17) | none |

- **Tech / shape modules** (any number, only files that exist in `STD/modules`): `spine-2d` (Spine characters / UI),
  `world-3d` (one big 3D world scene + controller packs), `multi-game` (hub of mini-games, one scene each). Propose the
  ones the detection supports (Spine runtime folder, URP 3D scenes, a `MiniGameData` registry).
- Reference sources (ripper workspace, legacy project path, Figma link), dev save file name.
- Profile switches only if the user wants something other than the defaults
  (`changelog: every-change`, `self_test: full`, `comment_language: en`).

## 3a. New project (no docs yet)
- Copy the templates, fill every `{{…}}` from what was detected / answered:
  - `{{TODAY}}` = today. Imports are written `@~/.claude/bacon-standard/...` (the junction, never an absolute path).
  - `modules` in the profile = the type module first, then the tech modules (`original` with none → `[]`);
    the template's `["{{TYPE_MODULE}}"]` becomes that list. `{{MODULE_IMPORTS}}` = one
    `@~/.claude/bacon-standard/modules/<m>.md` line per entry.
  - `{{MODULE_TAGS}}` (spec intro, Vietnamese) = the tags the chosen modules add, e.g. clone-rip: `; [LD?] = đọc từ code,
    cần xác nhận trên LDPlayer; [SCENE] / [UI] = đọc từ scene / UI của bản rip`; legacy-rebuild: `; [OLD?] = đọc từ code /
    prefab bản cũ, xác nhận bằng cách chạy bản cũ`; none → empty.
  - `{{SETTINGS_APPLY}}` = the project's settings-apply menu if it has one, else remove the clause.
  - `{{MEASURE_METHOD}}` = how the copy is compared with the original / legacy build; `original` → delete that plan section.
  - Unknown values stay as a visible `TODO:` line, never invented.
- `.claude/bacon-profile.json`: `protected` = the vendor folders found under `Assets/` (DOTween / Demigiant, Sirenix, Spine,
  Plugins, SDKs, asset-store packs) **except** the game pack of a `pack-reskin`; `ask` = `Assets/_Project_Base/**`;
  `save_file` = `%USERPROFILE%/AppData/LocalLow/<company>/<product>/<applicationIdentifier>.gd` from PlayerSettings.
- The first CHANGELOG entry records the setup.

## Profile keys (`.claude/bacon-profile.json`)

| Key | Values | Meaning |
|---|---|---|
| `standard` | `bacon-unity@<major.minor>` | standard version the profile was written for (informational) |
| `project` | name | project name; also the backup folder `~/.claude/bacon-backups/<project>/` |
| `type` | `clone-rip` · `legacy-rebuild` · `pack-reskin` · `original` | what the project is rebuilt from (table in step 2) |
| `modules` | list | rule files under `modules/` imported by `CLAUDE.md`; includes the type module |
| `mcp` | `coplay` · `ivanmurzak` · `none` | which Unity MCP server is wired in |
| `changelog` | `every-change` (default) · `after-user-test` · `on-request` | when to write the changelog |
| `self_test` | `full` (default) · `runtime-only` · `none` | see `core.md` "Workflow profile" |
| `comment_language` | `en` (default) · `vi-ascii` | language of code comments |
| `docs` | `{plan, mechanics, changelog}` | doc paths from the doc root; `mechanics` may be a per-game pattern (`GamePlan/<Game>/<Game>.md`, `multi-game`) |
| `save_file` | path (env vars allowed) | dev save backed up before Play |
| `protected` | globs | Edit / Write blocked (vendor folders) |
| `ask` | globs | Edit / Write needs explicit confirmation (`Assets/_Project_Base/**`) |
| `allow_packages` | bool (default false) | `true`: Edit / Write under `Packages/` without the confirmation prompt |
| `forbidden_names` | `{file, sections, min_length, allow, allow_paths}` or `null` | clone projects: original identifiers from the rename map `file` (`sections`, default `["classes"]`) flagged in `Assets/**/*.cs|json`; names shorter than `min_length` (default 6) ignored; `allow` = words never flagged; `allow_paths` = globs skipped (e.g. `Assets/**/Editor/**` rip / import tools) |

## 3b. Adopt an existing project (has docs)
- **Never overwrite.** Write the proposal inside the project being adopted, `<project root>/.claude/bacon-migration/`
  (project data never goes into the standard repo; old memories archived there too):
  - `CLAUDE.md` rewritten as imports + only the project-specific sections (keep every project fact; drop only text the
    standard now carries, and list each dropped rule with the standard line that covers it);
  - `bacon-profile.json`;
  - `MIGRATION.md`: what moves where, rules of the old file that conflict with the standard (ask how to resolve), doc
    format gaps and the proposed fix, memories that duplicate the standard and can be deleted.
- Doc shapes met so far and their fix:
  - Handoff kept as "Notes: trạng thái + việc tiếp theo" entries at the top of the changelog (DF) → move the latest into
    the plan's `▶ Trạng thái & bước tiếp theo` block; the changelog keeps history only.
  - Plan, baseline and changelog in one file (P09 `CHANGELOG.md` with sections 0–7 + "Nhật ký thay đổi") → split into
    `PLAN_*.md` (status, risks / decisions, phases), the spec (rules, data) and `CHANGELOG.md` (dated entries).
  - Handoff block far over the format (BC54 ~95 lines) → trim to ≤ 40 lines (target ~25), details go to plan sections
    or the changelog.
  - Spec with other confidence marks (BCA30 ✅ / 🟡 / ⚠️) → propose a mapping to the tags, ask before rewriting.
  - Changelog without **Kiểm tra**, decision tables without D# / Q# → fix new entries only, do not rewrite history.
- Show the user the diff summary; apply to the project only after approval, file by file.
- Old projects that are finished are not migrated unless the user asks.

## 4. Finish
- Tell the user what was created, what is still `TODO:`, and that the external import (`@~/.claude/bacon-standard/...`) asks for approval the
  first time Claude Code loads the CLAUDE.md. Never commit.
