# Module: legacy-rebuild — rewrite one of our own older projects

For projects that rebuild an internal game whose old Unity project still exists (DF ← `Fightinggame`): same content and
feel, all logic rewritten on the Bacon base, legacy bugs fixed.

## The legacy project

- **Read-only reference**: never edit it, never commit / tag it, never copy its scripts. Re-implement from the spec (DF).
  Its path, Unity version and old script folders go in the "Reference sources" table of `CLAUDE.md`.
- The spec cites legacy paths with short prefixes defined in its intro (DF `CS/`, `P:Player`).
- Legacy code may **overwrite serialized values at runtime** (DF: the old Spine bridge forced `timeScale`, hiding a prefab
  saved with 0). Before trusting a converted prefab, grep the old code for runtime writes (`timeScale`, `isTrigger`,
  `gravityScale`, `bodyType`, `enabled`, volume / mute, sorting layer) and audit the converted prefabs for them (DF
  `Bacon/Data/Audit Prefabs`).

## Assets and data

- Move assets **with their `.meta`** (GUIDs kept) into `_Project/` by type; old prefabs / data / scenes used only as a
  source go under `Legacy/` subfolders (`Prefabs/Legacy`, `Data/Legacy`, `Scenes/Legacy` not in the build) (DF).
- Converters live in `Bacon/Migrate/*` (legacy prefab / map / UI → new prefabs). A fix to converted output goes **into
  the converter** too, or the next rebuild undoes it. Before changing a converter, rerun it and diff a full snapshot of its
  outputs against the current assets (0 differences = no hand edit will be lost); diff again after (DF).
- Static config (levels, characters, skins…) moves into ScriptableObject catalogs; the old save format (e.g. Easy Save) is
  replaced by the base save (DF Q2: never released, so no save migration; a shipped legacy game needs one: ask).

## Bacon base from a newer Unity (only when the user asks)

Normally the user prepares the base project and sends its path. Only when the user asks to port the base from a newer
project (DF: BC46 base, Unity 6, into an older Unity):
copy **scripts / prefabs / art only**, never scenes, TMP font assets or other Unity-6-serialized assets as-is. Rebuild the
boot scenes with an editor builder (`Bacon/Setup/Build Main Scene`); regenerate TMP SDF atlases on the target TMP version
(`ClearFontAssetData`); vendor plugins built for the newer Unity may need the older project's copy (DF).

## Spec (`GAME_MECHANICS.md`)

- **Part A becomes the old → new map**: legacy asset / data path → new path table, plus which data moved where.
- Part B cites legacy files (`file:line`, prefab + component field). Part D lists legacy bugs that **must not be
  reproduced**; Part E the quirks to keep for the feel. Pending `[TODO]`s may be collected in a Part F (DF).
- Tag added by this module: **`[OLD?]`** = read from legacy code / prefab, confirm by playing the legacy build.
- Verification: the legacy project still opens in its Unity version; feel baselines (videos + numbers) live outside
  `Assets/` (`Docs/Baseline/`) and in Part C.
