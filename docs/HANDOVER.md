# Bàn giao dự án (đọc trước khi làm việc với chủ kênh)

Repo này làm **video vụ án tiếng Nhật** (Shorts dọc 1080×1920, 30 fps): giọng đọc tiếng Nhật, chữ vàng ngắn chạy theo giọng, ảnh kiểu ảnh cũ, tiêu đề vụ án ở trên cùng, theo video mẫu của chủ kênh (`00-video-mau/`). Xây ngày 13/11/2026 cùng lúc với repo song sinh `maihaianh2911-bit/germany-crime-video-factory` (tiếng Đức): hai repo **cùng mã**, chỉ khác `prompts/channel.json` (ngôn ngữ, giọng, chữ ghi trên ảnh AI) và `prompts/readings.json`. Cách vận hành giống các repo khác của chủ kênh (phiếu → Claude chia lời → máy tạo giọng, tìm ảnh → Claude chọn ảnh, xem trước → máy dựng → Claude kiểm tra). Mã lấy từ `japan-archive-video-factory` (dây chuyền, xem trước, ảnh từ kho tự do) và `germany-news-video-factory` (kiểm tra giọng tiếng Đức).

## Chủ kênh

- GitHub `maihaianh2911-bit`. Nói chuyện **bằng tiếng Việt, ngắn gọn, dễ hiểu, không thuật ngữ**.
- Muốn **tự động hoàn toàn**: mở phiếu có kịch bản là có video; góp ý thì sửa trên cùng phiếu.
- Chỉ dùng **hạn mức gói Claude** (dùng chung với các repo khác), không dùng Claude API trả tiền; không giảm chất lượng.

## Quyết định của chủ kênh (giữ nguyên khi làm)

- 13/11: *"Tạo 2 repo mới cho dạng vụ án, chia ra Đức/Nhật"* + video mẫu → hai repo `germany-crime-video-factory` và `japan-crime-video-factory`, chia **theo ngôn ngữ kênh** (repo Đức: giọng và chữ tiếng Đức; repo Nhật: tiếng Nhật; vụ án ở nước nào cũng được).
- 13/11: dựng **như mẫu + tiêu đề**: chữ vàng in hoa (tiếng Nhật: chữ đậm vàng), 2–3 từ một lần, viền đen; ảnh cũ có viền, nền đen; thêm tiêu đề vụ án ở trên cùng suốt video.
- 13/11: hình ảnh: **ảnh thật trước + AI minh họa** — ưu tiên ảnh thật (nơi xảy ra, báo cũ, tòa án); thiếu thì ảnh AI kiểu ảnh cũ, **luôn có chữ "イメージ（AI生成）"** trên ảnh và **không vẽ giống mặt người thật**. Không máu me, không chữ giả (báo, hồ sơ giả).

## Quy trình

Phiếu `[Vụ án] …` → `.github/workflows/crime.yml` + `scripts/crime/run.py` (máy) và `AGENT_NIGHTLY.md` → `AGENT_CRIME.md` (Claude):

`crime-plan` Claude viết `crime/<N>/script.json` (tiêu đề, câu đọc, từ khóa tìm ảnh, lời tạo ảnh AI) → `crime-voice` máy tạo giọng (11labs, một job mỗi câu), Whisper kiểm tra phát âm và lấy thời điểm từng từ, tìm ảnh (Commons, Openverse, Europeana, Thư viện Quốc hội Mỹ), tạo ảnh AI → `crime-pick` Claude xem ảnh, chọn, đặt khung, xem trước (`scripts/crime/preview.py`), viết `picks.json` → `crime-render` máy dựng (`src/crime/CrimeV.tsx`, Remotion) → `crime-check` Claude xem bảng cảnh → `crime-done`. Bình luận của chủ kênh → `crime-fix`. Kết quả: nhánh `renders`, thư mục `crime/<N>/`.

Bố cục đo từ video mẫu: `scripts/crime/layout.py` (dùng chung cho video và bản xem trước). Chữ chia cụm: `scripts/crime/captions.py`. Hiệu ứng ảnh cũ: `scripts/crime/prep.py`. Tạo ảnh AI: `scripts/gen_images.py`.

## Trạng thái (13/11/2026)

- Mã đã viết và thử bằng dữ liệu giả cả tiếng Nhật và tiếng Đức (`tests/crime_units.py`, `tests/crime_smoke.py --still`). **Chưa có video thật nào**; chưa chạy trên GitHub.
- Còn thiếu, theo thứ tự:
  1. Secrets (Settings → Secrets and variables → Actions): `VN11_API_KEY` (giọng đọc, như các repo khác), `CLAUDE_TASK_URL` + `CLAUDE_TASK_TOKEN` (cùng giá trị như `japan-video-factory`).
  2. Khóa tạo ảnh AI — **chủ kênh chưa chọn**: một trong `OPENAI_API_KEY` (đẹp nhất, trả tiền theo ảnh), `GEMINI_API_KEY` (đẹp, trả tiền theo ảnh), hoặc `CF_ACCOUNT_ID` + `CF_API_TOKEN` (Cloudflare, miễn phí mỗi ngày một số ảnh, kém hơn). Chưa có khóa thì video chỉ dùng ảnh thật (và ảnh chủ kênh gửi kèm phiếu).
  3. Tác vụ Claude chung (`AGENT_NIGHTLY.md` của `japan-video-factory`) phải biết repo này (thêm dòng kiểm tra `crime`).
  4. Chạy workflow **Tạo nhãn** một lần.
- Sau video đầu tiên: đo lại tốc độ đọc trong `AGENT_CRIME.md`, xem cỡ chữ vàng và độ đậm của hiệu ứng ảnh cũ, hỏi chủ kênh.

## Lưu ý kỹ thuật

- `gh` trong phiên cloud chỉ dùng REST (`gh api …`), lệnh GraphQL lỗi.
- Wikimedia chặn tải ảnh gốc kích thước tùy ý (lỗi 429): chỉ lấy các cỡ chuẩn (1920, 3840 px) — đã xử lý trong `scripts/find_images.py`.
- ffmpeg trên máy GitHub lấy từ gói pip `imageio-ffmpeg` (xem `scripts/crime/ff.py`). Ghim `faster-whisper==1.1.1` + `av==13.1.0` (PyAV mới làm hỏng faster-whisper).
- Từ hay bị giọng đọc sai ghi vào `prompts/readings.json`.
- Phông: tiếng Nhật Noto Sans JP (đậm 900); tiếng Đức Anton (chữ vàng, tiêu đề) + Source Sans 3 (chữ nhỏ). `scripts/crime/get_fonts.sh` tự chọn theo `prompts/channel.json`.
