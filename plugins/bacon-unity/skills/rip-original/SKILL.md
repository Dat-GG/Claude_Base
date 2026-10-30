---
name: rip-original
description: Use whenever a value, rule, asset or behavior of the original game is needed from its APK / xapk, rip, decompiled code (Ghidra, IL2CPP, Lua, Cocos JS), data files, saves or the live game on LDPlayer - before trying any new tool or approach.
---

# Get it from the original — cheapest proven method first

Every entry in `references/` has: status (✅ proven / 🧪 tried once / ❌ dead end), cost 1 (seconds) … 5 (hours),
when / how / pitfalls / evidence, ordered cheapest first. **Read the matching reference before running anything.**

Tools folder: `${CLAUDE_SKILL_DIR}/tools` — in the references and `tools/README.md` this path is written `<tools>`;
substitute it (and pass the same absolute path to subagents such as reference-researcher). Shell variables do not survive
between Bash calls: write the full quoted path in every command.
Machine paths: `<ghidra>`, `<projects>` etc. are keys of `~/.claude/bacon-machine.json` (printed at session start); read the
file if a key is needed and not printed. Missing key / file → run /setup-machine or ask the user.

## 0. Already known?
- The game's `CLAUDE.md` "Reference sources" table, its workspace `README.md`, `GAME_MECHANICS.md` (the value may already be
  there with its source) and `Research/` reports. A value already in the spec with a source → use it, stop.

## 1. Identify the engine (cost 1, once per game)
Run `py -I "${CLAUDE_SKILL_DIR}/tools/detect_engine.py" <game.xapk | .apk | folder>` (< 1 s, reads the
nested splits in place): engine, Unity version, IL2CPP metadata version, Addressables / YooAsset / asset packs, encryption
and obfuscator hints, biggest native libs, asset file types, and which reference to read. By hand, the signs are
(xapk: also the split `config.arm64_v8a.apk`):

| Found | Engine | Reference |
|---|---|---|
| `lib/*/libil2cpp.so` + `assets/bin/Data/Managed/Metadata/global-metadata.dat` | Unity IL2CPP | `references/engine-il2cpp.md` |
| `assets/bin/Data/Managed/Assembly-CSharp.dll` | Unity Mono | `references/engine-il2cpp.md` (end) |
| `libcocos2dcpp.so` + encrypted `assets/gameres/**.dat`, `jsb_*` symbols | Cocos Creator (JS) | `references/engine-js.md` |
| one big game `.so` (`lib<Game>.so`), no libunity / libil2cpp | native C++ (cocos2d-x / custom) | `references/engine-native-cpp.md` |
| dex only | native Android app | `references/engine-js.md` (custom containers) |
| `libtolua.so` / `libxlua.so` next to `libil2cpp.so` | Unity + Lua (logic in Lua bundles) | `references/engine-il2cpp.md` › Lua-scripted Unity |
| source code available (our own legacy / partner project) | — | read it; ask the user where it is |

`libunitycoherencenative.so` alone is the Unity Ads SDK, not a Unity game. AssetRipper "Unknown backend, no valid assets" →
not Unity.

## 2. Pick the cheapest method that can answer the question
General order (each reference refines it):
1. **Ask / reuse**: the user may have an extracted folder, a video, or the answer; an older workspace may have the tool.
2. **Read data that is already plain**: rip YAML / ScriptableObjects / prefabs, xml / json / level files, bare audio.
3. **Read names and strings**: stub `.cs`, dumper output, `stringliteral.json`, RTTI / symbol strings.
4. **Read code**: per-class decompile export, targeted disassembly (capstone), full Ghidra.
5. **Runtime**: RAM carving, save editing + live measurement on LDPlayer.
6. **Measure**: reference video / screenshots (`/ref-video`), forced resolutions, user playtest (`references/no-data.md`).

Move down only when the level above cannot contain the answer, failed, or is not precise enough; say why in one line.
Data / code values beat measured values; measured values beat guesses.

Shared scripts for every game: `<tools>` (`tools/README.md`: engine detection, Mono decompile, Ghidra queries without
re-analysis, IL2CPP string-literal cross-reference, Unity-side rip helpers in `unity/` (URP material conversion, scene
lighting, script-reference remap, scene MonoBehaviour dump), recovery of lost scripts from old session transcripts).

Also: `references/assets.md` (textures, Spine, fonts, audio, Figma), `references/device-ldplayer.md` (adb, capture, input),
`references/save-files.md` (same state on both sides), `references/workspace.md` (machine tools, workspace layout).

## 3. While working
- Use the machine paths in `references/workspace.md` (`py -I`, ffmpeg path, `MSYS_NO_PATHCONV=1`).
- A ❌ entry is not retried unless something changed (say what).
- Scripts that work go into the workspace `Tools/` with a header, never only in the scratchpad. Output that can grow
  with the input (matches, trees, dumps) prints a capped head (≈ 40–150 lines) plus a count, writes the full result to a
  file and prints its path (the shared tools do this: `il2cpp_literals find`, `scene_mb_dump`, `transcript_find`,
  `who_uses`, `framekit diff / mask`).
- **Stop rule**: ≈ 30 min without progress → stop, report what was tried, ask the user (extracted folder, a recording,
  their eyes / ears, a playtest).
- Results go into `GAME_MECHANICS.md` with the source (`Class::Method @addr`, file:line, prefab path, video + time) and the
  right tag.

## 4. After a new case (always)
When something not in the references was needed — a new engine, tool, trick, workaround, or a dead end that cost time —
run `/add-lesson` to add it to the right reference file: proven status, cost, exact commands, pitfalls, project + date,
inserted in cost order. When a cheaper method replaced an old one, put it above and keep the old as fallback. When an
entry turned out wrong or stale (a tool no longer on disk, a path changed), fix it in the same way.
