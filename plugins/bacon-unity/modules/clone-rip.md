# Module: clone-rip — rebuild a released game from its extracted data

For projects that follow an original game we do not own (BC45, BC46, BC54…): data and code are extracted from the APK,
logic is re-implemented, art is replaced before release.

## Ripper workspace (outside the Unity repo, read-only from the project)

`<projects>/<Name>_Ripper/` (or `<Name>_Ripped`; `<projects>` and the other `<key>` paths are keys of `~/.claude/bacon-machine.json`), same layout every time:

| Folder | Content |
|---|---|
| `GameApk/` | the original xapk / apk, extracted |
| `GameAssets/` | extracted data and assets (converted to readable formats) |
| `Decompiled/` | Ghidra / Il2CppDumper / Cpp2IL output, AssetRipper project |
| `Research/0N_<system>.md` | one report per system: pseudo-code, exact constants, original symbol + address, Unity notes, open questions |
| `Tools/` | python tools: data builder, converters, rename map, save tool, device tool (`ld_tool.py`), `_save/` for captures |

The project's `CLAUDE.md` has a "Reference sources" table pointing at these paths.
Never commit decompiled code, rip output or tool output into the game repo (only the generated game data the project uses).

## Rules

- **Numbers exact, names new**: every numeric parameter matches the original; **no original identifier** (class, method,
  field, data key, template / clip / sound name) appears in C# or JSON. New names come from the rename map
  (`Tools/rename_map.json`); add entries there when needed. Original names appear only in docs, for lookup.
  The profile's `forbidden_names` makes a hook flag original class names written into code.
- **Original assets are temporary**: keep them in an `Original/` subfolder of their type (`Art2D/Original`, `Audio/Original`,
  `Prefabs/Original`…); our own assets stay outside. Replacement art follows the project's override pipeline.
- **No original branding** in the product (logos, titles, promo art) even when the original stamps it on a feature.
- **Never copy** SDK keys, ad unit ids or analytics ids from the rip. Never copy stripped / stub scripts from an IL2CPP rip:
  read their field names and serialized values, re-implement the logic.
- Third-party DLLs in the rip are unlicensed copies: never ship them; use the same pack / package and version from a
  licensed source (BC54: RCCP 1.37.0, UPM packages instead of ripped Cinemachine / TMP / DOTween DLLs).
- **Physics / time like the original**: copy its gravity, fixed step, iterations and collision matrix into spec B0 and
  `ProjectSettings`. When the original steps physics in its own loop, step it the same way from code (BC46: Box2D 1/120 s →
  `Physics2D.simulationMode = Script` + `PhysicsStepper`; gameplay physics in `OnPhysicsStep`, not `FixedUpdate`).
- Serialized values in the rip beat values measured from video; video beats guesses.
- **Units**: the original's units stay in the data; convert in exactly one place in code (`<Project>Units`), never ad hoc.

Methods for extracting data, saves and device work: `/rip-original` (proven playbook, cheapest first).
Frame-by-frame measurement: `/ref-video`.

## Verifying against the original

- The original runs on LDPlayer (root). adb from `<ldplayer>/adb.exe`, device `<adb-device>`; from Git Bash
  prefix with `MSYS_NO_PATHCONV=1`. Turning wifi off inside Android drops adb: reboot the instance with `ldconsole`.
- Same state on both sides: edit the original's save with the project's save tool, set the same progress in Unity.
- Scripted inputs on both sides (device tool on LD, scripted input in Unity), compare measured numbers and side-by-side
  recordings. Baselines go into `GAME_MECHANICS.md` Part C.
- Spec tags added by this module: `[LD?]` (read from code, confirm on the device), `[SCENE]` / `[UI]` (read from the rip's
  scenes / UI). Keep an `[LD?]` checklist in the plan.
