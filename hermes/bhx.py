"""Adapt the supplied BHX allocation reader to unapproved sales candidates."""
from collections import defaultdict
from datetime import date
from pathlib import Path
from .bhx_reader import read_allocations
from .model import validate


def candidates(path, sale_date):
    date.fromisoformat(sale_date)
    path = Path(path)
    if path.suffix.lower() != '.pdf' or path.stat().st_size > 25_000_000:
        raise ValueError('BHX adapter accepts one PDF up to 25 MB')
    stations, issues = read_allocations(path.read_bytes(), path.name)
    # Never import partial results when the source parser reports a failure.
    if issues or not stations:
        raise ValueError('BHX parse requires review: ' + '; '.join(issues))
    result = []
    for station in stations.values():
        groups = defaultdict(list)
        for item in station['rows']:
            groups[item['store']].append(item)
        for customer, items in groups.items():
            result.append(validate({'source_hash': station['source_hash'],
                'order_ref': f"BHX-{station['id']}-{customer}-{sale_date}",
                'customer': customer, 'sale_date': sale_date,
                'lines': [{'line_id': str(i), 'product': item['product'], 'unit': item['unit'],
                           'quantity': str(item['qty']), 'unit_price_vnd': None}
                          for i, item in enumerate(items, 1)]}))
    return {'status': 'unapproved_candidates', 'records': result}
