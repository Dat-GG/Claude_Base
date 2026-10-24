# Bacon base framework (`_Project_Base`)

Applies to projects built on the studio's "Bacon" base. The project's `CLAUDE.md` only lists what differs (extra scenes,
its flow controller, its save sub-model, which `USE_*` are set).

## Two-tier code layout

- **`Assets/_Project_Base/`** — reusable framework: RouteController, UIManager / PopupBase, DataManager / PlayerModel,
  FileDataHelper save, AudioController, Ads / IAP / Firebase / UMP, LanguageManager (I2), Helpers, SafeArea.
  Vendored infrastructure: **no game logic here**. Edit only for framework bugs, **with approval** (hook asks).
- **`Assets/_Project/`** — game layer: `Scripts/{Core, Data, Gameplay, UI, Utils, Editor}`, assets next to it
  (`Art2D/` or `_3D_Art/`, `Prefabs/`, `Animations/`, `Audio/`, `Fonts/`, `VFX/`, `Data/`, `Scenes/Tests/`).
  Editor scripts in `*/Editor/` folders, menus under `Bacon/*`.
- No asmdefs in `_Project` / `_Project_Base`: everything compiles into `Assembly-CSharp`.
- Layering: `_Project_Base` never references `_Project`; gameplay never references UI (UI listens to gameplay events);
  gameplay never calls save / ads / analytics directly (raise an event, a service in `Core` handles it).
- Extend through the `*Base` classes (`DataManagerBase` → `DataManager`, `PlayerModelBase` → `PlayerModel`).
- Do not bypass the base: no standalone splash, no replacement UI system, no second save path. Follow the newest
  project that uses the base as the reference pattern, and ask before deviating.

## Boot & app flow

Build scenes **`0_SplashScene` → `1_MainScene`** (more only if the project says so).
1. `UILoadingSplash` loads `1_MainScene`.
2. `RouteController` (`Singleton`, DontDestroyOnLoad) runs init: data load → remote config → consent (UMP) → ads → analytics.
3. `UILoading` waits for `RouteController.Instance.InitDone`, then `RouteController.InitGame()` hands over to the game's
   flow controller (`StoryFlow`, `FightFlow`…).

## UI / popup system

Screens are `PopupBase` subclasses under `UIManager`'s SafeArea, collected in `Awake`.
`UIManager.Instance.ShowPopup<T>()` / `HidePopup<T>()`; override `ShowStart` / `ShowCompleted` / `HideStart`;
`IsAnchor = true` for persistent popups. Never instantiate popups directly. Panels are prefabs; when a builder made them,
the project says whether to edit the prefab or the builder.

## Data & save

`DataManager.Instance._player` (`PlayerModel`) is the live state; call `DataManager.Instance.Save()` after mutating.
`FileDataHelper` writes gzip JsonUtility `<applicationIdentifier>.gd` under `Application.persistentDataPath` (async
queue, temp file then swap; changing the bundle id loses the save). The load is **asynchronous** (10 s timeout → default
data): read `_player` only once `DataManager.Instance.dataLoaded` is true, and never save before that.
Base versions differ: BC46 / BCA30 delete an unreadable save; DF keeps the previous save as `.bak` (`File.Replace`), an
unreadable one as `.corrupt` (load falls back to `.bak`), and has `saveVersion` + `PlayerModel.Migrate()`: bump
`CurrentSaveVersion` and add a step whenever the save layout changes. Do not add PlayerPrefs keys or a second persistence path.

## Feature flags

SDKs are gated by `USE_*` defines (`USE_MAX`, `USE_ADMOB`, `USE_FIREBASE`, `USE_INAPP`…). Keep SDK code inside the
matching `#if USE_*`. Rewarded-ad rewards go through one gateway (dev builds grant instantly until the ads phase).
Code under `#if UNITY_ANDROID && !UNITY_EDITOR` is invisible to Editor compiles: after touching it, compile player scripts
for the target (or build) before calling it done.

## Singletons

`StaticInstance<T>` / `Singleton<T>` in `_Project_Base/Scripts/Module/Utils/Helpers.cs`; some managers declare `static Instance`
by hand (`UIManager`, `DataManager`). Match the class you are editing.

## Third-party plugins usually present

DOTween, Odin Inspector (`[Button]`, `[FoldoutGroup]`…: attributes are load-bearing), I2 Localization (`LanguageManager` / `LocaleText`), TextMesh Pro, Hapthicks (haptics).
