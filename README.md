# japan-crime-video-factory

Dây chuyền làm **video vụ án tiếng Nhật** khổ dọc 9:16 (1080×1920) cho Shorts / TikTok / Reels, theo video mẫu của chủ kênh ([`00-video-mau/MAU-VU-AN.mp4`](00-video-mau/MAU-VU-AN.mp4)): nền đen, ảnh kiểu **ảnh cũ** (màu phai, hạt, bụi, vết xước) phóng chậm, đổi ảnh mỗi 3–4 giây, **chữ vàng 2–3 từ** chạy đúng theo giọng đọc, **tiêu đề vụ án** ở trên cùng. Giọng đọc tiếng Nhật. Chạy hoàn toàn trên GitHub.

Repo song sinh: [`maihaianh2911-bit/germany-crime-video-factory`](https://github.com/maihaianh2911-bit/germany-crime-video-factory) làm cùng kiểu video bằng tiếng Đức.

## Làm một video

1. **Issues → New issue → 🔎 Video vụ án** ([mở thẳng](https://github.com/maihaianh2911-bit/japan-crime-video-factory/issues/new/choose)). Dán kịch bản (tiếng Việt hoặc tiếng Nhật) → **Create**. ChatGPT cũng tạo phiếu được, theo mẫu trong [`docs/CHATGPT.md`](docs/CHATGPT.md).
2. Không cần làm gì thêm. Claude chia lời (dịch sang tiếng Nhật nếu cần) → máy tạo giọng đọc, tự kiểm tra phát âm, tìm ảnh thật và tạo ảnh minh họa → Claude xem từng ảnh, chọn ảnh đúng với câu đọc, xem trước khung hình → máy dựng video → Claude kiểm tra lại từng cảnh. Mỗi bước báo trong phiếu.
3. Bình luận cuối có link **xem / tải video (MP4)**, **phụ đề** (SRT), **nguồn ảnh** (dán vào mô tả video) và **bảng nguồn từng cảnh**.
4. Muốn sửa: viết **một bình luận** gom hết yêu cầu, ví dụ "cảnh 3 đổi ảnh khác, câu 5 đọc sai tên". Claude sửa và dựng lại trên cùng phiếu.

## Ảnh

- **Ảnh thật trước**: nơi xảy ra, nhà, nhà thờ, tòa án, báo cũ, tài liệu — chỉ ảnh được phép dùng trong video kiếm tiền (phạm vi công cộng, CC0, CC BY, CC BY-SA) từ Wikimedia Commons, Openverse (Flickr…), Europeana, Thư viện Quốc hội Mỹ.
- **Ảnh AI minh họa** khi không có ảnh thật cho câu đó (căn phòng, buổi tối, phiên tòa…): luôn có chữ **"イメージ（AI生成）"** trên ảnh, **không vẽ mặt người thật**, không máu me, không chữ giả. Cần một khóa tạo ảnh (xem Cấu hình); chưa có khóa thì video chỉ dùng ảnh thật.
- Mọi ảnh đều được làm thành **ảnh cũ** như mẫu (giấy tờ, báo thì giữ rõ nét).

## Nhãn trên phiếu (máy tự gắn)

| Nhãn | Ý nghĩa |
|---|---|
| `crime-plan` | Chờ Claude chia lời và chọn từ khóa ảnh |
| `crime-voice` | Máy đang tạo giọng đọc, tìm ảnh, tạo ảnh minh họa |
| `crime-pick` | Chờ Claude chọn ảnh |
| `crime-render` | Máy đang dựng video |
| `crime-check` | Chờ Claude kiểm tra từng cảnh |
| `crime-done` | Video xong (link ở bình luận cuối) |
| `crime-fix` | Bạn yêu cầu sửa, Claude sẽ làm |
| `crime-failed` | Máy gặp lỗi, Claude sẽ xem |

## File kết quả

Nhánh **`renders`**, thư mục `crime/<số phiếu>/`: `video.mp4`, `subtitles.srt`, `credits.txt` (nguồn ảnh + ghi chú ảnh AI), `sources.json` (từng cảnh: lời, ảnh, nguồn, ảnh AI hay thật), `sheet.jpg` (ảnh các cảnh). Video của phiếu không hoạt động quá 14 ngày sẽ được dọn tự động, nên hãy tải về sớm.

## Cấu hình (làm một lần)

- **Secrets** (Settings → Secrets and variables → Actions):
  - `VN11_API_KEY` (giọng đọc 11labs, giống các repo khác);
  - `CLAUDE_TASK_URL` + `CLAUDE_TASK_TOKEN` (để GitHub gọi Claude khi có việc; **cùng giá trị** như repo `japan-video-factory`);
  - khóa tạo ảnh AI, chọn **một**: `OPENAI_API_KEY` (đẹp nhất, trả tiền theo ảnh), `GEMINI_API_KEY` (đẹp, trả tiền theo ảnh) hoặc `CF_ACCOUNT_ID` + `CF_API_TOKEN` (Cloudflare Workers AI, có phần miễn phí mỗi ngày, ảnh kém hơn).
- Chạy workflow **Tạo nhãn** một lần (tab Actions).
- Ngôn ngữ, giọng mặc định, chữ ghi trên ảnh AI: [`prompts/channel.json`](prompts/channel.json).

## Chạy tay (tab **Actions**)

| Workflow | Làm gì |
|---|---|
| **Video vụ án** | Chạy lại một bước cho một phiếu: `prepare` (giọng + ảnh), `search` (tìm thêm ảnh), `render` (dựng) |
| **Gọi Claude ngay** | Gọi Claude làm tiếp khi phiếu đang chờ (ví dụ sau khi hết hạn mức) |
| **Tìm ảnh (ảnh tự do)** | Tìm ảnh miễn bản quyền theo từ khóa |
| **Dọn video cũ (nhánh renders)** | Dọn file của phiếu cũ (tự chạy mỗi tuần) |
| **Tạo nhãn** | Tạo các nhãn của phiếu |

Hướng dẫn cho Claude: [`AGENT_NIGHTLY.md`](AGENT_NIGHTLY.md) (điểm vào khi GitHub gọi Claude) và [`AGENT_CRIME.md`](AGENT_CRIME.md) (các bước làm video). Bàn giao và các quyết định của chủ kênh: [`docs/HANDOVER.md`](docs/HANDOVER.md).
