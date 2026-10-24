# Module: world-3d — 3D world scene on the Bacon base

For 3D games with one big world scene driven by vehicle / character packs (BC54 city).

## Scenes and cameras

- Build list `0_SplashScene` → `1_MainScene` (base) → `2_Gameplay` (the world), loaded **additively** by the base
  `SceneHelper` behind `UILoading` (BC54, BC46 pattern).
- **No cross-scene serialized references**: all UI stays as `PopupBase` panels under `1_MainScene/UIManager/SafeArea`;
  world controllers fetch panels at runtime (`UIManager.GetUI<T>()` through one accessor, BC54 `GameUi`).
- The world camera is a URP **Base** camera with the base `UICamera` **stacked** as overlay; base `MainCamera` off; one
  EventSystem (the base one); one AudioListener: turn the UICamera listener off before enabling the world one (BC54
  "2 audio listeners").
- Playing `2_Gameplay` alone in the Editor must reboot from build scene 0 (BC54 `GameplayEditorBoot`), never run half
  initialized.

## Packs and input

- Vehicle / character controller packs: same pack and **same version as the original** when it used one (BC54 RCCP
  1.37.0, Easy Minimap 2.4.2); drive them through our adapter (`BikeAdapter`, `VanAdapter`), never their demo input
  scripts (legacy `Input`). Tuning that deliberately differs from the original lives in one data asset (BC54
  `BikeHandling.asset`, PLAN Q17).
- A pack that reads `UnityEngine.Input` forces **Active Input Handling = Both**; our code still uses the Input System only.
  The switch needs an editor restart (BC54).
- Pack editor buttons can write into pack settings assets (BC54: RCCP "Enable mobile controller" saves
  `mobileControllerEnabled`): set such flags at runtime, keep the asset value, restore it on disable.

## Rip → URP, lighting

Materials, lightmaps vs Mixed lights, script remapping: `/rip-original` `references/engine-il2cpp.md` ("Built-in →
URP", "Using the rip as a Unity project"). Converters are `Bacon/Import/*` menus: fix the converter, rerun, compare a
capture with the device (BC54 Simple Lit specular enum written backwards). Keep the original's color space (BC54 Gamma).

## Big-scene performance (measure on device before optimizing further)

- Pool runtime spawns the original instantiated (BC54 traffic cars: original Instantiate / Destroy hitched).
- Bake occlusion culling for the world scene and rebake when the world changes; HDR off when there is no post-process;
  path / navigation queries at 0.1 s, not every frame (BC54 C2–C4).
- Ripped static batching is baked (`Combined Mesh (root: scene)`, unreadable): keep `m_StaticBatchInfo`, never let Unity
  batch it twice; per-block split is a plan decision (BC54 Q6).
- New city / environment packs: check texture sizes, per-object MeshColliders, LOD, shaders before adopting (BC54
  `Classical_city`: 1 GB of uncompressed TIF, 1 728 MeshColliders, no LOD, Built-in shaders).
- FPS / resolution follow the original (BC54: 60 fps if RAM > 2 GB else 30, render scale 0.8).
