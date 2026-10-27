"""A deterministic synthetic acceptance run. Never connects to production."""
from .model import digest
from .routing import route
from .store import Store


def run():
    store = Store(':memory:')
    checks = []
    def blocked(call, label):
        try:
            call()
        except ValueError:
            checks.append(label)
        else:
            raise AssertionError(label)
    try:
        record = {'order_ref': 'DEMO-001', 'customer': 'DEMO CUSTOMER',
                  'sale_date': '2026-01-01', 'source_hash': digest('synthetic data'),
                  'lines': [{'line_id': '1', 'product': 'DEMO FISH', 'unit': 'kg',
                             'quantity': '8.4', 'unit_price_vnd': None}]}
        record['routing'] = route(record['customer'], {'rules': []})
        row = store.create(record)
        blocked(lambda: store.approve(row['id'], row['hash'], 'demo'), 'unknown_route_blocks_approval')
        record['routing'] = route(record['customer'], {'rules': [
            {'customer': 'DEMO CUSTOMER', 'destination': 'DEMO ONLY'}]})
        row = store.revise(row['id'], record, row['hash'])
        blocked(lambda: store.publish_mock(row['id']), 'unapproved_write_blocked')
        store.approve(row['id'], row['hash'], 'demo')
        assert store.publish_mock(row['id'])['inserted']
        assert not store.publish_mock(row['id'])['inserted']
        checks.append('duplicate_publish_prevented')
        assert row['totals']['final_total_vnd'] is None
        checks.append('missing_price_kept_pending')
        record['lines'][0].update(unit_price_vnd='130000', price_basis='Synthetic test price')
        row = store.revise(row['id'], record, row['hash'])
        blocked(lambda: store.publish_mock(row['id']), 'settlement_requires_reapproval')
        store.approve(row['id'], row['hash'], 'demo')
        result = store.publish_mock(row['id'])
        assert result['payload']['totals']['final_total_vnd'] == '1092000'
        checks.append('settled_mock_total_correct')
        return {'status': 'passed', 'checks': checks, 'data': 'synthetic_only',
                'production_writes': 0, 'business_rules_configured': False}
    finally:
        store.close()
