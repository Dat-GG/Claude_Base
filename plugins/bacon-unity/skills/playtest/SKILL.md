---
name: playtest
description: Use whenever Claude itself enters Play mode in a Unity project through the Unity MCP - to verify a change, reproduce a runtime bug or capture the running game.
---

# Play-mode test (Unity MCP)

Follow the steps in order. Skip none, even for a "quick look". Read `.claude/bacon-profile.json` first:
`self_test` decides whether this skill runs at all (`none` → do not enter Play unless the user asked; `runtime-only` →
runtime bugs only, hand visual / UI checks to the user), `save_file` is the save to protect, `mcp` the server flavor.

## 1. Right editor, user not in it
- MCP instances: when more than one Unity editor is connected (reference / ripper editors), select ours
  (`set_active_instance`) and confirm with `Application.dataPath` that it is this project.
- `EditorApplication.isPlaying` true, or `manage_editor play` answers "Already in play mode" → **the user is playing**.
  Do not compile, do not stop it. Tell the user and wait, or stop only with their OK.
- Script changes pending → refresh, wait for compilation, console clean **before** Play (never compile during Play).

## 2. Fresh save backup (file level)
- Resolve `save_file` (expand `%USERPROFILE%`). Record its size + md5 + mtime **now**: the user may have played since
  the last turn, so a backup from an earlier turn is stale and must never be restored.
- Copy it to the scratchpad (`<scratchpad>/save_backup/<timestamp>_<name>`). The hook also copies it to
  `~/.claude/bacon-backups/<project>/` when Play starts; the scratchpad copy is the one you restore.
- Never snapshot the save from memory in the first frames of Play: the load is asynchronous, so early state is the
  default / fallback model, not the user's progress.

## 3. Enter Play, wait for data
- Enter Play through MCP. Wait until the project's "data loaded" flag is true (Bacon base:
  `DataManager.Instance.dataLoaded`, `_player != null`) before reading or changing progress.
- Put test state (stage, currency, unlocks) **in memory** when possible, and say what you set.

## 4. Drive frames when the editor is not focused
Unfocused editors do not tick. In one `execute_code`:
`EditorApplication.isPaused = true; Time.captureDeltaTime = 1f / 60f;` then loop `EditorApplication.Step()`
(one step = one 1/60 s frame). Keep each call under ≈ 600 steps or MCP times out (work continues, query state after).
Unscaled-time tweens barely advance while stepping.

## 5. Tap UI through a real raycast
Never invoke `onClick` directly (it hides "decor image covers the button" bugs). At the button's screen point:
`EventSystem.current.RaycastAll` (with the UI camera), take `hits[0]`,
`ExecuteEvents.GetEventHandler<IPointerClickHandler>`, then execute pointer enter / down / up / click on that handler.
Synthetic mouse input loses to the user's real mouse: if timing by hand matters, ask the user.

## 6. Capture and measure
- `ScreenCapture.CaptureScreenshot(path)` then Step twice; captures occasionally come out cyan, retry.
- Measure (positions, sizes, pixel colors, counts) instead of eyeballing; compare with the original / Figma when it exists.
- For visual bugs, render first, then look at logic.
- Change touches UI, anchors, safe area or the camera → capture the same screen at 3 aspect ratios: 9:16, 9:20 (tall
  phone), 3:4 (tablet), via the Game view size (reflection on `UnityEditor.GameViewSizes`; not proven yet, record the
  working call with `/add-lesson`). Check only objective faults (cut off, overlapping, off-anchor, outside the safe
  area); whether it looks right is the user's call: hand them the 3 captures.

## 7. Leave clean
- Stop Play. Restore the save from **this test's** backup (compare md5 with the value recorded in step 2 to be sure you
  restore the right file); keep the backup until the restore is verified.
- Delete temporary scripts / objects created for the test. Console has no new errors.
- Report: what was tested (scenario, numbers), what was **not** tested, and that the save was restored.
