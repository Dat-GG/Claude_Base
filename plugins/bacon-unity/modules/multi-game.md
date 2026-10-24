# Module: multi-game — a hub of mini-games, one scene each

For titles that are a collection of mini-games behind one Home (BCA30 NUMPUZ: 17 games; BCA17 Mini Challenges: 34).

## Docs: one spec per game

- Each game has its own spec, the source of truth for its rules: `GamePlan/<Game>/<Game>.md` (BCA30), plus an index
  `GamePlan/README.md` (id → bundle / tag → display name) and shared parts (`GamePlan/AUDIO.md`). Data-extraction scripts
  for the original go in `GamePlan/_tools/`.
- Profile: `docs.mechanics` = the per-game pattern (`"GamePlan/<Game>/<Game>.md"`); `docs.plan` / `docs.changelog` stay one
  file for the whole title (the handoff block and the changelog hook read them). A per-game `GamePlan/<Game>/CHANGELOG.md`
  is optional, for "why" notes and dead ends of that game; read it before touching that game again (BCA30).
- Spec rules of `docs-format.md` apply per file (tags, sources, "update the spec before the code").

## Two UI systems: name them

- `Bacon.UIManager` / `Bacon.PopupBase` (global popups in `1_MainScene`) and the per-scene `MiniGame.UIManager` /
  `MiniGame.PopupBase` have almost the same API; a bare `UIManager` binds to the wrong one. In mini-game scenes always
  write `Bacon.X` / `MiniGame.X` (BCA30). Same for per-game `GameManager`s (BCA17 `MiniGameXO.GameManager` vs
  `Bacon.GameManager`).
- Each game keeps the namespace it already has; do not normalize namespaces across games (BCA30).

## Registry, scenes, launch

- One registry asset `MiniGameData` (`id`, `name`, `thumb`, `sceneName`, `isRelease`, `isHotGame`); design-time config per
  game belongs there, not in the save (BCA30, BCA17).
- Wiring a game = scene → **add to the build list** (`SceneHelper.LoadScene` cannot load it otherwise) → `sceneName` →
  `isRelease: 1` (BCA30).
- Launch: `MiniGameSession.CurrentGameId` (transient hand-off) → `RouteController.StartLevel(sceneName)` → additive load.
  The loaded scene shows its own popup and **hides `Bacon.UILoadingMiniGame` itself**; back to Home = unload + show
  `UIHome` (BCA30).
- A mini-game scene played alone in the Editor (no `DataManager`) must still run on a temporary save slice (BCA30).

## Save

- Per-game progress only through `MiniGameSaveService.GetOrCreate(id)` (lazy create, never pre-populate all games) +
  `customJson` for game-specific state, wrapped by one static `<Game>Progress` class per game (BCA30, BCA17).
- No new PlayerPrefs keys (outside the save file, not cleared by `ResetData`); long per-level arrays stored as a string
  (BCA30).

## Editor tools

Per-game menus under `Tools ▸ <Game> ▸ …` through the constants in `Bacon.MiniGameMenu`
(`[MenuItem(Bacon.MiniGameMenu.WaterSort + "…")]`); no new menu roots (BCA30).
