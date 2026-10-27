# Nguồn mã BHX

Nguồn do người dùng chỉ định: `dondathang-bhx-main (2).zip`.
SHA256 ZIP: `2be887d2e15304cd8b8102b098c2320bad8b15f77b207189b4df8050d7faab6e`.

`hermes/bhx_reader.py` lấy có chọn lọc bốn hàm `clean`, `number`, `pdf_members`, `read_allocations` từ `processing.py`. Bỏ nhánh tăng tốc tùy chọn để chỉ dùng pdfplumber và tránh import module ngoài gói. Các hàm còn lại của ứng dụng không được sao chép. Không sao chép cấu hình đăng nhập, danh sách tài khoản, lịch sử giao dịch hoặc mapping khách hàng.

ZIP không liệt kê file LICENSE. Không tự gán giấy phép cho mã có sẵn; chủ sở hữu xác định giấy phép trước khi phân phối công khai. Các dependency giữ giấy phép riêng của dự án tương ứng.
