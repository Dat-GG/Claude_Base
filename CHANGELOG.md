# Changelog — bacon-unity standard

Mỗi bản: heading `## <version> — <ngày>` (`<version>+` = chỉ sửa `standards/` / `modules/`, không tăng version), dưới là
gạch đầu dòng `file — thay đổi (project nguồn)`. Mới nhất lên đầu.

## 0.1.12 — 2026-10-27
- `skills/size-audit/SKILL.md` §3: asset trong `Resources` của pack mà script editor của pack đọc → chuyển vào `Editor/Resources`,
  không ra thư mục thường; §4: ước tính APK ≈ 0,6 × packed cho texture / mesh / font (đo BC54: −30,7 packed → −18,9 APK) (BC54).

## 0.1.11 — 2026-10-27
- `skills/size-audit/BuildSizeAudit.cs`: build report không có packed asset (build tăng dần dùng lại data cũ) → dừng, báo cần
  Clean Build, không ghi đè `assets.tsv` bằng file rỗng nữa; `SKILL.md` §1 thêm bẫy này (BC54).

## 0.1.10 — 2026-10-27
- Skill mới `skills/size-audit` (+ `BuildSizeAudit.cs`, `who_uses.py`): rà dung lượng build từ `Library/LastBuild.buildreport`
  (MB theo asset / loại / thư mục, Combined Mesh của static batching, Resources không scene nào dùng, MB riêng của từng nhánh
  object trong scene build kèm trạng thái tắt + vertex static, import / player settings), tra ngược GUID, cuối cùng ra danh sách
  đề xuất A (an toàn) / B (cần quyết định) / C (chất lượng, cần mắt người) / D (hiệu năng, đo trên máy) + so sánh sau khi cắt
  (`assets_prev.tsv`). 7 bẫy ghi trong skill (BC54: APK 225 MB, tìm ra ~125 MB có thể cắt).

## 0.1.9 — 2026-10-24
- Repo chỉ giữ phần dùng chung: `migrations/BC46/` chuyển vào BC46 `.claude/bacon-migration/` (đường dẫn trong `MIGRATION.md` sửa
  theo); `recovered/` (bản gốc script khôi phục) chuyển về workspace: E2D → `<projects>/E2D_Ripper/Tools/_recovered/`,
  HMR → `<projects>/Traffic_Rider/_recovered/`. `skills/new-project` §3b: bản đề xuất ghi vào `<project>/.claude/bacon-migration/`.
  README: bỏ dòng `migrations/`, thêm `PLAN.md`, `setup-machine`. Các dòng cũ bên dưới nhắc `migrations/` / `recovered/` là lịch sử.

## 0.1.8 — 2026-10-23
- `hooks/guard.mjs`: tách lệnh theo dấu nháy (không tách ở `;` `|` `` ` `` `$(` trong nháy đơn, không tách ở `;` `|` `&&` trong nháy kép).
  Trước đó một lệnh `sed` có chữ "git clone" trong chuỗi nháy đơn bị chặn nhầm. Test lại toàn bộ ca hook: 0 lỗi.
- Đổi tên còn sót `_ClaudeStandard` → `Claude_Base` (README, add-lesson, setup-machine).

## 0.1.7 — 2026-10-23
- Repo chuyển sang `D:/GG_SnM/Tools/Claude_Base` (git của user, remote GitHub). Máy này: `standard` trong file máy, junction
  `~/.claude/bacon-standard` và marketplace `gg-snm` trỏ sang chỗ mới. Thêm `.gitignore` (cache Python / Jython, file tạm).
- `setup-machine/doctor.mjs`: `studio` = thư mục cha gần nhất của repo có `Project/` (repo có thể nằm trong `<studio>/Tools/`).

## 0.1.6 — 2026-10-23
- Mang sang máy khác được: đường dẫn máy chuyển thành key trong `~/.claude/bacon-machine.json` (`standard`, `studio`, `projects`,
  `tools-home`, `ghidra`, `ghidra-projects`, `jdk17`, `il2cppdumper`, `cpp2il`, `assetripper`, `dotnet`, `ilspycmd`, `ldplayer`,
  `adb-device`, `unity-editors`, `python`, `ffmpeg`); tài liệu ghi dạng `<key>` (~80 chỗ trong references, skills, agent, module,
  `user/CLAUDE.md`, BC46 `CLAUDE.md`). Project import chuẩn qua `@~/.claude/bacon-standard/...` (junction tới
  `<standard>/plugins/bacon-unity`; tài liệu Claude Code xác nhận hỗ trợ `@~/`): BC46, `templates/CLAUDE.md`, `migrations/BC46`.
- Skill mới `setup-machine` + `doctor.mjs` (Node, không cài gì): dò tool / thư mục (~13 s), `write` / `set` / `link`, kiểm tra Python
  libs, plugin, luật cá nhân; in nguồn tải cho thứ thiếu. `requirements.txt` cho Python libs.
- `hooks/common.mjs`: `expandPath` thay `<key>` từ file máy (profile dùng được `<projects>/...`); `session_start` in đường dẫn máy,
  báo thiếu file máy / junction.
- `tools/_machine.py`: script Python đọc file máy; `ghidra_query.py` (`ghidra`, `jdk17`), `mono_decompile.py` (`ilspycmd`, `dotnet`)
  hết đường dẫn cứng, thiếu key → lỗi 1 dòng chỉ sang /setup-machine.
- Máy này: đã tạo `~/.claude/bacon-machine.json` (đủ 17 key) + junction; BC46 profile `forbidden_names.file` = `<projects>/...`.

## 0.1.5 — 2026-10-22
- `skills/new-project` bước 0 viết lại theo user: bình thường user tự tạo project base rồi gửi path, Claude làm việc trên đó, không
  tự tạo / chép base; chép base từ project khác chỉ khi user yêu cầu (ngoại lệ DF). Bỏ câu hỏi "base lấy từ project nào".
  `modules/legacy-rebuild.md` mục base Unity mới hơn: chỉ áp dụng khi user yêu cầu.

## 0.1.4+ — 2026-10-22 (standards only)
- `standards/core.md`: JSON / save mặc định JsonUtility, không Dictionary; project được chọn khác (BCA17 Newtonsoft + Dictionary)
  nếu ghi rõ trong `CLAUDE.md` của project (user chốt: theo từng project).

## 0.1.4 — 2026-10-22
- Module mới: `modules/legacy-rebuild.md` (project cũ chỉ đọc, chép asset giữ `.meta`, sửa converter `Bacon/Migrate/*` chứ không
  sửa output + so ảnh chụp trước / sau, lấy base từ Unity mới hơn, Phần A = bảng cũ → mới, nhãn `[OLD?]`) (DF).
- Module mới: `modules/spine-2d.md` (khoá version Unity + spine-unity, chỉ qua 1 wrapper, `SkeletonAnimation.timeScale` = 1,
  `MaterialPropertyBlock`, tên anim / event kiểm bằng validator, thay art giữ PMA) (DF, P09).
- Module mới: `modules/world-3d.md` (scene `2_Gameplay` additive, không tham chiếu chéo scene, camera stack, `GameplayEditorBoot`,
  input Both vì pack, rip → URP trỏ sang `rip-original`, hiệu năng thành phố lớn) (BC54).
- Module mới: `modules/pack-reskin.md` (pack là game nên được sửa, đánh dấu `// <PROJECT_CODE>:`, re-skin tại chỗ, ẩn UI cũ bằng
  `CanvasGroup`, Figma trỏ sang `references/assets.md`) (P09, BC23T).
- Module mới: `modules/multi-game.md` (spec riêng từng game `GamePlan/<Game>/<Game>.md`, bẫy `Bacon.UIManager` / `MiniGame.UIManager`,
  registry `MiniGameData` + build list + `isRelease`, save qua `MiniGameSaveService`, menu `Tools ▸ <Game>`) (BCA30, BCA17).
- `modules/clone-rip.md`: DLL bên thứ 3 trong rip không có license, không ship (BC54); physics / time chép từ bản gốc vào B0, tự step
  physics khi bản gốc làm vậy (BC46 `PhysicsStepper`).
- `standards/core.md`: `modules` phải chứa module của type; bỏ type `template` (không có project nào), định nghĩa `original` (BCA17);
  `Packages/` cần user xác nhận (hook hỏi, `allow_packages`); pack là game được sửa; ProjectSettings lưu qua menu của project hoặc
  File > Save Project (bỏ menu `Bacon/Setup/Apply Physics & Layers` vì không có trong base); thêm 2 bài học MCP (DF); bảng profile đầy
  đủ chuyển sang `new-project` (core giữ bản tóm tắt).
- `standards/bacon-framework.md`: save đúng thực tế (gzip `.gd`, temp rồi thay; DF có `.bak` / `.corrupt` / `saveVersion` + `Migrate()`).
- `standards/docs-format.md` + `templates/`: khối handoff có `Lưu ý` ở cả 3 nơi; cột `D#` / `Q#`; template spec có Phần E, template
  plan có "Cách đảm bảo giống gốc" (DF, BC46, BC54 đều dùng); `docs.mechanics` có thể là pattern theo game.
- `skills/new-project`: trigger tiếng Việt, bước 0 lấy base từ project mới nhất (hỏi user), chọn type + module, điền `{{MODULE_TAGS}}`,
  bảng profile đầy đủ (`allow_packages`, `forbidden_names.min_length / allow / allow_paths`, `standard`, `project`), các ca thực tế khi
  nhận project cũ (DF, P09, BC54, BCA30).
- `skills/handoff`: bỏ trigger "chốt changelog" (thuộc `log-change`). `skills/add-lesson`: trỏ bảng profile + format CHANGELOG mới.
  `agents/reference-researcher`: thêm nhãn `[OLD?]`.
- `migrations/BC46/CLAUDE.md`: `python -I` → `py -I`.
- `README.md`: danh sách module thật; `standards/` / `modules/` sửa là có hiệu lực, không tăng version; `guard` hỏi khi sửa `Packages/`.
- `hooks/` (sau review chạy thử ~250 ca): `save_backup` bắt cả `execute_code` có `isPlaying = true` và menu `Edit/Play` (BC46 vào
  Play kiểu này ~40 % số lần, trước đây không backup), timestamp có ms, chỉ xoay vòng file backup thật, báo khi `save_file` không có;
  `track_edits` ghi cả thay đổi qua MCP (scene / prefab / asset, `execute_code` có lưu / ghi) để `stop_changelog` nhắc, thêm
  `forbidden_names.allow_paths`; `stop_changelog` mặc định `every-change` khi profile không ghi; `guard`: chặn thêm `git add/stage/notes/
  update-index/...`, git trong `bash -c` / `powershell -Command` / `cmd /c` / `( )` / `>`, `gh` ghi (`api -X POST`, `pr comment/review`…),
  hết chặn nhầm heredoc / comment / `echo`, hỏi khi shell xóa / ghi `.meta` / `Library/` / `Packages/`, `Packages/` đổi deny → ask,
  glob `**/` không khớp nhầm tên folder; `common`: luật đường dẫn theo thư mục Unity gần nhất kể cả khi profile ở thư mục cha, không quét
  xuống khi kiểm file (trước 0.5–1.9 s), input / state hỏng không in lỗi; `session_start`: BOM, heading `###`, cắt 40 dòng có dấu báo,
  báo profile hỏng JSON, xóa state > 30 ngày. Test: ~80 ca tự động + đường dẫn BC46 thật, ~40 ms / hook.
- `skills/rip-original` + `skills/ref-video`: `${CLAUDE_PLUGIN_ROOT}` chỉ được thay trong SKILL.md → SKILL.md khai báo
  `${CLAUDE_SKILL_DIR}/tools`, references / README ghi `<tools>`, mọi lệnh viết đủ đường dẫn (bỏ `$T` / `$FK` vì biến shell mất giữa
  các lần gọi). Xóa `_args$py.class`, `ghidra_query.py` chạy Jython từ thư mục tạm nên không sinh lại, tự tạo folder `--out`.
  `transcript_find.mjs` quét cả transcript subagent. Sửa 11 đường dẫn sai, đánh số lại "Names and code" (2b → 5). `detect_engine` /
  `mono_decompile` / `il2cpp_literals` báo lỗi 1 dòng thay vì traceback, `detect_engine` nhận folder output của `il2cpp_literals extract`.
  Khôi phục `xref.py` / `plt.py` (E2D, mất từ scratchpad) từ transcript subagent 2026-10-08 vào `E2D_Ripper\Tools\`. Tool rip → Unity
  dùng chung ở `tools/unity/` (`RipMaterialConverter.cs`, `RipSceneLighting.cs`, `rip_remap.py`, `scene_mb_dump.py`, chép từ BC54 / UFD,
  hằng số project tách lên đầu file).
- BC46 (project): `forbidden_names.allow` = Background / Mission / Localization (từ thường bị báo nhầm), `allow_paths` = Editor;
  `CLAUDE.md` `python -I` → `py -I`.

## 0.1.3+ — 2026-10-22 (standards only, no version bump)
- `standards/core.md` Coding rules: 4 dòng lấy ý từ Ponytail (dietrichgebert/ponytail, không cài plugin): thang tái sử dụng
  project → Bacon → Unity / package, không thêm thứ không yêu cầu, grep mọi caller + sửa gốc ở code chung, code di chuyển
  giữ xử lý lỗi.

## 0.1.3 — 2026-10-22
- `tools/detect_engine.py`: nhận diện engine từ apk / xapk / folder trong < 1 s (Unity IL2CPP / Mono + version + metadata,
  Addressables / YooAsset / asset pack, Cocos JS / Lua / C++, native C++ + RTTI, Godot, Unreal, Flutter, GameMaker, Defold,
  Solar2D, AIR, React Native, Xamarin, HTML5). Chạy đúng trên E2D, UFD, HMR, Fish Sort + 11 bản build của mình; sửa nhận nhầm
  `libgame.so` của Unity 6 thành cocos. Godot / Unreal / Lua / các engine khác: dấu hiệu theo tài liệu, chưa gặp game thật (🧪).
  `SKILL.md` bước 1 gọi script này trước.
- `tools/mono/mono_decompile.py` + cài .NET SDK 10 (`D:\Tools\dotnet`, không vào PATH) + ilspycmd 11.1: build Mono → C# đầy đủ
  thân hàm + `literals.tsv`. Thử trên apk Mono tự build (Unity 2022.3.62f3, ra đúng hằng số / công thức / key PlayerPrefs) và
  DLL BC46 (600 KB → 320 file, 5.6 s, 72/72 số float). Ghi vào `engine-il2cpp.md` mục Mono, `workspace.md`.

## 0.1.2 — 2026-10-21
- Thử XERJ (search server local) cho agent tra code dịch ngược: A/B −34 % token, nhanh 2.5×, cùng độ chính xác, nhưng tìm theo
  từ khóa trượt `CarCamera`, phải chạy server nền, tự đòi gửi report lên mạng → user chốt gỡ. Đã gỡ sạch (binary, data, `~/.xerj`);
  ghi ❌ kèm số liệu vào `references/workspace.md`.

## 0.1.1 — 2026-10-21
- Agent `reference-researcher`, skill `port-mechanic`, tool khôi phục từ transcript, kết quả thử REA (xem các dòng dưới).

## 0.1.0 — 2026-10-21
- Bản đầu, dựng từ khảo sát 18 project dùng Claude (BC23T → BC54, DungeonFighting):
  `standards/core.md`, `bacon-framework.md`, `docs-format.md`, `modules/clone-rip.md`, `templates/`,
  skill `new-project`, `playtest`, `log-change`, `handoff`, `add-lesson`, `rip-original` (8 reference, gom từ
  BC46 / BC54 / BC36 / BC45 / NUMPUZ / BCA27 / BCA21), `ref-video` + `framekit.py`, 5 hook (Node).
  Nguyên tắc mới trong core: chọn cách rẻ nhất đủ đúng; script dùng lại được phải lưu vào `Tools/`.
- Khôi phục từ transcript (thư mục scratchpad cũ đã bị dọn): 4 script Ghidra của E2D (2026-10-10) và tool chuỗi IL2CPP
  của HMR (2026-09-25). Viết lại dạng dùng chung trong `skills/rip-original/tools/` (`ghidra_query.py` thay file .bat,
  `il2cpp_literals.py` tự đọc section ELF + metadata v31/v39), chạy lại cho kết quả trùng với lần đầu. Bản gốc nguyên văn:
  `recovered/`. Thêm `tools/transcript_find.mjs` để lần sau tự khôi phục.
- Thêm skill `port-mechanic` (spec → research → spec → code → kiểm tra → log) và agent `reference-researcher`
  (chỉ đọc, context riêng, trả về giá trị + nguồn + nhãn), để file decompile / rip lớn không vào phiên chính.
- Thử REA (morluto/rea, npm 6.7.0) qua CLI, không đăng ký MCP: IL2CPP metadata chưa có trong bản phát hành (🧪, chờ bản mới);
  Ghidra provider trên Windows chỉ nhận PE, không nhận `.so` Android (❌); `inspect-managed-members` đọc DLL Mono nhanh (3 s) nhưng
  không ra code C# (🧪). Ghi vào `engine-il2cpp.md`, `engine-native-cpp.md`, `workspace.md`.
