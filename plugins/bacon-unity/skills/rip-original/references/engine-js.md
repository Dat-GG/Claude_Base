# Cocos Creator / JS originals (and other non-Unity, non-native-symbol apps)

Proven on NUMPUZ (`com.dopuz.klotski.riddle`, Cocos Creator 3.x, 17 mini-games) and BCA27 Paint by Number
(`com.oakever.paintbynumber`, native Android app). Entries cheapest first.

**Stop rule**: after ≈ 30 min without progress on extraction, stop and ask the user (an extracted folder, a playtest,
their ears). The user once had to ask "đang check gì mà lâu vậy?".

---

## Recognise it

### APK contents
- Status: ✅ NUMPUZ 2026-08-05 · Cost: 1
- Cocos: `libcocos2dcpp.so`, `assets/gameres/<16 random dirs>/<hash>.dat`, symbol `jsb_set_xxtea_key`, packer
  `libpglarmor.so`. Encrypted `.dat` (entropy ≈ 7.95) → the JS is not readable from the APK; go to RAM carving.
- Native Android app (dex only): `dumpsys package <pkg>` lists deep links; grep the `.dex` for `<scheme>://`.

## Get the data

### 1. Ask the user for an already-extracted folder
- Status: ✅ NUMPUZ GameSpxdd 2026-08-18 · Cost: 1
- The user had `GameSpxdd/` (`spxddLevelConfig.json` + 250 pool JSONs). Always ask before carving.

### 2. Raw files that are not encrypted
- Status: ✅ NUMPUZ (159 mp3) · Cost: 1
- Only `.dat` was encrypted: audio sat bare at `base.apk!assets/gameres/<bundle>/<uuid>.mp3` (see `assets.md` › Audio).

### 3. Carve JS + data from process RAM (rooted LDPlayer)
- Status: ✅ GameGmmj 2026-08-05 (220 K chars), GameSpx 08-17, GameTbx 08-20, GameLbxzl 08-21 · Cost: 3
- When: Cocos / V8 game with encrypted assets.
- How:
  1. Open **that exact mini-game / screen** in the original (the bundle is in RAM only while it is open).
  2. `adb -s emulator-5554 shell pidof <pkg>` (PID changes every restart).
  3. `su -c cat /proc/<pid>/maps` → keep `rw-p` regions.
  4. Dump each region: `dd if=/proc/<pid>/mem bs=4096 skip=<start/4096> count=<n> >> /sdcard/dump.bin` then pull, or
     faster: pipe each region through `adb exec-out` into a host-side matcher and keep only the hits.
  5. Extract long runs containing a bundle marker (`System.register`, `_virtual/<Game>.ts`, the game's class prefix), grow
     them both ways, write `.js`.
- Reusable tools: `<projects>/BCA30_NUMPUZ/_tomb_run_dumps/` (`dumpmem.sh`, `dump2.sh`, `extracted\extract_bundle.ps1`
  (C# via `Add-Type`; pure PowerShell is too slow), `extracted\scan_levels.ps1`, `extracted\decode_levels.py`,
  `extracted\apply_order.py`, `extracted\chain_to_file.json`, carved `extracted\*.bundle.js`).
- Pitfalls:
  - Strings are **UTF-16LE or Latin-1**: scan both encodings at **both even and odd offsets**; accept code units > 127
    (Chinese text otherwise cuts the runs).
  - Region size threshold 0.5 MB (a bundle sat in a 530 KB region; a 2 MB filter missed it).
  - `[anon:libc_malloc]` = ArrayBuffers, atlases, Spine data; `[anon]` with Rss > 512 K = JS source + V8 string table;
    `[anon:Mem_0x*]` was empty.
  - "Dead on version X" was once a wrong-game-open mistake (1.1 GB dump, nothing): re-check run conditions first.
  - Make sure the carved bundle is the one that runs (old vs rewritten game were confused twice): cross-check with
    something visible (number of booster buttons…).
  - SIGSTOP freezing did not catch transient loads.
  - Ad blocking: `settings put global http_proxy 127.0.0.1:1` + `pm disable` of ad activities. **Never `svc wifi disable`**
    (see `device-ldplayer.md`).

### ❌ Attack the encryption (XXTEA key, caches, CDN)
- NUMPUZ 2026-08-05: key loaded at runtime, binary packed by `libpglarmor.so`; `files/subpackages`, `gameres_patch*`,
  `gamecaches` empty; `subpackage-route.json` only returns a version; XOR by filename gave nothing. Do not retry: carve RAM.

## Read rules from the carved JS

### Constant block + units
- Status: ✅ TombRun, DogJump, HexRescue · Cost: 1
- Constants sit in `_("g_fXxx", <num>)` near the top; follow one-letter aliases (`,H=t.g_f`). Box2D **PTM 32**:
  `_speed=16` = 512 px/s (video 514–528). Read every trigger path, not the first one found.
- Pitfalls: timing read from a Spine timeline was wrong (0.133 s vs `g_fActDelay=0.5`): constants win. Widget / prefab
  values (margins, font size, fit mode) are **not** in the bundle → measure (`no-data.md`).

### Code first, then scan data with the real struct
- Status: ✅ TombRun 2026-08-06 (594 layouts) · Cost: 3
- The code (`preLoadPassData`) showed levels are a BufferAsset of int32 `[w][h][w*h cells]` × up to 10 per file;
  `_tomb_run_dumps\extracted\scan_levels.ps1` then matched on the cell value set.
- ❌ before that: scanning float32 triples, float64, SMI values (data lives outside the V8 heap); `.bin` files were Spine
  skeletons; screenshot tiling (camera scrolls).

### True order through a V8 Map (pointer chasing)
- Status: ✅ TombRun (49/50 keyed + 1 by elimination) · Cost: 4
- Pointer compression (cage base in the dump), SMI = `v<<1`; chase FixedArray ← JSArray.elements ← JSObject field ← Map
  entry, read the int32 key before it (`_tomb_run_dumps\extracted\apply_order.py`,
  `chain_to_file.json`).
- Pitfalls: malloc order and heap order are both wrong (GC moves objects). Tables freed after parsing need a dump taken
  while the view using them is open.

### Index order
- Check iteration order in the code (HexRescue `createLayer` is column-major `col*4+row`; docs said rows). A wrong order
  still runs but builds something else.

## Custom containers (native Android app)

### "N00?" container (PBN)
- Status: ✅ BCA27 (188 pictures) · Cost: 2
- Format: magic, `N` u16 BE, `key` u16 BE (pad = key − 252); first and last N bytes swapped; strip padding; gunzip when it
  starts `1F 8B`.
- How: `py <studio>/pbn_sync.py` (pull `/sdcard/Android/data/<pkg>/files/<cache dir>`) → `py <studio>/build_bundle.py` →
  `<studio>/PBN_Data/`; ids in `<studio>/pic_map.json`. Make the app download a picture with its deep link
  `adb shell am start -a android.intent.action.VIEW -d '<scheme>://detail?id=<id>' <pkg>` (app running, on the library
  screen), poll the folder. Catalogue: root `/data/data/<pkg>/cache/retrofit/*.1`.
- Pitfalls: CDN zips AES-encrypted → open in-app. SQLite with WAL: copy `-wal`, delete `-shm`,
  `PRAGMA wal_checkpoint(TRUNCATE)`. `build_bundle.py` starts with rmtree: run it from a cwd outside the output.

## Source available (IFighter)
- The native C++ source existed: ported through an intermediate `projects/phaser_epic` and exported to JSON. Ask whether
  source exists before any extraction.
