import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def amount(value, positive=False):
    try:
        n = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("Use decimal numbers with '.' and no thousands separators") from None
    if not n.is_finite() or n < 0 or (positive and n == 0) or n > Decimal('1000000000000'):
        raise ValueError("Number outside permitted range")
    return format(n.normalize(), 'f')


def required(value, label):
    if not isinstance(value, str) or not value.strip() or len(value) > 500:
        raise ValueError(f"Invalid {label}")
    return value.strip()


def validate(record):
    """Canonicalize a complete manually reviewed sales draft; prices are VND/unit."""
    result = {k: required(record.get(k), k) for k in
              ('order_ref', 'customer', 'sale_date', 'source_hash')}
    date.fromisoformat(result['sale_date'])
    if len(result['source_hash']) != 64 or any(c not in '0123456789abcdef' for c in result['source_hash']):
        raise ValueError('Invalid source SHA256')
    lines = record.get('lines')
    if not isinstance(lines, list) or not 1 <= len(lines) <= 1000:
        raise ValueError('Require 1..1000 sale lines')
    result['lines'] = []
    ids = set()
    for line in lines:
        item = {k: required(line.get(k), k) for k in ('line_id', 'product', 'unit')}
        if item['line_id'] in ids:
            raise ValueError('Duplicate line_id')
        ids.add(item['line_id'])
        item['quantity'] = amount(line.get('quantity'), positive=True)
        price = line.get('unit_price_vnd')
        item['unit_price_vnd'] = None if price is None else amount(price)
        item['price_basis'] = required(line.get('price_basis'), 'price_basis') if price is not None else 'pending_market'
        result['lines'].append(item)
    return result


def totals(record):
    known = sum((Decimal(x['quantity']) * Decimal(x['unit_price_vnd'])
                 for x in record['lines'] if x['unit_price_vnd'] is not None), Decimal(0))
    pending = any(x['unit_price_vnd'] is None for x in record['lines'])
    return {'known_total_vnd': str(known.quantize(Decimal('1'), rounding=ROUND_HALF_UP)),
            'final_total_vnd': None if pending else str(known.quantize(Decimal('1'), rounding=ROUND_HALF_UP)),
            'price_status': 'pending_market' if pending else 'settled'}
