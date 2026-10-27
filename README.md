# Thịnh Vượng Hermes Agent — bản khởi đầu 0.1

## Cập nhật Master thử nghiệm

Xem `MASTER.md` cho kiến trúc 5 worker, `EXCEL.md` cho nhập Excel và `ROUTING.md`
cho phân luồng. Chạy `hermes demo` để kiểm thử quy trình bằng dữ liệu tổng hợp.
Mọi bản nháp thiếu luồng đều bị chặn duyệt, kể cả ví dụ cũ bên dưới: cần đặt
quy tắc và dùng `route` trước khi approve. Quy tắc thật hiện để trống.
Thông tin phát hành GitHub trong phần cuối là ghi chép bản ban đầu; không dùng
nó để xác định bản mới nhất đã được tải lên hay chưa. Xem trạng thái bàn giao.

Agent xử lý bán hàng chạy cục bộ bằng Python, điều khiển qua dòng lệnh. Luồng: PDF → nội dung chờ kiểm tra → bản nháp có cấu trúc → Excel → người dùng duyệt → ghi website **giả lập**. Có ghi nhận hàng bán trước và chốt giá thị trường sau.

Đây là ứng dụng độc lập mang tên Hermes, chưa tích hợp với một framework Hermes bên ngoài. Không có lời gọi đến website thật, không cần OpenAI API key, không gửi dữ liệu lên dịch vụ AI.

## Cài đặt (Windows PowerShell, Python 3.11+)

Giải nén ZIP, mở PowerShell trong thư mục chứa `pyproject.toml`:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m hermes.cli --help
New-Item -ItemType Directory -Force data | Out-Null
```

Linux/macOS: dùng `python3 -m venv .venv`, sau đó `.venv/bin/python` thay đường dẫn Python Windows. Lần cài đầu cần Internet để lấy thư viện; chạy ứng dụng sau đó không cần mạng. Không tự đọc `.env` trong phiên bản này.

## Chạy thử và duyệt

Ví dụ dùng dữ liệu **DEMO**, không phải số liệu đã chép từ sổ bán hàng. Chạy từng bước và kiểm tra kết quả trước bước duyệt:

```powershell
$python = '.\.venv\Scripts\python.exe'
$draft = (& $python -m hermes.cli draft examples/order.json | ConvertFrom-Json)
$orderId = $draft.id
& $python -m hermes.cli show $orderId
& $python -m hermes.cli export $orderId --out data/review-v1.xlsx
```

Mở Excel, đối chiếu khách hàng, ngày, mặt hàng, đơn vị, số lượng và giá với PDF. Giá chưa chốt là `PENDING`, tổng cuối cùng để trống. Không tự hiểu giá `130` trong sổ là `130000`: phải xác nhận thang giá. `unit_price_vnd` luôn là VND trên đơn vị; số dùng dấu chấm thập phân, không dấu phân cách hàng nghìn.

Nếu sai, sửa JSON bản nháp rồi chạy `revise <id> <json> --hash <hash hiện tại>`. JSON đưa vào `revise` là phần `record` của kết quả `show`, không phải toàn bộ envelope. Không sửa file Excel để cập nhật hệ thống: bản này chưa có chức năng nhập ngược Excel. Các trường định danh không đổi được sau khi tạo; dùng mã đơn và khách hàng ổn định ngay từ đầu.

Chỉ sau khi đã kiểm tra Excel và JSON tương ứng, chạy rõ ràng:

```powershell
& $python -m hermes.cli approve $orderId --hash $draft.hash --by 'Chu-cua-hang'
& $python -m hermes.cli publish-mock $orderId
```

Lệnh cuối chỉ ghi bảng `mock_writes` trong `data/hermes.sqlite`, mô phỏng upsert đơn hàng trên haisanthinhvuong.com. Gọi lại cùng phiên bản trả `inserted: false`. Có thể duyệt đơn chưa chốt giá để ghi nhận lượng hàng; hệ thống luôn giữ `final_total_vnd = null` khi còn dòng chờ giá.

## Chốt giá sau

```powershell
$current = (& $python -m hermes.cli show $orderId | ConvertFrom-Json)
& $python -m hermes.cli settle $orderId examples/prices.json --hash $current.hash
$updated = (& $python -m hermes.cli show $orderId | ConvertFrom-Json)
& $python -m hermes.cli export $orderId --out data/review-v2.xlsx
```

`prices.json` ánh xạ `line_id` tới giá và căn cứ giá (ngày, nguồn, người xác nhận). Có thể chốt một phần. Mỗi thay đổi tăng revision và hủy duyệt cũ; xem lại Excel rồi mới:

```powershell
& $python -m hermes.cli approve $orderId --hash $updated.hash --by 'Chu-cua-hang'
& $python -m hermes.cli publish-mock $orderId
```

Mock lưu lịch sử snapshot theo `order_id:revision`; hệ thống đọc báo cáo phải lấy revision mới nhất theo order_id, **không cộng dồn** các snapshot. Ví dụ hoàn tất có tổng 1.542.000 VND. Không tự tra hoặc áp giá thị trường khi chưa có nguồn giá được xác nhận.

## PDF và chữ viết tay

```powershell
& $python -m hermes.cli intake 'C:\duong-dan\Ban 24-10.pdf' --out data/intake.json
# Có bản chép tay hoặc OCR bên ngoài, dạng {"1": "nội dung trang 1", "2": "..."}:
& $python -m hermes.cli intake 'C:\duong-dan\Ban 24-10.pdf' --ocr-pages examples/ocr-pages.json --out data/intake-with-text.json
```

PDF tối đa 25 MB/100 trang. Trang không có văn bản thành `needs_ocr`. OCR luôn là `ocr_unverified`; không có OCR tự động trong bản này. Bản PDF cục bộ tương ứng mẫu Ban 24-10 đã được kiểm tra: 6 trang, không có lớp văn bản; trang đầu là ảnh sổ viết tay. Do chưa xác minh toàn bộ nội dung, không tạo giao dịch thật từ mẫu.

Sau khi đối chiếu từng trang, tạo JSON theo `examples/order.json`, thay `source_hash` bằng SHA256 do intake trả về. Một PDF có thể chứa nhiều đơn: mỗi đơn phải có `order_ref` riêng, ổn định. Lưu số trang gốc trong quy ước `order_ref` nếu cần (ví dụ `BAN-20261024-P1-01`). Chưa có bộ phân tích tự động cấu trúc sổ viết tay.

Để nối Ollama sau: triển khai `OCRProvider.recognize(pdf_bytes, page_number)` trong module riêng, render đúng trang rồi gọi mô hình vision cục bộ. Truyền đối tượng đó vào `intake(path, ocr=provider)`. Không cho mô hình gọi `approve`/`publish_mock`. Cần bổ sung timeout, giới hạn ảnh và kiểm thử trên tập ảnh có đáp án trước khi sử dụng thực tế. `OLLAMA_BASE_URL` trong `.env.example` chỉ là gợi ý cho adapter tương lai, chưa được đọc bởi chương trình.

## Tận dụng bộ mã BHX

Đã tái sử dụng có chọn lọc các hàm đọc biên bản chia hàng từ `processing.py` của ZIP BHX. Adapter chuyển bảng kho/cửa hàng thành các đơn chưa duyệt, không tự quy đổi đơn vị hoặc suy ra giá.

```powershell
& $python -m hermes.cli bhx 'C:\duong-dan\bien-ban-chia-hang.pdf' --date 2026-10-24 --out data/bhx-candidates.json
```

Kiểm tra danh sách `records`, lưu mỗi record thành một JSON riêng rồi chạy `draft`. Adapter chỉ hỗ trợ **biên bản chia hàng BHX**, không phải mọi mẫu PO/hóa đơn. Khi bất kỳ trang nào không đọc được, toàn bộ lần nhập bị chặn. Bộ tăng tốc PDF cũ không được đóng gói; dùng pdfplumber. Chưa có PDF BHX thực tế trong gói đầu vào để kiểm thử adapter đầu-cuối; test hiện dùng bảng giả lập. Xem `THIRD_PARTY.md`.

## Ranh giới duyệt, chống trùng và lưu trữ

- `intake`, `draft`, `revise`, `export` ghi file nháp/Excel/cơ sở dữ liệu cục bộ theo lệnh người dùng. Bước duyệt bắt buộc áp dụng cho **ghi nghiệp vụ vào connector**, không áp dụng cho file dùng để kiểm tra. Nếu yêu cầu không ghi bất kỳ byte nào trước duyệt thì phải dùng một giao diện trong bộ nhớ khác.
- SHA256 bản ghi chuẩn hóa gắn nội dung duyệt; sửa nội dung làm mất duyệt. `BEGIN IMMEDIATE` khóa việc cập nhật và ghi mock trong cùng giao dịch. Nhật ký audit lưu hành động, người duyệt, revision, thời gian UTC và hash.
- Khóa trùng: SHA256 PDF + order_ref; thêm khách hàng + ngày + order_ref để chặn cùng đơn từ PDF đóng gói lại. Không dùng so khớp gần đúng; đổi đồng thời tất cả mã định danh có thể vượt phát hiện trùng. Dùng mã khách và mã đơn nhất quán.
- Người có quyền sửa SQLite có thể thay dữ liệu; đây là CLI cho một người vận hành tin cậy, không phải hệ thống phân quyền nhiều người. `--by` là nhãn nhật ký, không phải xác thực danh tính. Không mở CLI thành API công khai.
- Tiền tính bằng Decimal, tổng làm tròn HALF_UP đến VND. Excel chứa số phục vụ xem xét; tổng chuẩn do Python tính. Giá chờ không biến thành 0. Sao lưu `data/` khi ứng dụng đã đóng.

## Telegram và website

`hermes/telegram.py` là scaffold thuần túy: kiểm tra webhook secret, allowlist chat riêng, update_id, loại PDF và kích thước. Không có bot đang chạy, không gửi tin nhắn và không tải tệp. Để triển khai cần webhook HTTPS hoặc polling, bot token lưu cục bộ, nhận header `X-Telegram-Bot-Api-Secret-Token`, lưu chống trùng update_id, tải file bằng API Telegram, xác minh magic bytes và chuyển sang intake. Không log URL chứa token. Không ánh xạ tin nhắn thành shell command và không cho Telegram tự duyệt.

Connector website chỉ có mock, không có công tắc bật production. Kết nối thật cần hợp đồng API, staging, xác thực, khóa idempotency phía server, upsert theo order_id/revision, xử lý retry và kiểm tra quyền duyệt phía server. Chưa thay đổi website haisanthinhvuong.com.

## Đưa lên GitHub

Trong lần tạo này không có GitHub connector; `git ls-remote` thất bại do proxy cục bộ không kết nối được. Chưa kiểm chứng trạng thái kho từ xa và chưa commit/push. Không có thông tin xác thực nào được đưa vào ZIP.

Khi mạng GitHub hoạt động và tài khoản có quyền ghi (Git Credential Manager/SSH hoặc GitHub plugin được kết nối), clone kho để giữ lịch sử hiện có:

```powershell
git clone https://github.com/luuthaohoa-bot/thinh-vuong-hermes-agent.git
cd thinh-vuong-hermes-agent
git switch -c feat/hermes-initial
# Chép nội dung gói này vào clone, kiểm tra các file trùng trước khi ghi đè.
git status --short
git add pyproject.toml .gitignore .env.example README.md THIRD_PARTY.md VALIDATION.md hermes tests examples .github
git diff --cached --stat
git commit -m "Add review-first Hermes sales workflow"
git push -u origin feat/hermes-initial
```

Không force-push. Không đưa PDF khách hàng, SQLite, `.env` thật hay ZIP BHX nguyên bản lên kho. Nếu dùng kho riêng tư, tài khoản Git phải có quyền truy cập kho; không dán token vào chat. GitHub Actions chạy bộ test trên Windows và Linux sau khi push.
