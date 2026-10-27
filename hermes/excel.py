"""Read daily Vietnamese sales ledgers; never evaluate spreadsheet formulas."""
import hashlib
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from openpyxl import load_workbook
from .model import amount, digest, required, validate

HEADERS = ['STT', 'Ngày', 'Khách hàng', 'Tên hàng', 'ĐVT', 'Số kg',
           'Đơn giá (đ/kg)', 'Thành tiền (đ)', 'Trang']


def candidates(path, ledger_id):
    ledger_id = required(ledger_id, 'ledger_id')
    path = Path(path)
    source_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    wb = load_workbook(path, read_only=True, data_only=False, keep_links=False)
    try:
        ws = wb['Sổ bán hàng']
        if ws.max_row > 10000 or ws.max_column > 100:
            raise ValueError('Ledger exceeds supported bounds')
        header = None
        for cells in ws.iter_rows(max_row=min(30, ws.max_row)):
            values = [c.value for c in cells]
            if all(values.count(h) == 1 for h in HEADERS):
                header = cells[0].row
                columns = {h: values.index(h) for h in HEADERS}
                break
        if header is None:
            raise ValueError('Required sales ledger headers not found')
        rows = []
        for cells in ws.iter_rows(min_row=header + 1):
            raw = {h: cells[i].value for h, i in columns.items()}
            if all(v is None for v in raw.values()):
                continue
            if raw['STT'] is None and raw['ĐVT'] == 'TỔNG ĐÃ ĐỌC':
                continue
            row = {'row': cells[0].row, 'raw': raw, 'errors': [], 'warnings': []}
            for key, val in list(raw.items()):
                if isinstance(val, (date, datetime)):
                    raw[key] = val.date().isoformat() if isinstance(val, datetime) else val.isoformat()
            try:
                if any(cells[columns[h]].data_type == 'f' for h in HEADERS if h != 'Thành tiền (đ)'):
                    raise ValueError('Formula in an input cell; replace with verified value')
                stt = raw['STT']
                if isinstance(stt, bool) or not isinstance(stt, int) or stt <= 0:
                    raise ValueError('STT must be a positive integer')
                customer = required(raw['Khách hàng'], 'customer')
                day = date.fromisoformat(raw['Ngày']).isoformat()
                row['key'] = (customer, day)
                line = {'line_id': str(stt), 'product': required(raw['Tên hàng'], 'product'),
                        'unit': required(raw['ĐVT'], 'unit')}
                if raw['Số kg'] is None:
                    row['errors'].append('Missing quantity')
                else:
                    line['quantity'] = amount(raw['Số kg'], positive=True)
                price = raw['Đơn giá (đ/kg)']
                line['unit_price_vnd'] = None if price is None else amount(price)
                line['price_basis'] = 'pending_market' if price is None else 'Excel ledger; requires review'
                if price is None:
                    row['warnings'].append('Missing price: pending_market')
                if 'quantity' in line and price is not None:
                    row['computed_vnd'] = str(Decimal(line['quantity']) * Decimal(line['unit_price_vnd']))
                total = raw['Thành tiền (đ)']
                if cells[columns['Thành tiền (đ)']].data_type == 'f':
                    # Cached formula results are deliberately never used.
                    row['warnings'].append('Amount recomputed from quantity and price; formula not evaluated')
                elif total is not None:
                    if 'computed_vnd' not in row or Decimal(amount(total)) != Decimal(row['computed_vnd']):
                        row['errors'].append('Entered amount does not match quantity × price')
                row['line'] = line
            except (ValueError, TypeError) as exc:
                row['errors'].append(str(exc))
            rows.append(row)
        if not rows:
            raise ValueError('No sales rows found')
        counts = Counter(str(r['raw']['STT']) for r in rows)
        for row in rows:
            if counts[str(row['raw']['STT'])] > 1:
                row['errors'].append('Duplicate STT')
        groups = defaultdict(list)
        for row in rows:
            if 'key' in row:
                groups[row['key']].append(row)
        # An unassignable row may belong to any order: block all candidates.
        unassigned = any('key' not in r for r in rows)
        records, blocked = [], []
        for (customer, day), members in groups.items():
            if unassigned or any(r['errors'] for r in members):
                blocked.append({'customer': customer, 'sale_date': day, 'rows': [r['row'] for r in members]})
                continue
            records.append(validate({'customer': customer, 'sale_date': day, 'source_hash': source_hash,
                'order_ref': 'excel-' + digest([ledger_id, day, customer.casefold()])[:24],
                'lines': [r['line'] for r in members]}))
        detail_names = set(k[0] for k in groups)
        folded = Counter(name.casefold() for name in detail_names)
        collisions = {name for name in detail_names if folded[name.casefold()] > 1}
        if collisions:
            for record in records[:]:
                if record['customer'] in collisions:
                    records.remove(record)
                    blocked.append({'customer': record['customer'], 'sale_date': record['sale_date'],
                                    'reason': 'Customer names collide ignoring case; review spelling'})
        summary_names = set()
        if 'Tổng theo khách' in wb.sheetnames:
            summary = wb['Tổng theo khách']
            if summary.max_row > 10000:
                raise ValueError('Summary exceeds supported bounds')
            for values in summary.iter_rows(values_only=True):
                if len(values) >= 2 and isinstance(values[0], int) and isinstance(values[1], str):
                    summary_names.add(values[1].strip())
        return {'status': 'unapproved_candidates', 'source_hash': source_hash, 'ledger_id': ledger_id,
                'summary': {'rows': len(rows), 'customers': len(detail_names),
                            'missing_quantity': sum(r['raw']['Số kg'] is None for r in rows),
                            'missing_price': sum(r['raw']['Đơn giá (đ/kg)'] is None for r in rows),
                            'known_total_vnd': str(sum((Decimal(r['computed_vnd']) for r in rows
                                                       if 'computed_vnd' in r and not r['errors']), Decimal(0))),
                            'candidate_orders': len(records), 'blocked_orders': len(blocked)},
                'name_review': {'only_in_detail': sorted(detail_names - summary_names),
                                'case_collisions': sorted(collisions),
                                'only_in_summary': sorted(summary_names - detail_names)},
                'rows': rows, 'records': records, 'blocked_orders': blocked}
    finally:
        wb.close()
