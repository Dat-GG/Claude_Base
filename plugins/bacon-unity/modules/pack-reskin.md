# Module: pack-reskin — an asset-store game pack with new art

For projects whose game is an asset-store pack / template (P09 ← MultiTechStudio Cooking2D, "almost the whole game is in
it"; BC23T ← Highway Racer) re-skinned from Figma, with the Bacon base around it.

## The pack is the game

- `core.md` "vendor folders are read-only" applies to the other third-party code (DOTween, Odin, Spine runtime, SDKs).
  The **game pack folder is game code**: keep it out of the profile's `protected` list and name it in `CLAUDE.md`
  ("Third-party" → game pack: path, vendor, version).
- Every edit inside the pack is marked `// <PROJECT_CODE>:` with the reason (same tag as approved vendor edits) and logged,
  so a pack update can be re-applied by grepping the tag (P09 `TargetManager` read-only properties; BC54 `// BC54:`).
- Prefer additions next to the pack over rewrites inside it: new UI in our folders, a thin bridge to the pack's managers
  (P09 `LegacyGameplayBridge`), new read-only accessors instead of changing pack logic.
- Pack class names collide with the base (`UiManager`, `GameManager`…): write `Bacon.X` where both exist.

## Re-skin without breaking the pack

- **Re-skin in place**: keep the pack's GameObjects and swap sprites / anchors, because pack controllers hold serialized
  references to them (P09 Level01: rebuilding the board on a new prefab was dropped for this reason).
- Hide old UI with `CanvasGroup.alpha = 0`, not `SetActive(false)`: pack managers run coroutines on those objects and
  inspector `UnityEvent`s break (P09).
- The pack's rules are the spec: Part A = the pack's structure (scenes, prefabs, managers, data assets), Part B = its rules
  read from its code with `file:method` sources (P09 `TargetManager.CheckForLevelPass`). A behavior change is a decision (D#).
- Keep the pack's save keys / data assets until a plan decision moves them to the base save (P09 kept the PlayerPrefs
  keys behind `CurrencyManager`).
- Pack demo / example folders are removed before release (P09 R8: `Spine Examples`, `TutorialInfo`, `DOTweenPro
  Examples`); list them in the plan's "Trước khi phát hành".

## New art from Figma

- Import procedure, `rawImages` instead of rendered exports, node pitfalls: `/rip-original` `references/assets.md`
  ("Figma as the source of new art", "Figma font names → TTF → TMP SDF").
- Canvas reference resolution = the Figma frame size so coordinates map 1:1; anchor to corners when the match axis crops
  the frame (P09 2160×1080, match height).
- UI tint multiplies: a saturated sprite cannot be tinted to another hue; import it in grayscale and tint (P09 R14).
- Re-read the Figma metadata before each import batch and scan the whole page: designers edit the file live and put
  upgrade art outside frames (P09 R17–R19). Record art still missing in the plan ("Chờ user").
