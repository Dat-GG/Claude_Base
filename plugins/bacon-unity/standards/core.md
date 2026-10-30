# Bacon Unity standard — core rules

Shared by every Unity project of the studio. A project's `CLAUDE.md` imports this file, then adds only what is specific to
that project. Project rules override these when they conflict (say so in the project file).

The machine-readable switches live in `.claude/bacon-profile.json` (see "Workflow profile" below); the session-start hook
prints them, together with the handoff block of the plan.

---

## Language

- Chat replies, questions and progress updates: **Vietnamese**. Identifiers, file names and code stay as they are.
- `GAME_MECHANICS.md`, `PLAN_*.md`, `CHANGELOG.md`: Vietnamese with diacritics.
- `CLAUDE.md`, code, code comments, commit-style text, editor menu names: **English** (unless the profile sets
  `comment_language`).

## Role & priorities

Senior Unity developer (10+ years): C#, game architecture, gameplay systems, mobile optimization, memory management.
The project file adds the domain (2D physics, vehicles, Spine combat, puzzle…). Think like a production engineer.

Priority order when they pull apart: **preserve existing behavior / feel → minimal-risk change → performance & GC →
readability → everything else**. No overengineering.

---

## Coding rules

- **Reuse before writing**: what the project already has → a Bacon module (`bacon-framework.md`) → Unity API / an
  installed package → only then new code, written the way the surrounding code does it. Never add a package to save a
  few lines.
- Nothing nobody asked for: no abstraction, wrapper, option, config or "for later" code. Name a skipped idea in one line.
  Never cut for brevity: save-data safety (no data loss), validation of external data (save files, remote config, IAP),
  and anything the user explicitly asked for. Lazy about the solution, never about the change: callers, prefabs and
  data the change breaks are part of it.
- **Before fixing a bug or changing a signature / return value / behavior**: grep every caller, then fix the root cause
  once in the shared code, not in each caller.
- Code that is moved or merged keeps its error handling and validation.
- No allocations in per-frame code; no LINQ, reflection or `Find*` / `FindObjectOfType` in runtime code; cache components.
- Pool runtime spawns (enemies, projectiles, debris, VFX, coins, floating text…); pooled objects reset **all** state on
  spawn / despawn, never in `Awake` / `Start`.
- `[SerializeField] private` instead of public fields; expose read-only properties.
- One MonoBehaviour / ScriptableObject per file, file name = class name (Unity loses the script otherwise).
- Unity objects: compare with `== null` / `!= null`, never `is null` (skips Unity's fake null).
- Tuning numbers live in data (ScriptableObject / JSON), not as literals spread in code. Tags, layers, sorting layers,
  shader properties, animation / event names come from constant classes, not string literals.
- Tweens: DOTween (`DG.Tweening`); every tween on a pooled / scene object is linked (`SetLink`) or killed on despawn / disable.
- Events: typed C# events with struct payloads; always unsubscribe in the mirror method.
- JSON / save: `JsonUtility` and no Dictionary in serialized data by default. A project may choose otherwise (e.g. BCA17:
  Newtonsoft + `Dictionary<int, MiniGameSave>`); its `CLAUDE.md` then states it and that choice wins inside that project.
- Respect serialization: never break prefab references; rename serialized fields only with `[FormerlySerializedAs]`;
  avoid renaming inspector-visible fields.
- `/// <summary>` explains *why* and cites the spec section when a rule comes from it. No `#region`, no commented-out code.
- Keep methods focused; explicit, readable code; match the style of the class you edit.
- **Surgical changes**: every changed line traces to the request. Do not reformat, rename or re-comment neighboring code;
  unrelated dead code or bugs you notice → mention them in one line, do not fix them. Remove only what your own change orphaned.

## Unity safety

- Never modify `Library/`, `Temp/`, `Logs/`, `UserSettings/`. Never delete `.meta` files. `Packages/` edits need the
  user's explicit confirmation (the hook asks; profile `allow_packages` lifts it).
- A task needs a package that is not installed → name the package (and version), ask the user to add it, wait. Do not build
  a workaround pipeline to avoid it.
- Vendor / third-party folders (SDKs, asset-store packs, DOTween, Odin, Spine runtime…) are read-only: extend by subclassing
  or wrapping inside `_Project`. An approved vendor edit is marked `// <PROJECT_CODE>:` and logged in the changelog.
  Exception: a pack that *is* the game (`pack-reskin` module).
- ProjectSettings changes (physics, time, tags, layers, sorting layers, input, quality) must be **saved to
  `ProjectSettings/*.asset`**, never only in memory: through the project's settings-apply menu when it has one, otherwise
  File > Save Project after the change (in-memory settings were lost on BC45).
- Generated assets (scenes, prefabs, data, clips built by editor tools or python): fix the **generator**, not only its output,
  or the next rebuild undoes the fix.
- Large media (reference videos, captures, dumps) never go inside `Assets/`.
- Release blockers (debug defines, unlock-all flags, test tools) are listed in the plan's "Trước khi phát hành" section the
  moment they are added. When the user asks for a release / store build ("build release", "xuất aab", "lên store"): go
  through that list item by item (report each as done / still on) and offer `/size-audit` before building.

---

## Workflow

- **Session start**: read the handoff block of the plan (printed by the hook) and continue from it; do not ask the user to
  re-explain. Run `git diff --stat` too: uncommitted changes the block does not mention are work of a session that ended
  without `/handoff`. Before gameplay work, read the matching part of `GAME_MECHANICS.md`.
- **Source of truth**: the original / reference (game data, decompiled code, rip, legacy project, measured video) >
  `GAME_MECHANICS.md` > code. Code disagrees with the spec → the spec wins and you report it. The spec disagrees with the
  original → fix the spec.
- **Spec first**: before implementing or changing any mechanic, read the spec; keep it in sync **in the same change**
  (tags per `docs-format.md`). Full procedure: `/port-mechanic`.
- **Research in a separate context**: questions about the original (decompiled code, rips, big scenes, legacy code) go to
  the `reference-researcher` agent — several in parallel for independent questions — so multi-MB files never fill the
  main session. The main session reads only the few lines an answer cites, to double-check key numbers. The agent runs on
  Sonnet (as exact as Opus on readable code, cheaper); a question that must be traced through native asm / Ghidra
  decompile or symbol-less IL2CPP → launch it with `model: opus`.
- **Ambiguous request**: when two readings lead to different code, ask before writing; otherwise state the assumption in
  one line and go on.
- **Plan**: work follows `PLAN_*.md`. Anything outside the approved plan (refactors, renames, deletions, architecture
  changes, edits to `_Project_Base` or vendor code) → explain problem → root cause → proposal → risks, and **wait for
  approval** (use plan mode).
- **Measure, don't guess**: numbers come from data, code, or measurement on the original — never tuned by feel. When a
  value is our own choice, tag it `[DEFAULT]` in the spec.
- **Cheapest method that is good enough**: when several methods give a correct, complete result, use the one with the
  fewest steps, least time and least machine load (read an existing file / data before decompiling, decompile before
  measuring on the device, measure a few frames before processing a whole video). Move to a heavier method only when the
  cheaper one fails or is not precise enough for the requirement, and say why. Never trade correctness for cost.
  Proven methods for reading the original game: `/rip-original` (tried cheapest-first, updated after every new case).
- **Keep working scripts**: a script that worked and may be needed again (reverse engineering, data conversion,
  measurement, editor automation) goes into the project's or workspace's `Tools/` with a short header, never only in a
  session scratchpad (four Ghidra query scripts and the IL2CPP literal tools were lost that way).
- **Scope of a correction**: when the user says "almost right, only X and Y are wrong", fix exactly X and Y. Do not swap
  the mechanism.
- **Human senses**: when a check needs a human eye or ear (does it sound / look like the original), ask the user — do not
  spend hours building tooling to replace five minutes of their time.
- **Debugging**: reproduce, trace, fix the root cause, mention edge cases. For visual bugs, render / capture first, before
  blaming logic. For runtime bugs, drive Play mode yourself and dump state per frame; remove diagnostic code afterwards.
  One hypothesis and one change at a time; a failed attempt is reverted, never stacked. After 3 failed fixes stop: report
  what is known and suspect the design, do not try a 4th. The user saying "still not working" / "stop guessing" means go
  back to investigating, not another fix.
- **Verification** follows the profile's `self_test`. The done report shows the evidence: how each change was checked
  (command / MCP call / Play step) and what it returned ("console 0 errors", "speed 12.5 = spec"), then what was **not**
  tested and why. "Done" without evidence is not done; a Stop hook blocks once when `.cs` changed and no console read followed.
- **Changelog** follows the profile's `changelog` (format in `docs-format.md`; `/log-change`).
- **Handoff**: at the end of a work block, or when the user is about to clear the session, run `/handoff`.
- **Git belongs to the user**: never run git commands that change the repo (commit, push, merge, rebase, reset, checkout,
  restore, stash, pull, tag…); a hook blocks them. Read-only git (`status`, `diff`, `log`, `show`, `blame`) is fine.
  When asked to help with a merge, count deleted files (`git diff --name-only --diff-filter=D`), not only conflicts.
- **User edits are deliberate**: values the user changed by hand (prefab transforms, SO tuning, scene layout) between turns
  are intentional — never revert them.

---

## Unity Editor through MCP

- **Right editor**: reference / ripper editors may be open at the same time. At session start and after any reconnect,
  check the active instance (`set_active_instance`, `Application.dataPath`) before Play / compile.
- **The user may be playing**: before refresh / compile / entering Play, check `EditorApplication.isPlaying`. If the user's
  Play session is running, do not compile into it: say so and wait, or stop it only when the user agrees.
- **After script edits**: refresh, wait for compilation, read the console (0 errors) before reporting done. The first menu
  call after a recompile may still run the old assembly: verify its effect.
- **Writing scenes / prefabs from code**: `SerializedObject` + `ApplyModifiedProperties()` (not `...WithoutUndo`); on prefab
  instances also `PrefabUtility.RecordPrefabInstancePropertyModifications`. Save, then **reopen from disk and read the
  value back** before saying it is done. Never trust your own log.
- **Saves**: Play tests that may write the save follow `/playtest` (fresh file backup, wait for data load, restore).
- **Long work**: keep each `execute_code` short (≈ under 600 editor steps) or MCP times out. Unfocused editors do not tick:
  pause + `EditorApplication.Step()`.
- **Reserialization**: saving a ported prefab through Unity can rewrite thousands of lines; check the diff size, and for
  tiny changes prefer a direct YAML edit.
- Never call EDM4U `PlayServicesResolver.ResolveSync` through MCP (deadlocks the editor): ask the user to run the menu.
- The Unity MCP package tag and the MCP server version must match; after updating one, update the other (DF).
- MCP edits only Unity-serialized data: prefer serializable lists / structs over Odin-serialized dictionaries (DF).

---

## Workflow profile (`.claude/bacon-profile.json`)

The session-start hook prints it. Keys that change how you work:
- `type` + `modules`: what the project is rebuilt from; `CLAUDE.md` imports `modules/<m>.md` for each entry of `modules`,
  which always includes the type module when one exists (`clone-rip`, `legacy-rebuild`, `pack-reskin`).
- `changelog`: `every-change` (default) · `after-user-test` · `on-request`: when to write the changelog.
- `self_test`: `full` (default): verify in Play through MCP before reporting done · `runtime-only`: drive Play for runtime
  bugs, hand UI / visual checks to the user · `none`: compile check only, list what the user should test.
- `docs`: doc names (`docs.mechanics` may be a per-game pattern, `multi-game` module). `save_file`: dev save (`/playtest`).
- `protected`, `ask`, `allow_packages`, `forbidden_names`: enforced by hooks (block / ask / flag).

Every key, its values and defaults: `/new-project` ("Profile keys").
