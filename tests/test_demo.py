import sqlite3
import unittest
from hermes.demo import run
from hermes.telegram import enqueue


class AcceptanceTests(unittest.TestCase):
    def test_master_has_five_workers_and_does_not_invent_debt(self):
        from hermes.store import Store
        from hermes.master import run as master
        from pathlib import Path
        import json
        store = Store(':memory:')
        try:
            record = json.loads((Path(__file__).resolve().parents[1] / 'examples/order.json').read_text())
            row = store.create(record)
            with self.assertRaises(ValueError): store.approve(row['id'], row['hash'], 'test')
            report = master(store)
            self.assertEqual(len([k for k in report if k.startswith('agent')]), 5)
            self.assertIsNone(report['agent04_receivables'][0]['balance_vnd'])
            self.assertFalse(report['agent02_receipts'][0]['issued'])
            self.assertEqual(store.db.execute('SELECT count(*) FROM mock_writes').fetchone()[0], 0)
        finally:
            store.close()

    def test_full_mock_workflow(self):
        result = run()
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(len(result['checks']), 6)

    def test_telegram_xlsx_queue_and_retry(self):
        db = sqlite3.connect(':memory:')
        update = {'update_id': 123, 'message': {'chat': {'id': 42, 'type': 'private'},
            'document': {'file_id': 'demo', 'file_size': 100,
            'mime_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}}}
        try:
            with self.assertRaises(ValueError): enqueue(db, update, 'wrong', 'secret', [42])
            self.assertTrue(enqueue(db, update, 'secret', 'secret', [42])['inserted'])
            self.assertFalse(enqueue(db, update, 'secret', 'secret', [42])['inserted'])
            self.assertEqual(db.execute('SELECT COUNT(*) FROM telegram_inbox').fetchone()[0], 1)
        finally:
            db.close()
