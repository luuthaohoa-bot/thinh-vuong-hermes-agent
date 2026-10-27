# Phân luồng khách hàng — khung thử nghiệm

File Excel đã nhận chỉ là mẫu thử. Không dùng khách hàng hoặc dữ liệu mẫu làm
quy tắc chính thức. `examples/routes.json` để trống cho đến khi chủ hệ thống
cung cấp quy tắc. Hiện đây là một chương trình Hermes có các bước xử lý,
chưa phải nhiều agent độc lập chạy tự động.

```powershell
hermes excel sample.xlsx --ledger-id test-ledger --routes examples/routes.json --out test-review.json
hermes draft test-review.json --record ORDER_REF
hermes route ORDER_ID --rules my-routes.json --hash CURRENT_HASH
```

Cấu trúc cấu hình: `{"rules": [{"customer": "Tên khách", "destination": "Tên luồng"}]}`.
Đây chỉ mô tả định dạng, không phải quy tắc nghiệp vụ đã được chấp thuận.
Tên được so khớp có dấu, không phân biệt hoa thường, bỏ khoảng trắng đầu/cuối.
Không đoán tên gần giống. Trùng quy tắc bị từ chối.

Nhập Excel qua CLI luôn thêm trạng thái phân luồng. Chưa có quy tắc phù hợp
thì giữ `pending` và chặn duyệt/ghi mock. Đổi luồng của bản nháp làm mất hiệu lực
duyệt cũ. Sửa file quy tắc không tự thay đổi đơn đã lưu: chạy `route` cho từng
đơn cần cập nhật rồi duyệt lại. Trường phân luồng là nhãn, không phải URL hay
lệnh thực thi; không tự gửi dữ liệu ra ngoài.

Tương thích: bản nháp cũ không có trường routing vẫn dùng quy trình duyệt cũ.
Muốn áp dụng phân luồng cho chúng, dùng lệnh `route` trước khi duyệt.

Kiểm thử cục bộ: 19 tests đạt, bao gồm chờ quy tắc, trùng quy tắc, không ghép
tên gần giống, đổi luồng phải duyệt lại và payload mock giữ đúng luồng.
