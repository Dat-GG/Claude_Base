# Claude_Base — chuẩn bacon-unity

Chuẩn làm việc với Claude Code cho các project Unity (nền Bacon). Repo này bạn tự quản lý git.

```
.claude-plugin/marketplace.json     marketplace local "gg-snm"
plugins/bacon-unity/
  standards/  core.md · bacon-framework.md · docs-format.md   ← CLAUDE.md của project @import các file này
  modules/    theo type: clone-rip · legacy-rebuild · pack-reskin   theo công nghệ / dạng game: spine-2d · world-3d · multi-game
  templates/  CLAUDE.md · GAME_MECHANICS.md · PLAN.md · CHANGELOG.md · bacon-profile.json
  skills/     new-project · setup-machine · playtest · log-change · handoff · add-lesson · port-mechanic
              rip-original (+ references/: engine-native-cpp, engine-il2cpp, engine-js, assets,
                            device-ldplayer, save-files, workspace, no-data)
              ref-video (+ framekit.py: probe · sheet · frames · diff · mask · track · color · compare · fit)
              size-audit (+ BuildSizeAudit.cs: build report → MB theo asset / scene branch / Resources / settings; who_uses.py)
  agents/     reference-researcher (chỉ đọc: lục code dịch ngược / rip / data gốc, trả về số + nguồn + nhãn)
  hooks/      session_start · guard · save_backup · track_edits · stop_changelog (Node, không cần Python)
CHANGELOG.md                        lịch sử thay đổi của chuẩn (add-lesson ghi vào)
PLAN.md                             trạng thái + việc tiếp theo của chính repo này (khối ▶)
user/CLAUDE.md                      → chép thành ~/.claude/CLAUDE.md (luật cá nhân, mọi project)
```

Repo chỉ chứa phần dùng chung. Dữ liệu riêng của từng project (đề xuất chuyển sang chuẩn, memory cũ, bản khôi phục script)
nằm trong chính project / workspace đó, ví dụ `<project>/.claude/bacon-migration/`.

## Cài (máy nào cũng vậy: PC, laptop)

1. Clone repo này về máy, đặt ở đâu cũng được: `git clone https://github.com/Dat-GG/Claude_Base E:/Work/Claude_Base`.
2. Cài plugin:
   ```bash
   claude plugin marketplace add <đường dẫn repo>
   claude plugin install bacon-unity@gg-snm
   ```
3. Mở Claude Code, gõ `/setup-machine` (hoặc "setup máy"): dò tool + thư mục, ghi `~/.claude/bacon-machine.json`, tạo liên kết
   `~/.claude/bacon-standard` → `<repo>/plugins/bacon-unity`, chép luật cá nhân `user/CLAUDE.md`, báo thiếu gì (chỉ cài khi bạn đồng ý).
   Chạy tay: `node <repo>/plugins/bacon-unity/skills/setup-machine/doctor.mjs [check|write|set k=v|link]`.
4. Mang theo dữ liệu (không phải tool): thư mục project + workspace rip (`<projects>`), project Ghidra đã phân tích
   (`<tools-home>/ghidra_projects`).

Tài liệu ghi đường dẫn máy dạng `<ghidra>`, `<projects>`, `<ldplayer>`… (key trong `~/.claude/bacon-machine.json`, in ra ở đầu
session). `CLAUDE.md` của project import chuẩn qua `@~/.claude/bacon-standard/...`, nên không phụ thuộc ổ đĩa. Lần đầu mở mỗi project,
Claude Code hỏi duyệt import ngoài: chọn đồng ý.

## Sửa chuẩn

- `standards/` và `modules/`: project import thẳng từ repo này (không qua cache plugin), sửa là có hiệu lực ở session mới,
  **không tăng version**. Profile chọn module qua `type` + `modules` (`modules` luôn chứa module của type).
- `skills/`, `hooks/`, `templates/`: plugin được copy vào cache khi cài. Sửa xong: tăng `version` trong `plugin.json`, chạy
  `claude plugin marketplace update gg-snm` rồi `claude plugin update bacon-unity@gg-snm`, mở session mới.
- Cách nhanh nhất: trong bất kỳ project nào, gõ `/add-lesson` (hoặc nói "ghi bài học này vào chuẩn chung").

## Hook làm gì

| Hook | Khi nào | Làm gì |
|---|---|---|
| `session_start` | mở / resume session | in profile + khối "▶ Trạng thái & bước tiếp theo" của PLAN |
| `guard` | trước Edit / Write / Bash / PowerShell | chặn `Library/Temp/Logs/UserSettings/obj`, folder vendor trong profile; hỏi khi sửa `Packages/` (trừ khi profile `allow_packages`), `.meta` hoặc `_Project_Base`; chặn git / gh làm thay đổi repo |
| `save_backup` | trước MCP `manage_editor play`, `execute_code` có `isPlaying = true`, menu `Edit/Play` | chép save dev vào `~/.claude/bacon-backups/<project>/` (giữ 30 bản) |
| `track_edits` | sau Edit / Write và các tool MCP sửa scene / prefab / asset (`execute_code` chỉ khi code có lưu / ghi) | ghi thay đổi; project clone thì báo nếu code chứa tên gốc (rename map; bỏ qua `allow`, `allow_paths`) |
| `stop_changelog` | Claude dừng | profile `every-change` (mặc định): nhắc 1 lần nếu có thay đổi mà chưa ghi CHANGELOG |

`guard` còn: hỏi lại khi lệnh shell xóa / ghi đè `.meta`, `Library/`, `Packages/`; đọc cả git bọc trong `bash -c` /
`powershell -Command` / `cmd /c`; bỏ qua chữ "git" trong heredoc / comment / `echo`. Luật đường dẫn tính theo thư mục Unity gần nhất,
kể cả khi profile nằm ở thư mục cha. `session_start` báo profile hỏng JSON, cắt khối handoff ở 40 dòng (có dấu báo), xóa state > 30 ngày.

Thử hook không cần cài: `BACON_PROFILE=<profile.json> BACON_PROJECT_ROOT=<unity project> node hooks/<hook>.mjs < input.json`.
