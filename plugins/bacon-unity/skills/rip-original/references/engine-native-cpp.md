# Native C++ originals (cocos2d-x / custom engine)

Proven on Earn to Die 2 (FGKit on cocos2d-x + Box2D, `libEarnToDie2.so`, arm64) → BC46, workspace
`<projects>/E2D_Ripper`. Entries per task, cheapest first.

**Machine**: Ghidra 11.0.3 `<ghidra>`, analyzed project `<ghidra-projects>/E2D.gpr`.
Java for Ghidra = JDK 17 shipped with Unity 6 (`<jdk17>`);
the JDK 11 of Unity 2022.3 is too old. Python with capstone + pyelftools: see `workspace.md`.
No `strings` / `objdump` / `readelf` / `nm` in Git Bash: use Python.

---

## Confirm it is native (not Unity)

### Engine check: lib list + RTTI strings
- Status: ✅ E2D 2026-10-08 · Cost: 1
- When: AssetRipper gives an empty project (only Packages / ProjectSettings) → not Unity.
- How: see `SKILL.md` step 1 for the lib list. Then in Python: printable strings `re.finditer(rb'[\x20-\x7e]{5,}', data)`
  filtered on asset extensions (`\.(webp|xml|ebw|ogg|dat)`) → asset path formats; `_ZTS(\d+)Name` regex → class names
  (≈ 205 game classes = **not stripped**, Ghidra output will be readable); count `b2Body` vs Bullet / `Sprite3D` → 2D vs 3D.
- Pitfalls: in an xapk the native libs live in the split `config.arm64_v8a.apk`. `libunitycoherencenative.so` is the
  Unity Ads SDK, not a Unity game.

## Read rules and constants

### 1. Grep the per-class decompile export
- Status: ✅ BC46 · Cost: 1
- When: the class / method is a game class (already exported to `Decompiled/`).
- How: `grep -o "^// ==== [^ ]*" Decompiled/StoryLevelState.c` (methods of a class); `grep -l <Method>` (callers);
  grep string literals (`"photo_{:d}"`, `"Car{:d}"`) to find UI features. Compare the original GUI / State class list with
  the remake's panels to spot features never researched.

### 2. `readdat.py`: constants at an address
- Status: ✅ BC46 (through 2026-10-21) · Cost: 1
- How: `<python> -I E2D_Ripper\Tools\ghidra\readdat.py 0xbf922c 6 f32` (types f32 · f64 · i32 · u64 · str · bytes). Maps
  Ghidra address − image base 0x100000 through ELF PT_LOAD to a file offset.
- Pitfalls: `.bss` addresses ("not in file-backed segment") are set at runtime: read the static-init code or the
  immediates instead. Hex float immediates in the decompile (`0x4428c000` = 675.0) decode with `struct`.

### 3. Research reports (`Research/0N_*.md`) via parallel subagents
- Status: ✅ E2D 2026-10-08 (5 agents ≈ 75 min → 280 KB of spec) · Cost: 3 (once per game)
- How: one agent per system over `Decompiled/`, given the paths, `readdat.py` and the output report path; require
  `Class::Method @addr` on every rule and "(suy luận)" on anything inferred.
- Pitfalls: an agent without write permission returns its report as text only: give write access or collect the text.

### 4. Targeted Ghidra re-query (no re-analysis)
- Status: ✅ BC46 2026-10-10, re-tested 2026-10-21 · Cost: 2 (≈ 45 s per run)
- When: engine function not in `Decompiled/`, symbol values, instruction listing with resolved names.
- How: `py -I "<tools>/ghidra/ghidra_query.py" --project <ghidra-projects>/E2D.gpr
  --program libEarnToDie2.so --out <file> decomp|syms|asm|byname <patterns / addresses / names…>`
  (`decomp` = decompile functions whose full name contains a pattern; `syms` = static values at symbols, hex + f32;
  `asm` = whole-function listing around Ghidra addresses; `byname` = listing by exact name). Works for any analyzed
  project (`UFD.gpr` + `libil2cpp.so` too).
- Pitfalls (why the wrapper exists): hand-written `.bat` files broke on `"%~dp0"` without the dot (trailing `\"` → Ghidra
  opens the project and exits silently), on commas / quotes through cmd.exe, and on sed edits (CRLF). The scripts were
  lost once in a session scratchpad and recovered from the transcript (`<tools>/transcript_find.mjs`). Cold start
  45–75 s per run; the project must not be open elsewhere (`<project>.lock` next to the `.gpr`).

### 5. Raw instructions with capstone (decompiler output is wrong / unclear)
- Status: ✅ E2D 2026-10-08, BC46 2026-10-21 · Cost: 1
- When: Ghidra prints "Removing unreachable block", loses the `.y` of a returned `Point`, loses `this`, or shows a variable
  offset. Decompiled output lies in these known ways: do not guess, read instructions.
- How: `md = capstone.Cs(CS_ARCH_ARM64, CS_MODE_ARM); md.disasm(data[a-0x100000 : b-0x100000], a)` (for `.text` file
  offset = vaddr; otherwise map through PT_LOAD like `readdat.py`). Add a dynsym / symtab name map so `bl` targets show
  names. `py -I <projects>/E2D_Ripper/Tools/xref.py 0x<ghidra addr> [--so <lib.so>]`: scan ADRP+ADD/LDR pairs
  hitting a page / offset (who references a DAT; 1.4 s on the 14 MB E2D lib). `py -I <projects>/E2D_Ripper/Tools/plt.py
  <addr> … [--so <lib.so>]` (pyelftools `.rela.plt`): resolve PLT thunks (`FUN_00492040` → `FGKit::Point::Normalize`).
  Both default to the E2D lib; addresses in Ghidra space (base 0x100000). They were lost in a subagent scratchpad and
  recovered 2026-10-22 from the transcript (`<tools>/transcript_find.mjs "xref\.py|plt\.py" --full`), smoke-tested the same day.
- Found this way: ProcessTilt hidden `fccmp` branch, −0.6π from immediate `0xbff1463b`, garage shadow offset @0062be58,
  `ExplosiveObjectBehaviour::GetBreakVelocity` = 700 (barrels; crates `DynamicBreakableObjectBehaviour` = 100).
- Pitfalls: `PYTHONIOENCODING=utf-8` or Unicode output crashes on the cp1252 console.

### 6. First-time Ghidra import + analysis
- Status: ✅ E2D 2026-10-08 (465 s for a 14 MB arm64 .so) · Cost: 4 (once per game, keep the project)
- How: `Tools\ghidra\run_analyze.bat`: `set MAXMEM=12G`, prepend `<JDK17>\bin` to PATH, then
  `<ghidra>/support/analyzeHeadless.bat <ghidra-projects> <Game> -import <so> -overwrite -scriptPath <Tools\ghidra>
  -postScript ExportGameDecomp.py <outdir> -analysisTimeoutPerFile 7200 < nul`. Run in the background as
  `cmd //c "<workspace>\\Tools\\ghidra\\run_analyze.bat" > log 2>&1`, wait with `until grep -qE "<done marker>|Traceback" log`.
  `ExportGameDecomp.py` writes one `.c` per top namespace (`// ==== Class::Method @ addr` headers), skips ≈ 80
  engine / third-party prefixes (cocos2d, std, b2, png, ssl…) + `_index.txt`; `run_export.bat` re-exports with
  `-process … -noanalysis -readOnly`.
- Pitfalls: `JAVA_HOME` alone → "Java runtime not found" (Java must be on PATH; also set `JAVA_HOME_OVERRIDE` in
  `support\launch.properties`). Inline `cmd /c "…"` from PowerShell breaks quoting → always a `.bat`. Without `< nul` it
  can hang on "Press any key". "ERROR Invalid PNG data" is harmless. Sanitize `<>:"|?*` and `::` in output file names
  (Errno 13). Engine classes (render, blend, image decode) are excluded from the export but are needed later → entry 4.
- **Never re-import** an analyzed binary: every later question is entry 1, 2, 4 or 5.

### ❌ REA (morluto/rea) Ghidra provider for Android libraries
- Checked 2026-10-21 (`rea-agents@6.7.0`): its Windows Ghidra support is "experimental P0" and admits only Windows PE
  (`.exe` / `.dll`) and raw 6502 images — not the ELF `.so` of Android games — and needs Ghidra 12.1 + JDK 21 (machine:
  11.0.3 + JDK 17). Keep `ghidra_query.py`. Re-check only if REA announces ELF support on Windows.

### ❌ Dynamic analysis on LDPlayer (Frida native hooks, gdb)
- The game is ARM running through houdini on x86: native hooking / debugging does not work. `/proc/<pid>/mem` reading was
  proposed but never run (🧪, cost 4). Use static reading + behavioral baselines (`device-ldplayer.md`).

## Convert original data

### Custom binary level format → JSON (`.ebw.bin`)
- Status: ✅ 30/30 levels parse to the last byte (2026-10-08) · Cost: 2
- How: reverse from a hex dump, then confirm against the serializer in the decompile (`WorldBinarySerializer`).
  `<python> -I Tools\ebw2json.py <templates.xml> <in|dir> <out_dir>`. Format: int32 marker, count; per object a string,
  flags (0x01 name / 0x02 visible / 0x04 xy / 0x08 rot / 0x10 scale / 0x20 layer), graphic properties, behaviour block only
  when the template has `<behaviour>`; property types from `templates.xml` className; values equal to the template default
  are not stored (merge defaults).
- Pitfalls: **assert the parser consumes every byte of every file**. 0xCD padding only for int / float alignment
  (strings, bools packed). First header field is a marker, not a version. Rect = x,y,w,h in .ebw but x1 y1 x2 y2 in xml.

### Atlases, images, movieclips, fonts, audio, locale
See `assets.md` (cocos webp is premultiplied, Flash-style movieclip matrix quirk, FlatBuffers SDF fonts).

### Save file
See `save-files.md` (XOR with the first 5 chars of the Android ID, recovered from known plaintext).

## Keep the remake's data honest

### Rename map + generator with validation
- Status: ✅ BC46 (54 files, 15.6 MB) · Cost: 2
- How: `Tools\rename_map.json` (sections classes, methods, xmlAttributes, configKeys, templates, templateProperties,
  movieclips, childLabels, bones, missionLogics, particles, sounds, saveFields, misc) is the only original → new mapping.
  `build_data.py --out <project>\Assets\_Project\Data\Raw` re-derives rule-generated lists and fails on mismatch, then
  `gen_raw_models.py` generates JsonUtility models. The generator checks: numeric round-trip of every source number, no
  original identifier in the output, placement counts per stage, every output parses; exit 1 on failure. Emulate float32
  where the original computes in float32.
- Pitfalls: back up the map before big edits; edit with `io.open(..., newline='')` (CRLF). JsonUtility turns a missing
  array into null. To change a code-side constant: edit `build_data.py`, rebuild into a scratch copy, diff, then write.
