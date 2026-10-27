import json
import unittest
from pathlib import Path
from hermes.routing import route
from hermes.store import Store


class RoutingTests(unittest.TestCase):
    def test_unknown_and_no_fuzzy_match(self):
        rules = {'rules': [{'customer': 'Khách A', 'destination': 'Luồng 1'}]}
        self.assertEqual(route(' KHÁCH A ', rules)['destination'], 'Luồng 1')
        self.assertEqual(route('Khach A', rules)['status'], 'pending')
        with self.assertRaises(ValueError):
            route('x', {'rules': rules['rules'] * 2})

    def test_route_change_invalidates_approval(self):
        record = json.loads((Path(__file__).resolve().parents[1] / 'examples/order.json').read_text())
        record['routing'] = route(record['customer'], {'rules': []})
        store = Store(':memory:')
        try:
            row = store.create(record)
            with self.assertRaises(ValueError): store.approve(row['id'], row['hash'], 'operator')
            record['routing'] = route(record['customer'], {'rules': [
                {'customer': record['customer'], 'destination': 'Mock A'}]})
            row = store.revise(row['id'], record, row['hash'])
            store.approve(row['id'], row['hash'], 'operator')
            self.assertTrue(store.publish_mock(row['id'])['inserted'])
            record['routing'] = route(record['customer'], {'rules': [
                {'customer': record['customer'], 'destination': 'Mock B'}]})
            row = store.revise(row['id'], record, row['hash'])
            with self.assertRaises(ValueError): store.publish_mock(row['id'])
            store.approve(row['id'], row['hash'], 'operator')
            result = store.publish_mock(row['id'])
            self.assertEqual(result['payload']['record']['routing']['destination'], 'Mock B')
        finally:
            store.close()
