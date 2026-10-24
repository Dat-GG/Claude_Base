# rip-original tools (shared by every game)

`<tools>` = this folder; its absolute path is given in `rip-original/SKILL.md` (`${CLAUDE_SKILL_DIR}/tools`, substituted
there only). Run from any working directory, always with the full quoted path (`py -I "<tools>/detect_engine.py" …`):
shell variables do not survive between Bash calls. Copy a tool into a game workspace only when the game needs a modified
version.

| Tool | What | Proven |
|---|---|---|
| `detect_engine.py` | engine / backend / versions / encryption hints of an apk, xapk, apks or folder (also a flat folder with `libil2cpp.so` + `global-metadata.dat`), without extracting; prints the reference to read next. Knows Unity IL2CPP + Mono, Cocos JS / Lua / C++, native C++, Godot, Unreal, Flutter, GameMaker, Defold, Solar2D, AIR, React Native, Xamarin, HTML5. Bad path / not a zip → one-line error, exit 2 | 2026-10-22 on E2D 2 (native, 243 RTTI, Box2D), UFD / Fish Sort (IL2CPP v31, 2022.3.62f2 / f3, YooAsset), HMR (v39, 6000.3.8f1, asset packs), 11 of our own builds; Mono on a probe build (see `engine-il2cpp.md`). Godot / Unreal / Lua / others: signatures from docs, 🧪 not met yet |
| `mono/mono_decompile.py` | Unity Mono build (apk / xapk / folder) → `Managed/*.dll` + ILSpy C# per type + `literals.tsv` (#US strings) | 2026-10-22 probe apk (exact constants, bodies, PlayerPrefs key), BC46 dll 600 KB → 320 files in 5.6–12.7 s |
| `ghidra/ghidra_query.py` | query an analyzed Ghidra project without re-analysis: `decomp` (decompile by name pattern), `syms` (static values at symbols, hex + f32), `asm` (whole-function listing around addresses), `byname` (listing by exact name). Runs the Jython scripts from a temp copy (no `_args$py.class` left in the plugin) | E2D 2026-10-10; re-tested 2026-10-21 (`CarModel::GetWheelRadius @005cfdf4`, `BlendFunc::ADDITIVE_PREMULTIPLIED = (1,1)`) and 2026-10-22 (28.6 s) |
| `ghidra/DecompNamed.py`, `DumpSyms.py`, `DumpAsm.py`, `DumpByName.py`, `_args.py` | the Jython postScripts behind `ghidra_query.py` (patterns come as `@file`); not run by hand | same |
| `il2cpp/il2cpp_literals.py` | where a string literal is used in an IL2CPP binary, no dumper needed: `extract` (xapk → metadata + arm64 libil2cpp.so) → `literals` (metadata v31 and v39) → `xref` (sections from the ELF) → `find` / `near` | HMR 1.4.1 v39 (2026-09-25; re-tested 2026-10-21: 1.4 s; 2026-10-22: whole chain 2.1 s, `rate_us` / `not_now` = analytics params); UFD v31 (15 159 literals = Il2CppDumper count) |
| `unity/RipMaterialConverter.cs` | Unity Editor menu `Bacon/Import/Convert Rip Materials to URP`: ripped Built-in materials → URP (copy into the project's Editor folder, set its PROJECT CONSTANTS) | BC54 2026-10-16 (103 materials) |
| `unity/RipSceneLighting.cs` | Unity Editor menu `Bacon/Import/Fix Rip Scene Lighting (active scene)`: lightmapped renderers and the Mixed sun on separate rendering layers | BC54 2026-10-16 |
| `unity/rip_remap.py` | remap `m_Script` references of ripped scenes / prefabs / assets to the target project's real package scripts (DLL fileID = MD4 rule) | BC54 2026-10-16 (1,887 / 3,261 refs); `--dry` re-test 2026-10-22 (3 min, mostly indexing `Library/PackageCache`) |
| `unity/scene_mb_dump.py` | serialized MonoBehaviour fields under given GameObject paths of a ripped scene (scripts missing in the target) | UFD → BC54 2026-10-16; re-tested 2026-10-22 (1.2 s) |
| `transcript_find.mjs` | recover a script / command that only existed in an old session; searches main sessions and subagent transcripts (`node "<tools>/transcript_find.mjs" "<regex>" [--project X] [--full] [--out file]`) | recovered all of the above 2026-10-21; E2D `xref.py` / `plt.py` from a subagent transcript 2026-10-22 |

Origins of `unity/`: `RipMaterialConverter.cs`, `RipSceneLighting.cs` from
`<projects>/BC54_Food_Delivery/BC54_Food_Delivery/BC54_Food_Delivery/Assets/_Project/Scripts/Editor/Import/`;
`rip_remap.py`, `scene_mb_dump.py` from `<projects>/Urban_Food_Ripped/Tools/` (copied 2026-10-22).

Timings include the cold start: `mono_decompile.py` 5.6–12.4 s for a 600 KB dll (12.7 s measured 2026-10-22);
`ghidra_query.py` 45–75 s per run (JVM start + project open; 28.6 s seen 2026-10-22), so batch several patterns in one
call. `detect_engine.py` < 1 s, `il2cpp_literals.py` 1–4 s per step.

Examples (each line is a separate command; output paths must be real folders, e.g. the workspace `Decompiled/`):

```bash
py -I "<tools>/ghidra/ghidra_query.py" --project "<ghidra-projects>/E2D.gpr" --program libEarnToDie2.so \
   --out "<workspace>/Decompiled/query/explosion.c" decomp "StoryLevelState::OnExplosion"
py -I "<tools>/il2cpp/il2cpp_literals.py" extract game.xapk --out "<workspace>/Decompiled/literals"
py -I "<tools>/il2cpp/il2cpp_literals.py" literals "<workspace>/Decompiled/literals/global-metadata.dat" --out "<workspace>/Decompiled/literals"
py -I "<tools>/il2cpp/il2cpp_literals.py" xref "<workspace>/Decompiled/literals/libil2cpp.so" "<workspace>/Decompiled/literals/literals.tsv" --out "<workspace>/Decompiled/literals"
py -I "<tools>/il2cpp/il2cpp_literals.py" find "<workspace>/Decompiled/literals" "save|key"
node "<tools>/transcript_find.mjs" "DumpSyms\.py" --project BC46 --full --out "<workspace>/Tools/_save/found.txt"
```

Workspace-specific tools that already exist (copy, then edit their constants): see `references/workspace.md`.
