# Bàn giao dự án (đọc trước khi làm việc với chủ kênh)

Repo này làm **video vụ án tiếng Nhật** (Shorts dọc 1080×1920, 30 fps): giọng đọc tiếng Nhật, kiểu hồ sơ vụ án trên mặt bàn (ảnh đen trắng, nhãn vàng, giấy ghi chép), phụ đề ô trắng chạy theo giọng, theo video mẫu của chủ kênh (`00-video-mau/`). Xây ngày 13/11/2026 cùng lúc với repo song sinh `maihaianh2911-bit/germany-crime-video-factory` (tiếng Đức): hai repo **cùng mã**, chỉ khác `prompts/channel.json` (ngôn ngữ, giọng, chữ ghi trên ảnh AI) và `prompts/readings.json`. Cách vận hành giống các repo khác của chủ kênh (phiếu → Claude chia lời → máy tạo giọng, tìm ảnh → Claude chọn ảnh, xem trước → máy dựng → Claude kiểm tra). Mã lấy từ `japan-archive-video-factory` (dây chuyền, xem trước, ảnh từ kho tự do) và `germany-news-video-factory` (kiểm tra giọng tiếng Đức).

## Chủ kênh

- GitHub `maihaianh2911-bit`. Nói chuyện **bằng tiếng Việt, ngắn gọn, dễ hiểu, không thuật ngữ**.
- Muốn **tự động hoàn toàn**: mở phiếu có kịch bản là có video; góp ý thì sửa trên cùng phiếu.
- Chỉ dùng **hạn mức gói Claude** (dùng chung với các repo khác), không dùng Claude API trả tiền; không giảm chất lượng.

## Quyết định của chủ kênh (giữ nguyên khi làm)

- 13/11: *"Tạo 2 repo mới cho dạng vụ án, chia ra Đức/Nhật"* + video mẫu → hai repo `germany-crime-video-factory` và `japan-crime-video-factory`, chia **theo ngôn ngữ kênh** (repo Đức: giọng và chữ tiếng Đức; repo Nhật: tiếng Nhật; vụ án ở nước nào cũng được).
- ~~13/11: dựng như mẫu cũ + tiêu đề (chữ vàng 2–3 từ, một ảnh cũ, tiêu đề trên cùng)~~ → thay bằng:
- 14/11: *"Đây là video mẫu mới, bỏ mẫu cũ đi"* + video mẫu mới (vụ gia đình Miyazawa, 4 phút 12 giây, lời Việt) → dựng **kiểu hồ sơ vụ án** như mẫu mới (xem `00-video-mau/README.md`): mặt bàn gỗ tối, ảnh đen trắng viền trắng, nhãn vàng viết tay, giấy ghi chép đánh máy, tiêu đề giấy xé, dấu đỏ, số lớn, dây đỏ; mỗi thứ hiện khi giọng đọc nhắc tới; phụ đề ô trắng nhỏ. Mẫu cũ đã xóa. Quy định ảnh AI (ghi "イメージ（AI生成）", không vẽ mặt người thật) giữ nguyên.
- 13/11: hình ảnh: **ảnh thật trước + AI minh họa** — ưu tiên ảnh thật (nơi xảy ra, báo cũ, tòa án); thiếu thì ảnh AI (kiểu ảnh đen trắng như mẫu), **luôn có chữ "イメージ（AI生成）"** trên ảnh và **không vẽ giống mặt người thật**. Không máu me, không chữ giả (báo, hồ sơ giả).

## Quy trình

Phiếu `[Vụ án] …` → `.github/workflows/crime.yml` + `scripts/crime/run.py` (máy) và `AGENT_NIGHTLY.md` → `AGENT_CRIME.md` (Claude):

`crime-plan` Claude viết `crime/<N>/script.json` (tiêu đề, câu đọc, từ khóa tìm ảnh, lời tạo ảnh AI) → `crime-voice` máy tạo giọng (11labs, một job mỗi câu), Whisper kiểm tra phát âm và lấy thời điểm từng từ, tìm ảnh (Commons, Openverse, Europeana, Thư viện Quốc hội Mỹ), tạo ảnh AI → `crime-pick` Claude xem ảnh, chọn, đặt khung, xem trước (`scripts/crime/preview.py`), viết `picks.json` → `crime-render` máy dựng (`src/crime/CrimeV.tsx`, Remotion) → `crime-check` Claude xem bảng cảnh → `crime-done`. Bình luận của chủ kênh → `crime-fix`. Kết quả: nhánh `renders`, thư mục `crime/<N>/`.

Bố cục đo từ video mẫu: `scripts/crime/layout.py`; dựng hình: `src/crime/CrimeV.tsx` (bản xem trước dùng chính mã này qua `scripts/crime/stills.mjs`, cần `npm ci`). Phụ đề chia cụm: `scripts/crime/captions.py` (`subs`). Ảnh đen trắng / ảnh cũ: `scripts/crime/prep.py`. Nền bàn gỗ, hạt phim: `scripts/crime/board.py`. Phông (4 loại: chữ thường, chữ có chân, chữ đánh máy, chữ viết tay): `scripts/crime/fonts.py`. Tạo ảnh AI: `scripts/gen_images.py`.

## Trạng thái (14/11/2026)

- Mã đã viết và thử bằng dữ liệu giả cả tiếng Nhật và tiếng Đức (`tests/crime_units.py`, `tests/crime_smoke.py --still`). Trên GitHub: workflow **Kiểm tra mã** chạy xanh, các nhãn `crime-*` đã tạo, tác vụ Claude chung (`AGENT_NIGHTLY.md` của `japan-video-factory`) đã kiểm tra phiếu vụ án của cả hai repo. **Chưa có video thật nào** (chưa có nhánh `renders`).
- 13/11 (sửa sau kiểm tra): chữ vàng tiếng Nhật không còn cắt giữa từ (思いま|すか, できな|かった, chữ nhỏ ょ ở đầu cụm), một dòng chữ rộng hơn (12 chữ Nhật); chữ tiếng Đức giữ dấu chấm của số thứ tự và chữ viết tắt (`AM 1. JULI`, `DR. MÜLLER`); bản xem trước đặt tiêu đề, nhãn và chữ đúng chỗ như video, chữ Đức nghiêng như video; vòng đỏ hình bầu dục trong video không còn bị xoay sai hình.
- 14/11: **đổi sang mẫu mới** (kiểu hồ sơ vụ án). `picks.json` giờ chia **cảnh** (`scenes`), mỗi cảnh có các **món** (`items`: ảnh, nhãn, tiêu đề, giấy ghi, dấu, số lớn, chữ lớn, dây đỏ) đặt theo tọa độ và hiện lúc giọng đọc nói tới chữ đó (`"at": "3:DNA"`). Bản xem trước giờ dựng bằng chính mã video (Remotion), không còn bản vẽ lại bằng Python (`frame.py` đã xóa). Phông: Noto Sans JP, Noto Serif JP, M PLUS 1 Code, Yusei Magic (Đức: Source Sans 3, Roboto Slab, Space Mono, Kalam). Thử bằng dữ liệu giả cả hai thứ tiếng; chưa có video thật theo mẫu mới.
- Còn thiếu, theo thứ tự:
  1. Secrets (Settings → Secrets and variables → Actions): `VN11_API_KEY` (giọng đọc, như các repo khác), `CLAUDE_TASK_URL` + `CLAUDE_TASK_TOKEN` (cùng giá trị như `japan-video-factory`).
  2. Khóa tạo ảnh AI (không bắt buộc) — **chủ kênh chưa chọn**: một trong `OPENAI_API_KEY` (đẹp nhất, trả tiền theo ảnh), `GEMINI_API_KEY` (đẹp, trả tiền theo ảnh), hoặc `CF_ACCOUNT_ID` + `CF_API_TOKEN` (Cloudflare, miễn phí mỗi ngày một số ảnh, kém hơn). Chưa có khóa thì video chỉ dùng ảnh thật (và ảnh chủ kênh gửi kèm phiếu).
  3. Video thật đầu tiên: mở một phiếu `[Vụ án] …`.
- Sau video đầu tiên: đo lại tốc độ đọc trong `AGENT_CRIME.md`, xem cỡ phụ đề, cỡ nhãn vàng, độ tối của nền bàn và độ tương phản của ảnh, so với mẫu, hỏi chủ kênh. Mẫu có thể có tiếng động nhỏ (máy đánh chữ, đóng dấu) — chưa làm.

## Lưu ý kỹ thuật

- `gh` trong phiên cloud chỉ dùng REST (`gh api …`), lệnh GraphQL lỗi.
- Wikimedia chặn tải ảnh gốc kích thước tùy ý (lỗi 429): chỉ lấy các cỡ chuẩn (1920, 3840 px) — đã xử lý trong `scripts/find_images.py`.
- ffmpeg trên máy GitHub lấy từ gói pip `imageio-ffmpeg` (xem `scripts/crime/ff.py`). Ghim `faster-whisper==1.1.1` + `av==13.1.0` (PyAV mới làm hỏng faster-whisper).
- Từ hay bị giọng đọc sai ghi vào `prompts/readings.json`.
- Phông: bốn loại cho mỗi tiếng (bảng `FAMILIES` trong `scripts/crime/fonts.py`); `scripts/crime/get_fonts.sh` tự chọn theo `prompts/channel.json`.
