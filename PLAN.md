# Plan — chuẩn bacon-unity (repo Claude_Base)

## ▶ Trạng thái & bước tiếp theo

- **Cập nhật:** 2026-10-30 · plugin **0.1.17** trong repo (marketplace `gg-snm` kiểu `directory`, từ `D:/GG_SnM/Tools/Claude_Base`):
  skill mới hiện ngay trong session, `installed_plugins.json` vẫn ghi 0.1.16.
- **Đang ở:** 0.1.14–0.1.17: Stop compile gate, researcher chạy Sonnet, hook `skill_usage` (+ tóm tắt 14 ngày / lần),
  description skill chỉ còn điều kiện kích hoạt, nhắc đối chiếu sau compaction + `Đã thử, không được` trong khối ▶, codegraph
  tùy chọn cho researcher, skill `ugui` / `tmp-fonts` (từ plugin Unity), tool in tóm tắt + bản đủ ra file, doctor biết
  `luajit-decompiler` / codegraph, `effort: low` cho `setup-machine`. Ngoài repo: claude-hud 0.14.0. Việc harness còn treo
  (memory `harness-backlog`): `/retro` (để sau), đo researcher trên Ghidra (Sonnet / Sonnet effort high / Opus), kiểm tên
  `read_console` + đổi Game view size bằng code (lần mở project Unity tới). Repo ngoài đã xem: memory
  `reviewed-external-repos`. Lịch sử chi tiết: `CHANGELOG.md`.
- **User cần làm:**
  - Commit các thay đổi 0.1.13–0.1.17 đang chưa commit (Claude không chạy git ghi).
  - Cài 0.1.17: `claude plugin marketplace update gg-snm` rồi `claude plugin update bacon-unity@gg-snm`.
  - Tùy chọn: muốn researcher dùng codegraph cho HTDT thì `cd D:/GG_SnM/Project/HTDT_Ripped/GameAssets/lua_src && codegraph init`
    (tạo `.codegraph/` 64 MB trong workspace rip). Không muốn dùng nữa: `npm rm -g @colbymchenry/codegraph`.
  - Session mới: gõ thử một `/<skill>`, xem `skill-usage.tsv` có dòng `user` không; khi có subagent chạy, xem dòng Agents
    trên HUD báo `reference-researcher` chạy Sonnet.
  - Tùy chọn: xóa các bản cũ 0.1.0–0.1.15 trong `~/.claude/plugins/cache/gg-snm/bacon-unity/`.
  - Mở session mới ở BC46, đồng ý hộp thoại duyệt import ngoài (`@~/.claude/bacon-standard/...`), kiểm tra luật chung được nạp.
  - Sau khi BC46 chạy ổn: xóa thư mục cũ `D:/GG_SnM/_ClaudeStandard` (không còn gì trỏ vào nó).
- **Chờ user cung cấp — nhóm 3, build / phát hành / SDK:** quy ước package id, chỗ để keystore, đặt tên apk / aab, `USE_*` nào bật
  cho bản release. Có thông tin → thêm mục "SDK & release" vào `standards/bacon-framework.md` + skill checklist `release-build`.
- **Chưa kiểm chứng:**
  - `/setup-machine` trên một máy khác thật (mới chạy trên máy này).
  - Import `@~/...` trong session tương tác (chế độ `-p` không nạp import ngoài cho tới khi duyệt).
  - Hook mới (0.1.4–0.1.8) trong session Claude thật: mới test giả lập (~80 ca).
  - 2 file `.cs` trong `skills/rip-original/tools/unity/` chưa compile thử trong Unity.
  - Script trong workspace rip (`<projects>/*_Ripper/Tools`) còn đường dẫn tuyệt đối bên trong: sửa khi chạy trên máy khác.
- **Quyết định đã chốt (2026-10-22/23):** JSON / save theo từng project (BCA17 Newtonsoft được); bỏ type `template`;
  không đưa save DF vào base BC46; BCA30 giữ changelog riêng từng game; base project do user tạo và gửi path (chép base từ
  project khác chỉ khi user yêu cầu); không cài skill Coplay; REA, XERJ, awesome-gamedev-agent-skills, Ponytail: không cài
  (Ponytail chỉ lấy 4 dòng vào `core.md`).
- **Lưu ý:** `D:/Tools/ghidra_projects/UFD.lock` cũ (15/10) còn đó, chỉ xóa khi user không mở UFD trong Ghidra.

## Việc có thể làm sau
- Nhóm 3 (release / SDK) khi có thông tin.
- Khi gặp engine mới (Godot, Unreal, Lua…): làm cách đọc thật rồi `/add-lesson` (hiện chỉ có nhận diện, 🧪).
- Nếu share cho team: chặn git thành tùy chọn trong profile, tách luật cá nhân khỏi plugin.
