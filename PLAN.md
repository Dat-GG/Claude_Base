# Plan — chuẩn bacon-unity (repo Claude_Base)

## ▶ Trạng thái & bước tiếp theo

- **Cập nhật:** 2026-10-24 · plugin **0.1.9** (repo chỉ còn phần dùng chung; dữ liệu BC46 / bản khôi phục về lại project), cài từ `D:/GG_SnM/Tools/Claude_Base` (marketplace `gg-snm`).
- **Đang ở:** đã xong review toàn bộ + sửa nhóm 1 (hook, tool, đường dẫn), nhóm 2 (5 module mới), chuẩn hóa đa máy
  (`~/.claude/bacon-machine.json`, junction `~/.claude/bacon-standard`, `/setup-machine`), chuyển repo sang `Tools/Claude_Base`.
  Lịch sử chi tiết: `CHANGELOG.md`.
- **User cần làm:**
  - `git add . && git commit && git push -u origin main` (remote `github.com/Dat-GG/Claude_Base`; Claude không chạy git ghi).
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
