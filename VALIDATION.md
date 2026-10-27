# Kiểm chứng bản 0.1 — 2026-10-27

Môi trường đã chạy: Windows, Python 3.12.14; pypdf 6.10.0, pdfplumber 0.11.9, openpyxl 3.1.5.

`python -m unittest discover -s tests -v`: **11/11 PASS**.

- Chặn ghi mock trước duyệt; chặn hash cũ.
- Nhập lại cùng dữ liệu và gửi lại cùng revision không tạo bản ghi trùng.
- Chặn cùng mã nghiệp vụ khi SHA256 PDF khác nhau.
- Chốt giá tăng revision, hủy duyệt cũ; tổng demo chính xác 1.542.000 VND.
- Kết nối SQLite mới vẫn giữ trạng thái duyệt và chống trùng; thay đổi từ kết nối khác được phát hiện.
- Không đổi nội dung thì giữ revision; sửa dựa trên hash cũ bị chặn.
- Chặn số âm, không hữu hạn, số lượng 0 và định dạng số mơ hồ.
- Excel giữ nội dung giống công thức dưới dạng text; giá chờ và tổng cuối không bị gán 0.
- PDF không có văn bản chờ OCR; sidecar không tự trở thành giao dịch.
- Telegram chặn sai secret/chat; không cho cấu hình secret rỗng.
- Bộ đọc BHX chuyển bảng giả lập sang bản nháp chờ giá; lỗi bảng chặn nhập.

Smoke test CLI trong tiến trình con: **PASS** cho draft → export → approve → publish-mock → retry → settle → export → approve → publish-mock. Đã kiểm tra cả hai lần chặn ghi trước duyệt.

Đầu vào thực tế: bản cục bộ tương ứng Ban 24-10 có 6 trang không có lớp văn bản; intake trả cả 6 trang `needs_ocr`, không sinh sales_records. Đã xem ảnh trang đầu. Chưa chép hoặc xác minh toàn bộ số liệu viết tay. PDF văn bản tổng hợp riêng được đọc thành công.

Giới hạn kiểm chứng:

- Chưa có PDF biên bản BHX thực tế để kiểm tra đầu-cuối; adapter dùng test bảng giả lập và mã đọc lấy từ ZIP được cung cấp.
- Chưa chạy OCR Ollama, Telegram bot hoặc website thật; không có thông tin xác thực cần thiết và các phần này chưa được triển khai kết nối.
- Chưa kiểm tra cài đặt môi trường sạch qua Internet hoặc chạy GitHub Actions; bộ test chạy với thư viện có sẵn. CI được cung cấp cho Windows/Linux, Python 3.11/3.12, nhưng chưa có kết quả CI.
- GitHub không truy cập được qua proxy hiện tại; không có commit/push từ phiên này.
- Lần chạy test đầu gặp ACL của thư mục tạm Windows. Test đã dùng thư mục riêng với ACL kế thừa, sau đó chạy đạt toàn bộ; không phải bỏ qua kiểm thử SQLite.

ZIP chỉ chứa mã, ví dụ giả lập, tests, CI và tài liệu; không chứa PDF khách hàng, cơ sở dữ liệu, tài khoản từ ZIP BHX hay token.
