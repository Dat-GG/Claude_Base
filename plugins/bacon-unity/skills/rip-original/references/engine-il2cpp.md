# Unity originals (IL2CPP; Mono notes at the end)

Proven on Urban Food Delivery → BC54 (`<projects>/Urban_Food_Ripped`), Highway Moto Rush → BC36
(`Traffic_Rider\ExportedProject`), Fish Sort → BC45 (`Fish_Sort_Ripper`), aMAZE → BCA21 (`AMAZE`). All were IL2CPP.

**Tools on disk**: AssetRipper GUI Free 1.3.14 `<assetripper>`
(logs next to it) · Il2CppDumper 6.7.46 `<il2cppdumper>` (config `RequireAnyKey:false`) · Cpp2IL
2022.1.0-pre-release.20 `<cpp2il>` · Ghidra 11.0.3 (see `engine-native-cpp.md`) · Python with UnityPy 1.25.3,
capstone 5.0.7, pyelftools, numpy (`workspace.md`) · Unity 2022.3.62f3 + 6000.3.16f1.
ilspycmd 11.1 `<ilspycmd>` (Mono builds). Not installed: AssetStudio, dnSpy.

**Order of attack** (cheapest first): rip YAML / ScriptableObject values → stub `.cs` names → `il2cpp_literals.py` (1 s, no dumper) / `stringliteral.json` →
`disasm.py` → Ghidra. Measuring video is the last resort: a serialized value beats a measured one.

**Address spaces cost the most time**: write down for every tool whether it prints an RVA, a VA or a file offset, and the
Ghidra image base (0x100000).

---

## Identify version / backend

### AssetRipper log line, metadata header
- Status: ✅ UFD 2026-10-15, Fish Sort 2026-10-05 · Cost: 1
- How: `grep -E "found Unity version|scripting backend|game structure" AssetRipper_*.log` ("IL2Cpp … 2022.3.62f3"), or the
  rip's `ProjectVersion.txt`, or `xxd -l 16 global-metadata.dat` → magic `af1bb1fa` + version (0x1f = v31 = 2022.3,
  v39 = Unity 6). UnityFS bundle headers carry the build version.
- Pitfalls: "Mixed structure, 'Unknown' backend, no valid assets" = not Unity (→ `SKILL.md` step 1). AssetRipper can report
  the patch level slightly off (UFD f2 vs f3).

## Get the files

### Nested zip in Python (xapk)
- Status: ✅ BC36 2026-09-25 · Cost: 1
- How: `zipfile.ZipFile(xapk)`, open each inner `.apk` via `io.BytesIO`. `global-metadata.dat`: base apk
  `assets/bin/Data/Managed/Metadata/`. `libil2cpp.so`: `config.arm64_v8a.apk` `lib/arm64-v8a/`. Addressables:
  `AddressablesAssetPack.config.astc.apk` `assets/aa/Android/*.bundle`. Play Asset Delivery replaces OBB (no game had OBB).

### Pull the installed split apk from LDPlayer
- Status: ✅ UFD 2026-10-15 · Cost: 1
- How: `MSYS_NO_PATHCONV=1 adb -s emulator-5554 shell pm path <pkg>` → `adb pull …/base.apk` + `split_config.arm64_v8a.apk`;
  `unzip -o -j split_config.arm64_v8a.apk lib/arm64-v8a/libil2cpp.so -d il2cpp`;
  `unzip -o -j base.apk assets/bin/Data/Managed/Metadata/global-metadata.dat assets/bin/Data/ScriptingAssemblies.json -d il2cpp`.
- Pitfalls: the installed version may differ from the ripped xapk (1.0.22 vs 1.0.23: different code / enums). **Take the
  binary from the same xapk you ripped.**

### On-demand asset packs from the device
- Status: ✅ BC36 2026-09-17/23 · Cost: 2
- When: content listed in `AddressablesPackMapping.asset` / `catalog.json` is missing from the rip (HMR had 3 of 12 bikes).
  An empty rip folder usually means Addressables / Play Asset Delivery.
- How: play until the game downloads them, then pull with root from
  `/data/data/<pkg>/files/assetpacks/<pack>/<ver>/<ver>/assets/aa/Android/*.bundle`; hashes match the catalog.
- Pitfalls: older downloaded packs on the device can have other hashes / old art.

## Extract assets and scenes

### AssetRipper GUI on the xapk
- Status: ✅ UFD, Fish Sort, HMR, aMAZE · Cost: 3 (minutes)
- How: open the `.xapk` directly (it handles the splits). Settings used: ScriptExportMode Hybrid, ScriptContentLevel Level2,
  ShaderExportMode Dummy, export Unity project → `Assets/{Mesh, Material, GameObject (prefabs), MonoBehaviour (SOs),
  Scenes, Scripts/Assembly-CSharp}`, `AuxiliaryFiles/{GameAssemblies, path_id_map.json}`.
- Pitfalls: IL2CPP scripts are stubs (empty bodies, no `#US` strings); shaders are dummies; sprite rects come out trimmed
  (use `preserveAspect`); occasional scale errors (a handlebar ×100); static batching gives unreadable
  "Combined Mesh (root: scene)" (split with `m_StaticBatchInfo`); `[SerializeReference]` unsupported; addressable /
  downloaded content missing. AnimatorControllers **are** exported (missing ones were not in the build).

### AssetRipper headless on a folder of bundles
- Status: ✅ BC36 2026-09-17 · Cost: 2
- How: `AssetRipper.GUI.Free.exe --headless --port 5555`, `POST /LoadFolder`, `POST /Export/UnityProject`. Output keeps the
  original paths → merges into the main rip.
- Pitfalls: without assemblies loaded, scripts get the stub GUID `0000000deadbeef15deadf00d0000000`, which is also used for
  unresolved materials (fileID 2100000), meshes (4300000), avatars (9000000). **Never replace it file-wide**: only `m_Script`
  with fileID 11500000 (a global replace broke 95 + 53 slots).

### UnityPy on single bundles
- Status: ✅ BC36 2026-09-23 · Cost: 2
- When: a few values / prefab trees from a bundle without a full rip.
- How: `UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.0f1"`; `env = UnityPy.load(bundle, monoscripts_bundle)`;
  MonoBehaviours: `obj.read_typetree()`; class name via `d.m_Script.read().m_ClassName`.
- Pitfalls: `read_typetree` on the ObjectReader, not on `.read()`'s result. Load the `*_monoscripts_*.bundle` too.

## Read values (cheapest, try first)

### Grep the rip's YAML (prefabs, ScriptableObjects, catalog)
- Status: ✅ HMR boosters 2026-09-11, BC36 Baseline.asset · Cost: 1
- How: grep `Assets/GameObject/*.prefab`, `Assets/MonoBehaviour/*.asset`. Addressables: `catalog.json` `m_InternalIds` +
  base64 `m_KeyDataString` map GUIDs to prefab paths.
- Pitfalls: remote-config values are not in the build. A law measured from video looked speed-based; the config was
  distance-based → read the data before measuring.

### `scene_mb_dump.py` / exporters for huge scenes
- Status: ✅ UFD 2026-10-16 · Cost: 1
- How: `py -I "<tools>/unity/scene_mb_dump.py" --scene <rip>/Assets/Scenes/GamePlay.unity --scripts
  <rip>/Assets/Scripts/Assembly-CSharp [--depth N] "<GameObject path>"` → MonoBehaviour fields per object (script GUID →
  class via `.cs.meta`; 1.2 s on the UFD GamePlay scene). Origin: `<projects>/Urban_Food_Ripped/Tools/`, where the
  game-specific `export_delivery_data.py`, `export_city_data.py` (→ JSON for editor wiring tools; index paths: many objects
  share names) still live.

## Names and code

### 1. Stub `.cs` in the rip
- Status: ✅ HMR, UFD · Cost: 1
- Gives class / field / method / enum names, `[CreateAssetMenu]`, serialized field lists. No constants, initializers,
  PlayerPrefs keys or tags.

### 2. Il2CppDumper
- Status: ✅ UFD 2026-10-15 (metadata v31) · Cost: 2
- How: `cd /d/Tools/Il2CppDumper && ./Il2CppDumper.exe libil2cpp.so global-metadata.dat <out>` → `dump.cs` (field offsets,
  method RVAs, TypeDefIndex), `script.json`, `stringliteral.json` (save keys, UI text), `il2cpp.h`, DummyDll.
- Pitfalls: "This file may be protected" was harmless; `RequireAnyKey:false` or it waits for a key. Not tried on v39 (Unity 6).

### 3. Cpp2IL diffable C#
- Status: ✅ UFD 2026-10-15 · Cost: 2
- How: `./Cpp2IL.exe --force-binary-path libil2cpp.so --force-metadata-path global-metadata.dat --force-unity-version <ver>
  --use-processor attributeinjector --output-as diffable-cs --output-to Decompiled/cpp2il_cs`.
- Pitfalls: its printed "RVA" is a file offset (UFD: code VA = offset + 0x4000).

### 4. `disasm.py` (capstone + dumper names)
- Status: ✅ UFD 2026-10-16 · Cost: 1 (≈ 1.3 s per class)
- How: `<python> -I Urban_Food_Ripped\Tools\disasm.py <Class> [Method]` or `--rva 0x…`: BL targets named from `script.json`,
  ADRP+LDR resolved to string literals / metadata, float constants, `[this+off]` → field names.
- Pitfalls: SO / dump paths are constants at the top of the script: copy it into the new workspace and edit them.

### 5. String-literal cross-reference without a dumper (any metadata version, Unity 6 included)
- Status: ✅ HMR 1.4.1 v39 2026-09-25, re-tested 2026-10-21 (1.4 s); UFD v31 (15 159 literals, = Il2CppDumper) · Cost: 1
- When: "where is string X used / is this a save key / which function sends this analytics event", before any dumper or
  Ghidra; also when the dumper does not support the metadata version.
- How (one command each, full path every time; `W` = a work folder such as `<workspace>/Decompiled/literals`):
  `py -I "<tools>/il2cpp/il2cpp_literals.py" extract game.xapk --out W` →
  `py -I "<tools>/il2cpp/il2cpp_literals.py" literals W/global-metadata.dat --out W` →
  `py -I "<tools>/il2cpp/il2cpp_literals.py" xref W/libil2cpp.so W/literals.tsv --out W` →
  `py -I "<tools>/il2cpp/il2cpp_literals.py" find W "<regex>"` (each use + the literals used within ±0x800 = identifies
  the function) / `... near W 0x<addr>`. Whole chain 2–4 s on HMR (2026-10-22). `W` is also a valid
  `detect_engine.py` input (flat libil2cpp.so + global-metadata.dat → unity-il2cpp + metadata version).
  Mechanism: data slots `(5<<29)|(idx<<1)|1` → R_AARCH64_RELATIVE relocation → GOT entry → ADRP+LDR uses in executable
  sections. arm64 only.
- Pitfalls: the original scripts were lost in a scratchpad and recovered from the transcript; this version reads section
  offsets from the ELF instead of hard-coding them.

### 6. Ghidra headless with dumper symbols
- Status: ✅ UFD 2026-10-15 (≈ 15 min, 863 functions / 89 classes) · Cost: 5
- How: `<python> -I Tools/ghidra/prep_symbols.py <il2cppdumper out> <cpp2il_cs> Decompiled/ghidra_input` (symbols / targets /
  fields `.tsv`) → `Tools/ghidra/run_decomp.bat` (`analyzeHeadless -import libil2cpp.so -noanalysis -postScript
  ApplyIl2CppSymbols.py -postScript ExportGameDecomp.py`, MAXMEM 12G) → `Decompiled/game/<Class>.c` →
  `annotate_fields.py fields.tsv Decompiled/game`; constants with `readdat.py`.
- Pitfalls: dumper addresses are RVAs, Ghidra base 0x100000 → add it (first run mislabelled everything). Ghidra marks the GC
  write barrier noreturn → truncated / glued functions (`ExportGameDecomp.py` clears it; else check with `disasm.py`).
  Needs ≈ 12 GB free RAM (a second run was killed) → prefer entry 4.

### Obfuscated code (Beebyte)
- Status: ✅ BC45 2026-10-05 · Cost: 2
- How: reference worktree `<projects>/Fish_Sort_Ripper` (C# with bodies + `// RVA 0x…`, names like `doaaaaaa`).
  Ignore methods marked as Beebyte fakes (no bl / b, delegate, vtable or UnityEvent reference). Roles come from hard-coded
  asset-path literals and serialized prefab data. Keep an obfuscated → role table + `file:line` citations in the spec; mark
  doubtful ones `[TODO]` and confirm in the disassembly.
- Pitfalls: when two code paths exist (A/B groups), check which one actually runs.

## Materials and shaders

### Trust the material, not the shader dump
- Status: ✅ aMAZE, HMR, UFD · Cost: 1
- `.mat` holds the real properties, colors, textures and shader name; `.shader` files are stubs. Infer the shader from its
  name + properties (aMAZE `Custom/WorldSpaceToonVertex`: `_HColor/_SColor/_RampThreshold`; HMR `RUNNER/Standarino`:
  `_MainTex` AO in alpha, `_RME` R rough / G metal / B emissive, `_Normal`). Some materials have no shader at all.

### Tune against screenshots in edit mode
- Status: ✅ aMAZE · Cost: 2
- How: in `execute_code`, render `Camera.main` to a RenderTexture → PNG, `GetPixel` region colors, compare with the
  original's screenshot. No Play mode needed (24-bit depth RT if stencil masks are used).

### Built-in → URP
- Status: ✅ BC54 2026-10-16 (103 materials) · Cost: 2
- How: copy `<tools>/unity/RipMaterialConverter.cs` (menu `Bacon/Import/Convert Rip Materials to URP`) and
  `<tools>/unity/RipSceneLighting.cs` (menu `Bacon/Import/Fix Rip Scene Lighting (active scene)`) into an Editor folder
  of the new project, then set their PROJECT CONSTANTS (rip folder marker `/Original/Rip/`, URP asset paths). Converter:
  Legacy Diffuse / Specular → Simple Lit, Standard → Lit, Transparent / Cutout → Simple Lit alpha, particles →
  Particles/Unlit. Lighting: lightmapped renderers → rendering layer 1, Mixed sun → layer 0. Both need URP (with an
  Editor asmdef: reference `Unity.RenderPipelines.Universal.Editor` + `.Runtime`). Origin:
  `<projects>/BC54_Food_Delivery/BC54_Food_Delivery/BC54_Food_Delivery/Assets/_Project/Scripts/Editor/Import/`.
- Pitfalls: `_SpecularHighlights` is an enum, 0 = on (inverted → everything glossy; call `BaseShaderGUI.SetMaterialKeywords`).
  Baked lightmaps already contain the sun → Mixed lights affect dynamic objects only. Keep Gamma if the original used it.
  Vendor packs: use their own URP shaders.
- Alternative ✅ BC36 (cost 3): a URP shader with the **same property names**, so no `.mat` needs editing; built-in leftovers
  → URP/Unlit transparent (copy `_MainTex` → `_BaseMap`).

## Addressables / bundles / YooAsset
- ✅ HMR: read `AddressablesPackMapping.asset` + `catalog.json` to know what is missing, pull packs, rip headless or UnityPy.
- ❌ partial (Fish Sort): YooAsset OfflinePlayMode, ≈ 2,975 bundles in `StreamingAssets/yoo`; the AssetRipper rip had
  neither the bundles nor the code. Loose JSON edits do nothing until bundles are rebuilt.

## Saves / PlayerPrefs
See `save-files.md`.

## Using the rip as a Unity project
- Status: ✅ BC36, BC45, BC54 · Cost: 2
- Open it in the matching editor version, install the same Unity MCP package; it is a **read-only reference**.
- Two editors open → pin our instance on every reconnect (`mcpforunity://instances`, `set_active_instance`, pass
  `unity_instance`, check `Application.dataPath`): commands silently went to the reference editor once.
- Remap ripped script references to real packages: `py -I "<tools>/unity/rip_remap.py" --rip <rip Assets>
  --target <project> [--dry] FILE...` (DLL fileID = MD4("s\0\0\0" + namespace + class)[0:4] as LE int32; BC54 restored
  1,887 / 3,261 refs in `2_Gameplay.unity` 2026-10-16). ✅ cost 2: indexing the target's `Library/PackageCache` took
  3 min on BC54 (2026-10-22, `--dry` on the UFD Splash Scene: 47 mapped / 6 unmapped). Origin:
  `<projects>/Urban_Food_Ripped/Tools/rip_remap.py`.

### 🧪 REA `inspect_il2cpp_metadata` (morluto/rea) — not usable yet
- Tried 2026-10-21: the metadata decoder (v24 / 27 / 29 / 31 / 39, method → code address with the binary) exists only on the
  repository `main`; the npm release `rea-agents@6.7.0` (2026-10-18) has no such command. Re-check when a newer release is
  out (`npm view rea-agents version`; command `inspect-il2cpp-metadata`), then compare with Names and code entries 2 / 5 on UFD (v31) and
  HMR (v39) before adopting it.

## Mono builds (`assets/bin/Data/Managed/Assembly-CSharp.dll`)
No Mono **original** met yet; the steps below are proven on our own builds. `detect_engine.py` says `unity-mono`.
Mono on Android is usually armeabi-v7a only: irrelevant here, the code is managed IL.

### 1. `mono_decompile.py` (ILSpy): full C# with bodies
- Status: ✅ probe apk (Unity 2022.3.62f3 Mono, 2026-10-22) + BC46 `Assembly-CSharp.dll` (600 KB → 320 `.cs` in
  5.6–12.7 s incl. cold start, 72 / 72 float literals of 40 gameplay files found) · Cost: 1
- How: `py -I "<tools>/mono/mono_decompile.py" <game.xapk | apk | folder> --out
  <workspace>/Decompiled/mono` → `Managed/*.dll` (all, used as references), `src/<Assembly>/**.cs` (one file per type,
  namespaces as folders), `literals.tsv` (every `ldstr` string: save keys, events, UI text). Game assemblies by default
  (`Assembly-CSharp*` + anything not engine / BCL / ad SDK); `--all` adds plugins (DOTween, Spine…); `--dll X.dll` for one.
  Then grep `src/` like the native per-class export.
- Pitfalls: the compiler has already folded constants: `1.0f` prints as `1f`, `0.01f * Mathf.Rad2Deg` as `0.5729578f`,
  `const` fields are inlined at every use (the declaration is kept). Code inside `#if` symbols that were off in that build
  does not exist in the dll. Partial classes come out as one file. A dll not starting with `MZ` is encrypted (the script
  warns): the key is in a native loader. Obfuscator attribute markers are reported by `detect_engine.py`.
  Tools: .NET SDK 10 `<dotnet>` + ilspycmd 11.1 `<ilspycmd>` (not on PATH; the script sets `DOTNET_ROOT`).

### 2. 🧪 REA (no install, `npx -y rea-agents@6.7.0 inspect-managed-members <dll> --format json`), cost 1, tried 2026-10-21 on our
  own BC46 `Assembly-CSharp.dll` (600 KB, 3 s): types, fields, methods + signatures, **call edges** (who calls what),
  **field accesses** (who reads / writes what), `ldstr` literals. No C# bodies (only IL opcode counts / hashes). Output is
  huge (16.7 MB JSON for 600 KB): filter it (`--filter-output`) or query it with node, never Read it whole. Useful for
  "who uses field X / where is string Y"; for the rule itself use ILSpy.
