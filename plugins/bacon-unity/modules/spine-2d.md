# Module: spine-2d — Spine characters and UI

For projects whose characters / decor are Spine skeletons (DF, P09).

## Versions

- **Pin the Unity + spine-unity versions** and write them in `CLAUDE.md`. Spine data must be exported for the runtime in
  the project (4.x data does not load in a 3.8 runtime); a Unity upgrade that forces a Spine upgrade is a plan decision
  (DF Q1: stays on 2022.3 + spine-unity 3.8, the player skeleton has no `.spine` source to re-export; P09 R1: artists
  export in 3.8).
- Never copy `*_Atlas.asset` / `SkeletonData.asset` produced by another runtime version (P09: a 4.x atlas asset).
- Do not ship `Spine Examples` (P09: 19 MB).

## Runtime rules

- Gameplay drives Spine **only through one animator wrapper** (DF `SpineAnimator`): animations / events looked up once
  and cached, callbacks to the current state only (detached on state exit), facing by `Skeleton.ScaleX`.
- Speed only through `TrackEntry.TimeScale`. **`SkeletonAnimation.timeScale` is forced to 1** on init (DF: a prefab saved
  with 0 froze E7, one saved with 2 ran Pet_3 ×4).
- Play on the track the skeleton expects: a skeleton with a starting animation on track 0 plus the wrapper on another track
  stacks two animations (DF end-gate character → track 0).
- Never `.material` on Spine renderers at runtime (material instances): flashes / tints through `MaterialPropertyBlock`
  (DF hit flash `_HitEffectBlend`); a material whose shader lacks the property shows nothing.
- Animation / event / skin / slot names come from definitions or constant classes, never scattered literals; a data
  validator checks every name exists in its skeleton (DF `Bacon/Data/Validate Catalogs`, P09 holder check).
- UI-space Spine = `SkeletonGraphic` with `SkeletonGraphicDefault` material (clips in a ScrollRect) (P09).

## Art replacement

- New art with the same `.json` / `.atlas.txt` (ignore CRLF) and same PNG size → overwrite **only the PNGs**, keep `.meta`.
  Different → it is a re-export: replace the whole set (P09).
- Materials are premultiplied alpha (`_StraightAlphaInput: 0`) unless set otherwise: hand-painted atlases break PMA (bright
  fringes, white boxes from colored alpha-0 pixels). Fix: `max(RGB) > A → RGB × A / 255`, `A = 0 → RGB = 0`; texture
  `Alpha Is Transparency` off; better, ask for a 3.8 export with premultiply on (P09).
- Atlases POT ≤ 2048 so they compress on mobile (P09 R2).
- Spine from other engines (Cocos): `/rip-original` `references/assets.md` (Spine sections).
