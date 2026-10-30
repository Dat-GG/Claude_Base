---
name: setup-machine
description: Use on a new PC / laptop, after moving tool or studio folders, when session start says ~/.claude/bacon-machine.json or the ~/.claude/bacon-standard link is missing, or when the user says "cài máy mới", "setup máy", "chuyển sang laptop", "check máy".
effort: low
---

# Set up this machine

Doctor script: `node "${CLAUDE_SKILL_DIR}/doctor.mjs"` (write the full quoted path in every command). It never installs
anything. Reply to the user in Vietnamese.

## 1. Check
Run `node "${CLAUDE_SKILL_DIR}/doctor.mjs"`. It prints each key (saved value, detected value, status), the link
`~/.claude/bacon-standard`, Node, Python libs, whether the plugin is installed and whether `~/.claude/CLAUDE.md` matches
the studio's personal rules.

## 2. Save the paths
- `node "${CLAUDE_SKILL_DIR}/doctor.mjs" write` saves detected values for keys not saved yet (a `.bak` is kept).
  `--force` replaces saved values with detected ones: only when the user says the old paths are wrong.
- Keys the script cannot guess or got wrong (`studio`, `projects`, a second Ghidra…): ask the user, then
  `node "${CLAUDE_SKILL_DIR}/doctor.mjs" set projects=E:/Work/Project`.
- Keys = tokens in the docs: `standard` (the Claude_Base repo), `studio` (studio root: Project/, Tools/, xapks),
  `projects`, `tools-home` (where RE tools are installed), `ghidra`, `ghidra-projects`, `jdk17`, `il2cppdumper` (folder),
  `cpp2il`, `assetripper`, `dotnet` (DOTNET_ROOT), `ilspycmd`, `ldplayer` (folder with adb.exe), `adb-device`,
  `unity-editors` (Hub editor folder), `python` (command prefix, `py -I`), `ffmpeg` (empty = imageio's).
- A new tool location in a lesson → a new key: add it here (`set`) and in this list.

## 3. Link the standard
`node "${CLAUDE_SKILL_DIR}/doctor.mjs" link` makes the junction `~/.claude/bacon-standard` →
`<standard>/plugins/bacon-unity`. Project `CLAUDE.md` files import `@~/.claude/bacon-standard/standards/core.md` etc.,
so they work wherever the repo lives. The first session in each project asks once to approve these external imports:
tell the user to accept.

## 4. Personal rules and plugin
- `~/.claude/CLAUDE.md` missing or different from `<standard>/user/CLAUDE.md`: show the difference and copy it only after
  the user agrees (it may hold their own rules).
- Plugin not installed: tell the user to run `claude plugin marketplace add <standard>` and
  `claude plugin install bacon-unity@gg-snm` (or do it after they agree), then open a new session.

## 5. Missing tools
For every missing key the script prints the source and install command. Ask the user which ones to install (only the
ones their work needs: Ghidra for native games, Il2CppDumper / Cpp2IL / AssetRipper for Unity IL2CPP, .NET + ilspycmd for
Unity Mono, LDPlayer for live tests). Install only after a yes, into `<tools-home>`, then run `write` again.
- Python libs: `py -m pip install -r "${CLAUDE_SKILL_DIR}/requirements.txt"` (after a yes).
- Analyzed Ghidra projects and the ripper workspaces are data, not tools: copy them from the old machine
  (`<tools-home>/ghidra_projects`, `<projects>/*_Ripper`), or re-create them per `/rip-original`.

## 6. Finish
Run the check again and report in a short table: ready / missing (what it blocks) / skipped by the user.
