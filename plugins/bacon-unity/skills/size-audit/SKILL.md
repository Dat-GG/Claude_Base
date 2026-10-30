---
name: size-audit
description: Use when the user asks why a Unity build (APK / AAB / any player) is big, how to reduce its size or what can be removed, or before a release build.
---

# Build size audit

Tools in this skill (copy / run as written; shell variables do not survive between Bash calls):
- `"${CLAUDE_SKILL_DIR}/BuildSizeAudit.cs"`: Editor script, menu `Bacon/Build/Size Audit (last build)`. Writes
  `Library/SizeAudit/size_audit.md` (+ `assets.tsv`; the previous run becomes `assets_prev.tsv`, the report shows the delta).
- `py -I "${CLAUDE_SKILL_DIR}/who_uses.py" <asset path or name part> [...]`, run from the Unity project folder: reverse
  GUID chains (texture → material → prefab → scene `*` / Resources `*`). Text search: says nothing about active state.

Read-only until the user picks items. Removing assets, editing vendor folders (`Resources` of packs) or `_Project_Base`
follows the normal approval rules.

## 1. A build report that matches the question
- `Library/LastBuild.buildreport` exists after any player build; the audit describes **that** build. Note its date and say
  which later changes it does not include. No report, or a stale one for the question → ask the user to build (or build
  through MCP when the project allows it), then continue.
- An incremental build that reuses cached data lists **no packed assets** (BC54, Unity 6.3: second build, "Build player"
  step 30 s): the menu stops with an error. The APK size is still valid; for per-asset numbers ask for a **Clean Build**
  (Build Profiles → Build dropdown).
- Install the script once: copy `BuildSizeAudit.cs` into the project's editor scripts (`Assets/_Project/Scripts/Editor/Build/`,
  namespace changed to the project's when it is not `Bacon`), refresh, console clean.

## 2. Run the audit
Not in Play mode. Run the menu (it opens the enabled build scenes additively, read-only, and closes the ones it opened;
a scene already open and dirty is left alone). Read `Library/SizeAudit/size_audit.md`.

## 3. Read it with these traps in mind (BC54, 2026-10-27: APK 225 MB, ~125 MB found)
- **Inactive objects ship.** A disabled branch (unused levels, old vehicles, sample content) keeps all its meshes /
  textures in the build. Look at "Scenes" for `(inactive)` branches with MB "only-here".
- **Static batching is invisible in folder views**: `Combined Mesh (root: scene) N` entries (BC54: 40 × 2.5 MB = 77 MB).
  Only active static renderers are combined; deleting inactive objects does not shrink it.
- **Everything under `Resources/` ships**, used or not: pack demos / samples (BC54: RCC demo vehicles + customization
  ~10 MB, I2 examples). Check what code loads them before moving them out, **editor scripts included**: an asset only the
  pack's editor scripts load goes to `<pack>/…/Editor/Resources/` (still found by `Resources.Load` in the Editor, never
  shipped), not to a plain folder (BC54: `RCCP_InitLoad` threw a NullReferenceException on every domain reload).
- **TMP dynamic fallbacks pull whole font files** (BC54: NotoSansJP 6.5 MB through the default font's fallback list) —
  ask which languages really ship.
- **Models with blendshapes / textures above what the original used** (BC54: avatar with 63 face blendshapes 14 MB;
  city atlas 4096 where the original shipped 1024).
- **A reference is not a use**: confirm "unused" with a component scan (serialized references from every build scene and
  prefab) and a grep for names loaded by string (`Resources.Load`, `Find`, Addressables keys), not only `who_uses.py`.
- **Scene overrides hide prefab edits**: while in the scenes, list prefab instance overrides on recently edited prefabs
  (`PrefabUtility.GetPropertyModifications`); a stale override makes the build differ from the prefab (BC54: popup text).

## 4. Proposal list (the deliverable)
Order every finding into four groups, biggest saving first inside each group, one table row per action. MB = packed MB of
the report; give the APK estimate as **≈ 0.6 × packed** for textures (ASTC / ETC included), meshes and fonts: the LZ4
`data.unity3d` still compresses them (BC54: textures −30.7 MB packed → APK −18.9 MB; "compressed textures ≈ 1 : 1" was
wrong). Code size is separate. Say what each row costs in risk and who must check it.

| Group | Meaning | Who decides |
|---|---|---|
| **A** | Safe: no visible / audible / gameplay change (unused branches, sample content, blendshapes nobody drives, duplicate assets) | Claude proposes, user OKs, Claude verifies in Play |
| **B** | Needs a product / plan decision (cut future content, drop a language, remove a feature) | user |
| **C** | Quality trade-off: texture size / compression, audio quality, mesh compression — needs a human eye or ear on device | user looks |
| **D** | Performance or code trade-off: static batching, stripping level, IL2CPP size mode — measure FPS / test on device | user + device test |

Row format: `| A1 | what to change (where) | ~N MB | risk / how it is verified |`. Also list repo-only weight separately (recovery
scenes, test scenes, old builds in the project folder): it does not change the build.
For a cut inside generated content (scenes / prefabs built by an editor tool), the action is "change the generator", not
"delete in the scene".

## 5. After the cuts: compare
Apply only the rows the user picked, one group at a time; log each in the changelog. Rebuild, run the audit again: the
"Change since the previous audit" section gives the delta per folder; report old → new build size and any row that saved
less than estimated (and why).
