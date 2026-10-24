# Driving and measuring the original on LDPlayer

**Machine**: `<ldplayer>/` has `adb.exe`, `ldconsole.exe` (v9.5.19), `dnconsole.exe`, `ldrecord.exe`.
Instance 0: `<adb-device>` (`emulator-5554` on the reference machine), Android 9, x86_64 with ARM through houdini, root via `su`, 1920×1080 landscape, density 280.
A real phone is sometimes plugged in: **always pass `-s emulator-5554`**. Some tools use `127.0.0.1:5555` (same emulator).

Device tools already written (copy into a new workspace, edit package / paths):
- `<projects>/Urban_Food_Ripped/Tools/ld_tool.py`: `shot | record | tap | hold | gesture | run | launch` (gesture =
  multi-touch). The E2D copy has no `gesture`.
- Save tools: `save-files.md`.

---

## Shell basics

### Connect
- Status: ✅ all projects · Cost: 1
- `A=/c/LDPlayer/LDPlayer9/adb.exe; export MSYS_NO_PATHCONV=1; $A devices;
  $A -s emulator-5554 shell "dumpsys window | grep -m1 mCurrentFocus"`
- Pitfalls: `adb connect 127.0.0.1:5555` adds a second entry for the same emulator → commands without `-s` fail as
  ambiguous.

### Quoting
- Status: ✅ · Cost: 1
- Git Bash: `export MSYS_NO_PATHCONV=1` (else `/sdcard/…` becomes `C:/Program Files/Git/sdcard/…`), `PYTHONIOENCODING=utf-8`.
  Root commands as one string: `shell "su -c '…'"`. Anything longer: write a `.sh` with LF endings, `adb push` it to
  `/data/local/tmp`, run `su -c 'sh <file>'`.
- Pitfalls: PowerShell expands `$(pidof …)` on the host → use Git Bash or a pushed script.

### Byte-exact pull / push
- Status: ✅ E2D 2026-10-13 · Cost: 1
- Pull: `su -c 'cp SRC /sdcard/t && chmod 644 /sdcard/t'` → `adb pull /sdcard/t` → remove. Push: `adb push` to `/sdcard`, then
  `su -c 'cp … && chown U:U … && chmod 600 … && rm …'` (owner from `stat -c %U`). Verify with `cmp` after pulling back.
- ❌ `adb shell "su -c cat f" > local`: the pty turns 0x0A into 0x0D 0x0A (a corrupted save made the game allocate 5.6 GB
  and die).

### Device offline after network changes
- Status: ✅ fix / ❌ `adb reconnect offline`, `kill-server`, `ldconsole adb --command …` · Cost: 2
- Cause: `svc wifi disable` / `svc data disable` — LDPlayer's adb uses the same virtual NIC. **Never disable wifi.**
- Fix: re-enable wifi inside Android by hand, or `<ldplayer>/ldconsole.exe reboot --index 0`, wait ≈ 45 s, poll
  `adb devices`. Wrap waits in `timeout 15` (commands hang while offline).

### Block the game's network (ads, remote config) without losing adb
- Status: ✅ UFD / BC54 2026-10-15, 10-19 · Cost: 1
- `U=$($A -s emulator-5554 shell "dumpsys package PKG | grep -m1 userId=" | tr -dc 0-9)`;
  `$A -s emulator-5554 shell "su -c 'iptables -I OUTPUT -m owner --uid-owner $U -j REJECT; ip6tables -I OUTPUT -m owner --uid-owner $U -j REJECT'"`;
  check `iptables -S OUTPUT | grep $U`.
- Pitfalls: the rule persists across sessions (note it, remove it later); cached ads still show. Alternative:
  `settings put global http_proxy 127.0.0.1:1` + `pm disable <ad activity>`.

## App control

### Launch / stop / deep link / APK path
- Status: ✅ · Cost: 1
- `monkey -p PKG -c android.intent.category.LAUNCHER 1` (or `am start -n PKG/.Activity`), `am force-stop PKG`, focus
  `dumpsys window | grep mCurrentFocus`, back `input keyevent 4`, deep link `am start -a android.intent.action.VIEW -d '<uri>' PKG`
  (app already on the right screen: a cold start drops the parameter), APK `pm path PKG`.
- Pitfalls: E2D shows a Google Play Games dialog on every launch (Cancel at 480, 488).

### Logcat / crashes / memory
- Status: ✅ E2D 2026-10-13 · Cost: 1
- `logcat -c`, launch, `logcat -d -t 3000 | grep -iE "FATAL|died|ActivityManager.*(Killing|died)|lowmemorykiller"`; Unity:
  `logcat -s Unity`. Low-memory kills only show in `su -c dmesg | grep "Killing '<last 15 chars of pkg>'"`.
  RSS: loop `su -c "grep VmRSS /proc/$(pidof PKG)/status"`; device `cat /proc/meminfo`.
- Process memory dumps (`/proc/<pid>/mem`): `engine-js.md`. ❌ Frida / gdb (ARM under houdini).

### Emulator management (ldconsole)
- ✅ `list2`, `reboot --index 0`. 🧪 (help only): `quit`, `launch`, `runapp / killapp --index 0 --packagename P`,
  `modify --index 0 --resolution 1920,1080,280`, `globalsetting --fps 60`, `pull / push --remote R --local L`,
  `backupapp / restoreapp`. `ldconsole adb --command` is useless once adb is offline.

## Capture

### Screenshot
- Status: ✅ · Cost: 1
- `py -I <workspace>\Tools\ld_tool.py shot OUT.png` (= `exec-out screencap -p`, binary-safe). 1920×1080 = 1 px per screen px.
- Pitfalls: `exec-out`, not `shell` (PNG bytes get mangled). ≈ 1 s per capture: not for timing.

### Screen recording
- Status: ✅ E2D, UFD · Cost: 2
- `ld_tool.py record OUT.mp4 --seconds N` (max 180) or `run --hold X Y --ms N --record a.mp4 --shot b.png`; record while
  scripting input: `( ld record v.mp4 --seconds 16 ) & sleep 1; ld gesture "…"; wait`.
- Pitfalls: **variable frame rate** (59.3 fps avg; another clip 983 frames / 30 s) → use container timestamps (`/ref-video`).
  The tool waits 1 s after the end so the encoder closes the file. ≈ 1.5 MB/s at 1080p. Check tiny files (a 113 KB
  recording was broken). Store outside `Assets/` (`<workspace>\Tools\_save\…`).
- Long or hand-played sequences: ask the user to record with LDPlayer's recorder (≈ 30 fps) into the workspace
  `_save\ld\user\`; note camera-mode changes with time ranges.

### Recording conditions for reliable measurement
- 1920×1080 landscape, 60 fps, **no ad banner** (iptables; a 158 px banner once shifted the whole layout and looked like a
  scaling bug), same save state (push a backup), scripted input running in parallel with the recording, 1–2 s lead-in,
  run twice to check repeatability (E2D baseline 460 vs 459 ft, ±0.2 %).

## Input

### Single pointer: `input tap / swipe`
- Status: ✅ E2D 2026-10-08 · Cost: 1
- `ld_tool.py tap X Y`; hold = `input swipe X Y X Y N`; scroll `input swipe 960 700 960 300 600`.
- Pitfalls: one pointer only (no throttle + tilt together); each adb call adds ≈ 100–300 ms.

### Multi-touch: sendevent script on the device
- Status: ✅ UFD 2026-10-15, BC54 10-19 · Cost: 1
- `py -I Urban_Food_Ripped\Tools\ld_tool.py gesture "down 0 1700 780; down 1 210 780; wait 0.35; up 1; wait 4; up 0" [--shots DIR]`
  (ops `down S X Y | move S X Y | up S | wait SEC | shot NAME`). Generates protocol-B events for `/dev/input/event2` and runs
  them as root on the device, so timing stays on the device.
- Pitfalls: `shot` inside a gesture delays what follows by ≈ 1 s. Device node and axis ranges are hard-coded: check
  `getevent -p /dev/input/event2` on a new instance (X 0..1919, Y 0..1079, slots 0..15).

### Keyboard into our own dev APK
- 🧪 BC54: a dev define reads PC keys (LDPlayer forwards them as a hardware keyboard). Remove the define before release.

## Layout probing

### Force resolutions to find the fit mode
- Status: ✅ HexRescue 2026-08-21 · Cost: 2
- `adb shell wm size 1080x2340` (then `2048x1536`), screenshot, compare an element's width % with the design frame
  (66.78 % vs 66.67 % → fit width; constant 0.750 ratio → show all). Reset with `wm size reset`.
