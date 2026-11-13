# Định dạng phiếu video vụ án (cho ChatGPT hoặc người tạo phiếu bằng tay)

Repo: `maihaianh2911-bit/japan-crime-video-factory`. Mỗi video = **một Issue mới** do tài khoản `maihaianh2911-bit` tạo (phiếu của tài khoản khác không chạy). Không gắn nhãn, không đẩy file: Claude chia lời (dịch sang tiếng Nhật nếu kịch bản là tiếng Việt), tìm ảnh thật, tạo ảnh minh họa khi thiếu, máy tạo giọng và dựng.

- **Tiêu đề:** `[Vụ án] <tên vụ án bằng tiếng Nhật> — <ý chính>`. Phải bắt đầu đúng bằng `[Vụ án]`.
- **Nội dung** (giữ nguyên tên mục):
```
### Vụ án (không bắt buộc)

<tên vụ án, nơi xảy ra, năm>

### Kịch bản (bắt buộc)

<kịch bản tiếng Việt hoặc tiếng Nhật, mỗi câu một ý>

### Giọng đọc

clone_190 (mặc định)

### Ghi chú (không bắt buộc)

<độ dài mong muốn, ảnh nên có / nên tránh; không có thì để _No response_>
```
- Độ dài: 60–120 giây là hợp nhất (video mẫu 95 giây); tối đa ~3 phút.
- Viết mỗi câu một ý cụ thể (một nơi, một người, một việc, một ngày), vì mỗi câu sẽ có một bức ảnh đi kèm.
- Chuyện chưa được tòa xác nhận thì viết là "bị cáo buộc", "theo lời khai…".
- Muốn sửa video: viết **một bình luận** gom hết yêu cầu vào phiếu (không bắt đầu bằng 🤖).
