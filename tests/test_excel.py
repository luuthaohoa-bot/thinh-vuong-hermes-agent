import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
from hermes.excel import candidates, HEADERS
from hermes.store import Store


class ExcelTests(unittest.TestCase):
    def parse(self, values):
        def cells(row, values):
            return [type('Cell', (), {'value': v, 'row': row,
                                     'data_type': 'f' if isinstance(v, str) and v.startswith('=') else 's'})()
                    for v in values]
        ws = MagicMock()
        ws.max_row = len(values) + 1
        ws.max_column = 9
        ws.iter_rows.side_effect = [iter([cells(1, HEADERS)]),
                                   iter([cells(i + 2, v) for i, v in enumerate(values)])]
        wb = MagicMock()
        wb.__getitem__.return_value = ws
        wb.sheetnames = ['Sổ bán hàng']
        with patch('hermes.excel.load_workbook', return_value=wb), \
             patch('hermes.excel.Path.read_bytes', return_value=b'fixture'):
            return candidates('fixture.xlsx', 'sales-main')

    def line(self, stt=1, qty=8.4, price=130000):
        return [stt, datetime(2026, 10, 24), 'Demo', 'Fish', 'kg', qty, price, '=F2*G2', 1]

    def test_pending_and_no_automatic_approval(self):
        result = self.parse([self.line(price=None)])
        record = result['records'][0]
        self.assertEqual(record['lines'][0]['quantity'], '8.4')
        self.assertIsNone(record['lines'][0]['unit_price_vnd'])
        store = Store(':memory:')
        try:
            draft = store.create(record)
            self.assertEqual(draft['id'], store.create(record)['id'])
            with self.assertRaises(ValueError): store.publish_mock(draft['id'])
        finally: store.close()

    def test_missing_quantity_blocks_whole_customer(self):
        result = self.parse([self.line(), self.line(2, qty=None)])
        self.assertEqual(result['records'], [])
        self.assertEqual(result['blocked_orders'][0]['rows'], [2, 3])

    def test_duplicate_stt_blocks_both_rows(self):
        result = self.parse([self.line(), self.line()])
        self.assertFalse(result['records'])
        self.assertTrue(all('Duplicate STT' in r['errors'] for r in result['rows']))

    def test_formula_input_blocked_and_repeated_products_preserved(self):
        self.assertFalse(self.parse([self.line(qty='=2+2')])['records'])
        result = self.parse([self.line(), self.line(2, qty=10)])
        self.assertEqual(len(result['records'][0]['lines']), 2)
        self.assertEqual(result['summary']['known_total_vnd'], '2392000.0')

    def test_entered_amount_mismatch_blocks(self):
        row = self.line(); row[7] = 1
        self.assertFalse(self.parse([row])['records'])

    def test_customer_case_collision_requires_review(self):
        a, b = self.line(), self.line(2)
        b[2] = 'DEMO'
        result = self.parse([a, b])
        self.assertFalse(result['records'])
        self.assertEqual(len(result['name_review']['case_collisions']), 2)

    def test_business_key_stable_after_save(self):
        record = self.parse([self.line()])['records'][0]
        changed = self.parse([self.line(qty=9)])['records'][0]
        self.assertEqual(record['order_ref'], changed['order_ref'])
        store = Store(':memory:')
        try:
            store.create(record)
            with self.assertRaises(ValueError): store.create(changed)
        finally: store.close()
