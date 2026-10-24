# Ripper workspace and machine setup

## Machine (verified 2026-10-21)

Locations: `~/.claude/bacon-machine.json` (created by /setup-machine); the values below are the reference machine.

| Tool | Where | Notes |
|---|---|---|
| Python 3.14.6 | `<python>` (reference machine: `py -I`, the launcher) | bare `python` in Git Bash is the MS Store alias ("Python was not found") |
| Python libs | capstone 5.0.7, pyelftools, UnityPy 1.25.3, numpy 2.5, opencv-python-headless 5.0, Pillow 12.3, imageio 2.37, imageio-ffmpeg 0.6, texture2ddecoder, pymupdf | **no** scipy / skimage |
| ffmpeg 7.1 | `<ffmpeg>`; empty = `imageio_ffmpeg.get_ffmpeg_exe()` (the reference machine) | not on PATH; **no ffprobe** (use `ffmpeg -i` or cv2) |
| Ghidra 11.0.3 | `<ghidra>`, projects `<ghidra-projects>/` | Java = Unity 6 JDK 17 `<jdk17>` (`<unity-editors>/6000.3.16f1/Editor/Data/PlaybackEngines/AndroidPlayer/OpenJDK`) |
| Il2CppDumper 6.7.46 | `<il2cppdumper>` | `RequireAnyKey:false` |
| Cpp2IL 2022.1.0-pre.20 | `<cpp2il>` | |
| AssetRipper 1.3.14 | `<assetripper>` | GUI + `--headless --port 5555` |
| adb / ldconsole | `<ldplayer>/`, device `<adb-device>` | `device-ldplayer.md` |
| Unity editors | 2022.3.62f3, 6000.3.16f1 (`<unity-editors>/<version>/Editor/Unity.exe`) | open rips in the matching version |
| REA (morluto/rea) | `npx -y rea-agents@<version> <command>` (CLI, nothing registered) | MCP not registered: its `setup` writes a **user-wide** MCP entry + skill; if ever adopted, register per workspace with `claude mcp add --scope project` instead. Results: `engine-il2cpp.md` (IL2CPP decoder not released yet, managed members 🧪), `engine-native-cpp.md` (❌ Ghidra provider for `.so`) |
| ❌ XERJ (xerj-org/xerj) | removed 2026-10-21 (user: "không đáng") | local search server indexing `Decompiled/` for the researcher agent. A/B on the E2D crate + camera questions: −34 % agent tokens (125 k → 82 k), 36 → 20 tool calls, 340 → 134 s, same accuracy; but lexical-only search missed `CarCamera.c` (fell back to `ls`), needs a background server + 3 min indexing, and its output keeps telling agents to auto-submit field reports to GitHub / xerj.org. Not worth it over grep + `reference-researcher`. Re-test only if it gains good semantic search offline |
| .NET SDK 10.0.402 | `<dotnet>` (user install via `dotnet-install.ps1`, **not on PATH**) | set `DOTNET_ROOT=<dotnet>` when calling .NET tools; telemetry off with `DOTNET_CLI_TELEMETRY_OPTOUT=1` |
| ilspycmd 11.1 | `<ilspycmd>` | Mono / .NET decompiler, wrapped by `<tools>/mono/mono_decompile.py` |
| Not installed | AssetStudio, dnSpy, ILSpy GUI, astcenc, Frida | ask the user before installing anything |

Always in Git Bash: `export MSYS_NO_PATHCONV=1 PYTHONIOENCODING=utf-8`.

## Workspace layout

New game → `<projects>/<Name>_Ripper/` (copy the layout of `E2D_Ripper` / `Urban_Food_Ripped`):

```
README.md          what is where, versions, package id, which xapk was ripped
GameApk/           the xapk / apks (the exact version that was ripped)
GameAssets/        extracted + converted data
Decompiled/        Ghidra / dumper / Cpp2IL output, AssetRipper project (or a sibling <Name>_Ripped/)
Research/0N_<system>.md
Tools/             every reusable script (python, .bat, ghidra scripts), ld_tool.py, <game>_save_tool.py
Tools/_save/       device saves (dated backups), screenshots, recordings (baseline/, ld/, ld/user/)
```

## Rules

- **Every script that worked goes into `Tools/`**, never only in a session scratchpad: four Ghidra query scripts (E2D) and the
  literal cross-reference tools (HMR) were lost that way and had to be rewritten. Give each a header: purpose, usage,
  inputs, outputs, proven date.
- Generic tools shared by all games live in the skill: `<tools>` (path in `SKILL.md`; engine detection, Mono decompile,
  Ghidra queries, IL2CPP literal cross-reference, Unity-side rip helpers, transcript recovery); see `tools/README.md`.
- A script that existed in an old session but is gone from disk: `node "<tools>/transcript_find.mjs" "<file name regex>"
  [--project <name>] --full` searches every session transcript, subagent runs included (`~/.claude/projects/*/*.jsonl`
  and `~/.claude/projects/*/<session>/subagents/*.jsonl`), for the Write / heredoc that created it. Old scratchpad folders under `%TEMP%\claude\` are usually emptied.
- Copy proven tools from older workspaces and edit their constants (package, paths, SO / dump paths): faster than writing
  new ones. Index of what exists: the "Tools" lines in `engine-*.md`, `device-ldplayer.md`, `save-files.md`.
- The workspace is read-only reference from the game project. Never commit decompiled code or rip output into the game
  repo. Never copy SDK keys / ad ids.
- Record the technique, path and version of each source in the game's `CLAUDE.md` "Reference sources" table.
