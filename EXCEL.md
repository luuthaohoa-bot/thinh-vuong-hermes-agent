# Nhập sổ bán hàng Excel

Hỗ trợ `.xlsx`, trang `Sổ bán hàng`, các cột như mẫu: STT, Ngày, Khách hàng,
Tên hàng, ĐVT, Số kg, Đơn giá (đ/kg), Thành tiền (đ), Trang.
Ngày dùng ô ngày Excel hoặc chuỗi ISO YYYY-MM-DD. Giá dùng VND/kg đầy đủ.

```powershell
hermes excel "so-ban-hang.xlsx" --ledger-id so-ban-hang --out review.json
hermes draft review.json --record excel-MA_ORDER_REF_TRONG_REPORT
hermes show ID_BAN_NHAP
hermes export ID_BAN_NHAP --out review-order.xlsx
hermes approve ID_BAN_NHAP --hash HASH_HIEN_TAI --by "Nguoi duyet"
hermes publish-mock ID_BAN_NHAP
```

`excel` chỉ tạo báo cáo cục bộ, không tạo đơn trong database và không gọi website.
`draft --record` chọn từng nhóm đơn sau khi người dùng kiểm tra. Quy trình approve
vẫn bắt buộc trước publish-mock. Mock chỉ ghi SQLite, không ghi website thật.

Giữ nguyên `ledger-id` khi nhập lại hoặc sửa cùng sổ. Mã đơn dựa trên mã sổ,
ngày và tên khách; lưu lại hoặc đổi tên file không tạo mã đơn mới. Nếu đã có đơn,
thay đổi cần dùng revise và duyệt lại. Đổi tên khách hoặc mã sổ làm đổi khóa:
phải đối chiếu đơn cũ trước khi tạo, không dùng để né kiểm tra trùng.

Dòng thiếu kg hoặc lỗi dữ liệu chặn cả nhóm khách/ngày để không nhập thiếu hàng.
Dòng thiếu giá giữ `pending_market`, dùng settle sau khi có giá; settle yêu cầu
duyệt lại. STT trùng bị chặn; nhiều dòng cùng mặt hàng nhưng STT khác được giữ.
Không tự đồng nhất tên khách. `name_review` nêu các tên không khớp bảng tổng.

Không chạy công thức Excel. Công thức trong ô đầu vào bị chặn; cột thành tiền
được tính lại từ kg × giá, không dùng cached value. Công thức tổng tùy biến
(chiết khấu/phí) chưa được hỗ trợ. Số tiền nhập tay lệch phép nhân bị chặn.
Báo cáo giữ số dòng, STT, trang gốc và dữ liệu thiếu để truy vết.

Không commit file khách hàng, review.json hoặc database lên GitHub.
Kiểm thử: `python -m unittest discover -s tests -v` (17 tests).
