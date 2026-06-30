# Wealth VN — Hướng dẫn chạy phần mềm quản lý tài sản

Đây là phần mềm quản lý tài sản đầu tư tại Việt Nam (cổ phiếu, vàng, ngoại tệ, thu nhập...). Tài liệu này dành cho người không chuyên về kỹ thuật, chỉ cần biết cách dùng máy tính cơ bản.

---

## Yêu cầu trước khi chạy

Bạn cần một máy tính Windows và kết nối Internet.

Phần mềm sẽ tự động cài đặt các thành phần cần thiết (Python, Node.js) nếu máy chưa có. Bạn không cần tự cài.

> **Lưu ý:** Lần chạy đầu tiên có thể mất vài phút để tải và cài đặt.

---

## Cách chạy phần mềm

### Bước 1: Mở thư mục phần mềm

Sau khi tải hoặc nhận được thư mục `FinProj`, mở thư mục đó trong File Explorer.

### Bước 2: Chạy file khởi động

Tìm file tên:

```
start.bat
```

Nhấp đúp chuột vào `start.bat`. Cửa sổ đen (PowerShell) sẽ hiện ra.

Nếu Windows hỏi **"Run anyway?"** hoặc cảnh báo về quyền, hãy chọn **Run anyway / More info → Run anyway**.

Nếu được hỏi quyền Administrator, hãy chọn **Yes** để phần mềm có thể tự cài đặt Python/Node.js nếu cần.

### Bước 3: Đợi khởi động

Cửa sổ sẽ hiển thị các dòng thông báo như:

- `WEALTH VN`
- `Khởi động backend...`
- `Khởi động frontend...`

Khi thấy dòng:

```
[>>] Ứng dụng đang chạy
Backend : http://localhost:8000
Frontend: http://localhost:5173
```

trình duyệt web sẽ tự mở ra. Nếu không, bạn có thể tự mở trình duyệt và vào địa chỉ hiển thị (thường là `http://localhost:5173`).

### Bước 4: Sử dụng phần mềm

Giao diện phần mềm hiện ra trong trình duyệt. Bạn có thể:

- Thêm tài sản đầu tư (cổ phiếu, vàng, ngoại tệ...)
- Ghi thu nhập / chi tiêu
- Theo dõi giá trị danh mục đầu tư
- Xem biểu đồ, phân tích, lịch sử giao dịch
- Nhập / xuất dữ liệu

---

## Cách tắt phần mềm

Khi đang sử dụng xong, quay lại cửa sổ đen đang chạy và nhấn **phím bất kỳ**. Phần mềm sẽ tự động tắt cả backend và frontend.

> **Không nên đóng cửa sổ bằng nút X** vì có thể để lại các chương trình chạy ngầm. Nên nhấn phím bất kỳ theo hướng dẫn trên màn hình.

---

## Nếu gặp lỗi

| Hiện tượng | Cách xử lý |
|-----------|------------|
| Máy báo thiếu Python / Node.js | Chạy lại `start.bat` bằng quyền Administrator (nhấp phải → Run as administrator). |
| Trình duyệt không tự mở | Mở trình duyệt, vào `http://localhost:5173` (hoặc số cổng hiện trên màn hình). |
| Màn hình đen biến mất ngay | Nhấp phải `start.bat` → Run as administrator, hoặc kiểm tra kết nối Internet. |
| Trang web trắng / không tải được | Đợi thêm 30 giây rồi refresh trang (F5). |
| Lỗi tiếng Việt không hiển thị đúng | Đảm bảo Windows đã bật UTF-8 (thường là mặc định trên Windows 10/11). |

Nếu vẫn không được, hãy chụp ảnh màn hình lỗi và gửi cho người hỗ trợ kỹ thuật.

---

## Dữ liệu của bạn lưu ở đâu

Tất cả dữ liệu được lưu trong file cơ sở dữ liệu SQLite tại:

```
backend/data/wealth.db
```

File này chứa tài sản, giao dịch, thu nhập và cài đặt của bạn. Nên sao lưu thư mục `backend/data/` định kỳ để tránh mất dữ liệu.

---

## Gắn nhãn chủ đề tự động (tùy chọn)

Phần mềm có thể tự động gắn nhãn chủ đề (tags) cho từng tin tức bằng một AI cục bộ nhỏ chạy trên máy của bạn, không gửi dữ liệu ra ngoài.

### Yêu cầu

- Cài đặt Ollama từ https://ollama.com (tương tự cài một phần mềm bình thường).
- Máy cần thêm khoảng 2 GB RAM để chạy mô hình nhỏ.

### Bật tính năng

1. Mở ứng dụng Ollama, chạy lệnh sau một lần duy nhất để tải mô hình tiếng Việt nhẹ:

```bash
ollama pull qwen2.5:1.5b
```

2. Tạo file `backend/.env` với nội dung:

```env
OLLAMA_ENABLED=true
OLLAMA_MODEL=qwen2.5:1.5b
```

3. Chạy lại `start.bat`. Các tin tức mới từ nay sẽ có tags như "cổ phiếu", "ngân hàng", "lãi suất"...

Nếu không bật Ollama, phần mềm vẫn tự gắn nhãn cơ bản bằng từ khóa, không cần thêm gì.

## Cập nhật phần mềm

Khi có phiên bản mới, chỉ cần thay thế toàn bộ thư mục `FinProj` bằng thư mục mới. Nhưng **trước khi thay**, hãy copy thư mục `backend/data/` sang nơi an toàn, sau đó chép lại vào đúng vị trí cũ để giữ dữ liệu.

---

## Cấu trúc đơn giản

- `start.bat` — Nút khởi động chính.
- `frontend/` — Giao diện người dùng (chạy trong trình duyệt).
- `backend/` — Máy chủ xử lý dữ liệu và kết nối thị trường.
- `backend/data/` — Nơi lưu trữ dữ liệu của bạn.

Bạn không cần sửa gì trong các thư mục này để sử dụng phần mềm hàng ngày.

---

## Liên hệ hỗ trợ

Nếu cần trợ giúp, vui lòng gửi ảnh chụp màn hình lỗi và mô tả chi tiết các bước bạn đã làm.


