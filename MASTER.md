# Kiến trúc Hermes Master trên Windows

Master điều phối 5 worker Python cục bộ. Đây là các bộ xử lý xác định, chưa phải
5 mô hình AI tự vận hành. Không cần trả phí API để chạy thử.

| Worker | Hiện có | Cần để vận hành thật |
|---|---|---|
| 01 Bán hàng | Đọc Excel/PDF, nháp, phân luồng, chốt giá | Quy tắc khách hàng |
| 02 Biên nhận | Dữ liệu biên nhận nháp theo phiên bản | Mẫu, cách đánh số, quy tắc phát hành |
| 03 Kiểm soát | Thiếu giá, thiếu luồng, duyệt, trùng | Quy tắc kiểm soát nghiệp vụ |
| 04 Công nợ | Tổng đơn, trạng thái thiếu dữ liệu thanh toán | Số dư đầu kỳ, thanh toán, đối soát |
| 05 Báo cáo | Tổng bản nháp hiện tại, đơn đã duyệt/chờ giá | Kỳ báo cáo và mẫu báo cáo |

```powershell
hermes demo
hermes --db data/hermes.sqlite master --out data/master-review.json
```

Master chỉ đọc bản nháp và xuất báo cáo. Không tự duyệt, phát hành biên nhận,
ghi nhận thanh toán hay gửi tin. Công nợ chưa đủ dữ liệu trả null, không suy ra
khách chưa trả tiền. Tổng bản nháp không được coi là doanh thu kế toán.

`examples/master-config.json` ghi thiết kế dự kiến 07:00 giờ Việt Nam và tắt
gửi tin. File này là mẫu thiết kế, chưa có scheduler đọc nó. Chưa đăng ký tác vụ
Windows và chưa có bot Telegram đang chạy. Hàng đợi Telegram hỗ trợ PDF/XLSX,
kiểm tra secret, chat allowlist và chống trùng, chưa tải file từ Telegram.

Để đưa vào vận hành cần cấu hình bot token cục bộ, chat nhận, API/staging của
phần mềm hải sản, và quy tắc do chủ hệ thống cung cấp. Không đưa token vào chat
hay GitHub. GitHub chỉ chứa mã nguồn và phiên bản; không lưu số liệu khách hàng.

Thay đổi an toàn: mọi đơn thiếu routing, kể cả bản nháp cũ, phải chạy `route`
với quy tắc đã xác nhận trước khi duyệt. Hướng dẫn tương thích cũ trong ROUTING.md
được thay thế bởi yêu cầu này. Demo luôn dùng dữ liệu tổng hợp trong bộ nhớ.
