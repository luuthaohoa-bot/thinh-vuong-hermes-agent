"""Selected BHX reader functions from user-supplied processing.py.
See THIRD_PARTY.md for provenance. No authentication/configuration files copied.
"""
import re
import math
import zipfile
import io
import hashlib
import pdfplumber

def clean(value):

    return re.sub(r"\s+", " ", "" if value is None else str(value)).strip()

def number(value):

    text = clean(value)

    if not text:

        return None

    # BHX exports use decimal points and commas as thousands separators.

    result = float(text.replace(",", ""))

    if not math.isfinite(result) or result < 0:

        raise ValueError("Số lượng phải là số không âm.")

    # Numeric editors can submit 96.99999999999999 for an intended 97.

    if abs(result - round(result)) <= 1e-10:

        result = float(round(result))

    return result

def pdf_members(data, name):

    if name.lower().endswith(".pdf"):

        return [(name, data)]

    if not name.lower().endswith(".zip"):

        raise ValueError("Chọn PDF hoặc ZIP chứa PDF.")

    with zipfile.ZipFile(io.BytesIO(data)) as archive:

        members = [m for m in archive.infolist() if m.filename.lower().endswith(".pdf")]

        if not members:

            raise ValueError("ZIP không chứa PDF.")

        if len(members) > 500 or sum(m.file_size for m in members) > 300_000_000:

            raise ValueError("ZIP quá lớn (tối đa 500 PDF, 300 MB giải nén).")

        return [(m.filename, archive.read(m)) for m in members]

def read_allocations(data, name):

    stations, issues, seen = {}, [], set()

    for filename, raw in pdf_members(data, name):

        digest = hashlib.sha256(raw).hexdigest()

        if digest in seen:

            issues.append(f"{filename}: PDF trùng nội dung, đã bỏ qua.")

            continue

        seen.add(digest)

        try:

            with pdfplumber.open(io.BytesIO(raw)) as pdf:

                header = clean(pdf.pages[0].extract_text())

                match = re.search(r"Mã\s*-\s*Tên kho:\s*(\d+)\s*-\s*BHX_([A-Z0-9]+_[A-Z0-9]+)\s*-\s*(.*?)(?=\s+\d+\s*-\s*CÔNG TY|\s+Nhà cung cấp:)", header)

                if not match or "BIÊN BẢN CHIA HÀNG" not in header:

                    raise ValueError("Không phải biên bản chia hàng có mã kho hợp lệ.")

                sid, code, point = match.groups()

                if sid in stations:

                    raise ValueError(f"Mã kho {sid} xuất hiện ở nhiều PDF khác nhau. Chỉ tải một biên bản cho mỗi kho trong một đợt.")

                rows = []

                for page_index, page in enumerate(pdf.pages, 1):

                    found_table = False

                    for table in page.extract_tables():

                        for cells in table:

                            if len(cells) != 7 or not clean(cells[0]).isdigit():

                                continue

                            if "BHX_" not in clean(cells[1]):

                                continue

                            found_table = True

                            qty = number(cells[5])

                            if qty is None or qty == 0:

                                continue

                            product, unit = clean(cells[4]).upper(), clean(cells[6])

                            if not product or not unit:

                                raise ValueError(f"Trang {page_index}: thiếu tên hàng hoặc đơn vị.")

                            rows.append({"store": clean(cells[1]), "label": clean(cells[0]).zfill(3),

                                         "product": product, "qty": qty, "unit": unit,

                                         "order": int(clean(cells[3]))})

                    if not found_table:

                        raise ValueError(f"Trang {page_index}: không đọc được bảng chia hàng.")

                    page.close()

                if not rows:

                    raise ValueError("Không có mặt hàng có số lượng.")

                rows.sort(key=lambda r: (int(r["label"]), r["store"], r["order"]))

                stations[sid] = {"id": sid, "code": code, "point": clean(point), "rows": rows,

                                 "source": filename, "source_hash": digest}

        except Exception as exc:

            issues.append(f"{filename}: {exc}")

    return stations, issues

