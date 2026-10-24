---
name: ref-video
description: Measure reference videos and screenshots of the original game frame by frame - probe (real timestamps, VFR), contact sheets to find moments, full-resolution frames, change / event detection, color masks, motion and position tracking, colors, side-by-side with Unity captures, curve fits - with the bundled framekit.py script. Use whenever timing, speed, size, position, color or animation of the original must be read from a recording or screenshot.
---

# Reference video / screenshot measurement

Script: `"${CLAUDE_SKILL_DIR}/framekit.py"`, run as `py -I "${CLAUDE_SKILL_DIR}/framekit.py" <command> … --out <dir>`.
Shell variables do not survive between Bash calls: write the full quoted path in every command (the short forms below,
`probe V …`, `sheet V …`, mean exactly that). Subagents get the same absolute path in their prompt.
Machine paths: `<projects>`, `<ffmpeg>` etc. are keys of `~/.claude/bacon-machine.json` (printed at session start); read the
file if a key is needed and not printed. Missing key / file → run /setup-machine or ask the user.
Needs numpy + opencv + Pillow (installed in the machine Python; `py`, not bare `python`). Output dir: the scratchpad or the
workspace `Tools/_save/<topic>/`, never inside Unity `Assets/`.

**First check whether the value exists in data or code** (`/rip-original`): a serialized / code value beats a measured one.
Measuring is the right tool for things data cannot hold (layout, feel, timing of animations, VFX look).

## Workflow (cheapest first)

1. **probe** — `py -I "${CLAUDE_SKILL_DIR}/framekit.py" probe V --out D`
   Real frame count (header counts can be off by one), first / last timestamp, real fps, dt min / median / max, `vfr`.
   LDPlayer `screenrecord` files are **VFR** (dt 0.012–0.068 s seen): every time in framekit is the decoded frame's
   container timestamp, never `frame / fps`.
2. **coarse sheet** — `sheet V --t0 0 --t1 <end> --step <2–5 s> --cols 5 --width 1500`
   Then `Read` the PNG to find the moments. Long videos: several coarse sheets, then fine sheets (`--step 0.1–0.5`,
   `--windows "26.6-27.9,56.2-58.1"`, `--roi` to zoom). ≤ 60 tiles per sheet, keep `--width` ≤ 1600 so it stays readable.
   Sheets are scaled: use them to **find**, never to **measure**.
3. **pin the moment** — choose the cheapest detector:
   - `mask V --t0 --t1 --roi x,y,w,h --lo r,g,b --hi r,g,b [--present N]`: a known-colored element appears / disappears /
     scales (bbox w, h per frame). Proven: BC36 menu PLAY button vanishes at frame 380 (12.667 s), press-scale visible in
     the bbox just before.
   - `diff V --t0 --t1 --roi …`: moving vs still segments and change onsets (popup freezes the world, effect starts).
     Use a quiet ROI (exclude HUD, ad banner, center UI). The summary prints the noise floor (compression ≈ 0.1–0.5).
4. **measure on full-resolution frames**:
   - `frames V --times a,b,c` or `--burst t0,t1` (every frame) → PNGs to Read / crop.
   - `track V --method phase --roi …` → per-frame dx, dy and px/s from real dt (pan, scroll, camera motion, inertia).
     **`response` < ≈ 0.3 = unreliable** (zoom, cut, overlapping motion): drop those rows.
   - `track V --method template --template T.png [--scales 0.8:1.2:0.01]` → position, scale, ncc per frame (an object, a
     HUD element; cut the template with `frames --roi`).
   - `color SRC --roi … --times a,b,c [--linear]` → median RGB / hex, spread between frames. Compression shifts saturated
     colors (#C1FF32 read as #BEF737): prefer the asset / prefab value when one exists. Linear-space projects: use `--linear`.
   - Sub-pixel sizes / edges: profile across the edge on a `frames` PNG; integer pixels create fake plateaus.
5. **compare with our build** — capture Unity (`/playtest` step 6, or render `Camera.main` in edit mode), then
   `compare <video@t | png> <unity.png> [--roi …] [--align]` → side-by-side, 50 % overlay, abs diff, mean colors, alignment
   offset. Same resolution and same state on both sides; composite all cameras (main + UI).
6. **fit** — `fit track.csv --x t --y vx_px_s --model linear|exp` (decay constants, rates). Video fits lose to config values.
7. **write it down** — `GAME_MECHANICS.md` with the source: `<video> t=12.667 s (f380)`, ROI, method; tag `[CONFIRMED]`
   (measured on the original). Keep the CSV / JSON next to the video in the workspace when it is a baseline.

## Making recordings measurable
LDPlayer recording rules (no ad banner, same save state, scripted input, lead-in, two runs): `/rip-original`
→ `references/device-ldplayer.md` › Recording conditions. Ask the user for hand-played clips; note camera-mode changes with
time ranges. Zoomed or partial videos cannot prove whole-screen behavior.

## Pitfalls already paid for
- One downscaled 222 px still led to 5 wrong conclusions (BCA27): measure on full frames.
- Particles share the label color; clouds / gradients break color and diff measurements: pick a clean patch.
- A seek past the last frame returns the last frame again ("nothing changes"): check `probe` last_t.
- A 158 px ad banner shifted the whole layout (BC36): check for banners before blaming scaling.
- No ffprobe on this machine; ffmpeg only through `imageio_ffmpeg` (framekit finds it).

## Extending
A measurement framekit cannot do yet → write it as a new subcommand in `framekit.py` (same output conventions), test it on a
video with a known answer, and record it with `/add-lesson`. Known test videos:
- `<projects>/BC36_Traffic_Rider/BC36_Traffic_Rider/Source/BC36_Rebuild/Assets/_Project/Scrs/Scene_game.mp4`
  (menu vanishes f380)
- `<projects>/Urban_Food_Ripped/Tools/_save/ld/traffic_start_30s.mp4` (VFR)
- `<projects>/BCA27_Paint/BCA27_Paint_by_Number/BCA27_Paint_by_Number/Assets/ScrShoot/video4.mp4` (pan inertia)
- `<projects>/Urban_Food_Ripped/Tools/_save/ld/user/video16.mp4` (pedestrian vanishes 163.4 → 168.3 s)
