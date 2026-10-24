# Asset conversion (any engine)

Original assets are temporary (`modules/clone-rip.md`): convert to use and compare, keep them in `Original/`.
Python: `py -I` (see `workspace.md`). Entries cheapest first.

---

## Unpack

### Python zipfile, only what is needed
- Status: ✅ E2D 2026-10-08, BC36 · Cost: 1
- `zipfile.ZipFile(apk).extractall(dst, [m for m in names if m.startswith('assets/') and '..' not in m])` for the base apk;
  `lib/` from `config.arm64_v8a.apk`; nested xapk via `io.BytesIO`. List the full tree first (a key file, `library.xml`,
  was overlooked once). apktool is only needed when Java / resources matter.

## Textures

### webp → PNG (cocos)
- Status: ✅ E2D · Cost: 1
- `<python> -I E2D_Ripper\Tools\convert_atlas.py --project <root> [--tier hi]` (Pillow, straight RGBA, size checked against the
  clip index); `convert_images.py --project` (crops black-padded power-of-two pages).
- Pitfalls: **cocos decodes webp premultiplied** (`Image::initWithWebpData` `MODE_rgbA`): shaders / blend modes must match
  (wrong blend = "white smoke too bright").

### ASTC → PNG: texture2ddecoder
- Status: ✅ DogJump 47 files 2026-08-20, HexRescue 36 · Cost: 1
- `py -I <projects>/BCA30_NUMPUZ/BCA30_Mini_Numpuz/GamePlan/_tools/astc-to-png.py <dir> --write` (dry run without `--write`). Header: magic `13 AB A1 5C`, block
  x/y/z, 24-bit LE w/h/d; decode → `Image.frombytes('RGBA',(w,h),dec,'raw','BGRA')`. Then import as Sprite / Single /
  PPU 100 / alphaIsTransparency, check no GUID references the `.astc`, delete it with `AssetDatabase.DeleteAsset`.
- Pitfalls: Unity has no `.astc` importer (looks like "can't change Texture Type"). PNGs left as `Default` type make
  `LoadAssetAtPath<Sprite>` return null. ≈ 1485 NUMPUZ `.astc` still unconverted (BlockPuz, BrickHit, ColorLink).
- Fallback 🧪 (cost 2): ARM `astcenc-sse4.1.exe -dl in.astc out.png` (no longer on disk). ❌ Unity GPU decompression
  (DirectX has no ASTC), ❌ imageio-ffmpeg (no astc decoder).

### WebP-lossless / PDF → PNG for data textures
- Status: ✅ BCA27 2026-07-31 · Cost: 1
- `BCA27_Paint\BCA27_Paint_by_Number\tools\import_picture.py` (Pillow + pymupdf): webp-lossless → PNG bit-exact; PDF rendered
  with `fitz` at map resolution; `--verify <id>` re-checks (0 px different).
- Pitfalls: data textures (region / id maps) must import Point / Uncompressed / no mip / sRGB off / NPOT None, or ids shift
  silently (an AssetPostprocessor enforces it). Empty line PDFs: check rendered ink coverage (< 3 %), not `get_drawings()`.
  Downscale alpha with BOX, not LANCZOS. Linear project: convert alpha measured on sRGB images.

### Irregular atlases / tinted sprites
- 🧪 DogJump: touching glyphs → uniform grid fails; split by alpha flood fill. Grey sprites are tinted at runtime
  (`sprite.color`): do not look for colored variants.

## Animation

### Flash-style movieclips (cocos `library.xml`)
- Status: ✅ E2D · Cost: 3
- Matrix quirk: skewY = 0 and skewX ≠ 0 drops the shear. 0.033 s / frame. Imported by BC46 `ClipImporter`; validated
  30,836 node-frames against the original formula (error ≤ 7e-6). Reuse the pattern: import + automatic comparison.

### Spine: detect the version
- Status: ✅ · Cost: 1
- Skeleton JSON `"spine":"3.7.94"` (TombRun index lists 40× 3.7.94; P09 = 3.8.99). No data: strings in the engine lib
  (`spine::VertexEffect` / `SwirlVertexEffect` → ≤ 3.8; `Sequence` / `PhysicsConstraint` / `Inheritance` → 4.x).
- Pitfalls: runtimes are version-locked (spine-unity 3.7 cannot load 3.8 data; 4.x `_Atlas.asset` fields do not copy into
  3.8). Check `Assets/Spine/version.txt` of the project.

### Spine from Cocos into spine-unity
- Status: ✅ TombRun 40/40 · Cost: 2
- Rename `.atlas` → `.atlas.txt`, add a blank first line, wire `SkeletonDataAsset.atlasAssets`, enable
  **`_StraightAlphaInput`** on every material (Cocos atlases are not PMA → white squares otherwise).
- Pitfalls: files with a wrong extension (`*.json` that are atlases). "Materials not set for atlas asset" = atlasAssets not
  wired. ❌ carving Spine skeletons from RAM (WaterSort: 672 MB dump, 0 skeletons): some effects are code + mask, not Spine;
  read the code first.

## Fonts

### FlatBuffers `.font` + SDF webp (cocos)
- Status: ✅ E2D · Cost: 2
- `<python> -I E2D_Ripper\Tools\convert_fonts.py --project <root>`: FlatBuffers vtable read with `struct` (no flatc), schema
  confirmed from the loader in the decompile.

### Figma font names → TTF → TMP SDF
- Status: ✅ P09 2026-10 · Cost: 2
- Font files supplied by the user (TTF / OTF). TMP: Sampling 90, Padding 9, atlas 1024, Dynamic SDFAA,
  LiberationSans fallback. Stroke `s` px at size `fs`: `_OutlineWidth = _FaceDilate = s / (0.18·fs)`.
- Pitfalls: a missing weight (Bold vs Regular) makes text slightly off: ask for the exact files. Sizes from Figma
  `fontSize`, or measured (`no-data.md`).

## Audio

### Copy original files under new ids
- Status: ✅ E2D (`import_audio.py`, byte-identical), NUMPUZ (159 bare mp3 in the APK) · Cost: 1
- Find a game's bundle by file count matching its `playSound` table plus the one long BGM.
- Unity import: BGM Streaming + stereo; SFX Decompress On Load + mono, Vorbis.

### Sound list and call sites from code
- Status: ✅ · Cost: 1
- grep `playAudio(` / `playSound` / the audio enum / `playMusic` (no `playMusic` = no BGM).

### Map events to clips from a reference video
- Status: ✅ NUMPUZ · Cost: 2
- `ffmpeg -af silencedetect` (ffmpeg path in `workspace.md`): event durations match clip lengths (96 ms / 212 ms); check
  silent screens (nothing above −60 dB).
- 🧪 poor value (cost 5): WASAPI loopback capture + cross-correlation narrowed 159 → 8 but swapped the two most common
  sounds. **Ask the user to listen to a pre-narrowed list** (5 min) instead.

## Locale / text
- ✅ E2D `build_locale.py --out <Raw>` (strings under new names). IL2CPP: `stringliteral.json` holds UI text.

## Data containers for Unity
- JsonUtility cannot read nested / root arrays: flatten
  (`<projects>/BCA30_NUMPUZ/BCA30_Mini_Numpuz/GamePlan/_tools/adventure-to-unity.js`, `spxdd-to-unity.py` → `;` / `|`
  text) or wrap as `{"items":[…]}`. Many small files → one TextAsset.

## Figma as the source of new art

### `download_assets` → `rawImages`
- Status: ✅ P09 2026-09-28, BC46 2026-10-21 · Cost: 1
- `mcp__claude_ai_Figma__download_assets {fileKey, nodeId, defaultFormat:"png", defaultScale:1}`, then download the
  `rawImages` URL (`curl -sL -o x.png "<url>"`).
- Pitfalls: the rendered export bakes an opaque white background; rawImages keep alpha but may be a few px off-size (ratio
  kept). 20 per node (`rawImagesTruncated`) → query child nodes. Pure vectors have no rawImage; group effects (a tint) are
  not downloadable (recolor). Node names lie: verify by image. The file is edited live: re-read metadata before each batch.
  Scan the whole page, not one frame. Set the canvas reference to the Figma frame size so coordinates map 1:1.
