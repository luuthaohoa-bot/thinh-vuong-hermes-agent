"""SQLite drafts, immutable approvals and a transactional mock outbox.

Local draft/audit storage is not production sales storage. Trust boundary is the
operator's OS account; this CLI is not a multi-user authorization service.
"""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from .model import digest, validate, totals, required


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path, timeout=15, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS drafts (
          id TEXT PRIMARY KEY, business_key TEXT UNIQUE NOT NULL,
          revision INTEGER NOT NULL, body TEXT NOT NULL, hash TEXT NOT NULL,
          approved_hash TEXT, approver TEXT);
        CREATE TABLE IF NOT EXISTS audit (
          seq INTEGER PRIMARY KEY, at TEXT NOT NULL, action TEXT NOT NULL,
          order_id TEXT NOT NULL, revision INTEGER NOT NULL, actor TEXT NOT NULL,
          hash TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS mock_writes (
          idempotency_key TEXT PRIMARY KEY, order_id TEXT NOT NULL,
          revision INTEGER NOT NULL, payload TEXT NOT NULL);
        ''')

    def close(self):
        self.db.close()

    @contextmanager
    def transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def event(self, action, row, actor):
        self.db.execute('INSERT INTO audit(at,action,order_id,revision,actor,hash) VALUES(?,?,?,?,?,?)',
                        (datetime.now(timezone.utc).isoformat(), action, row['id'], row['revision'], actor, row['hash']))

    def get(self, order_id):
        row = self.db.execute('SELECT * FROM drafts WHERE id=?', (order_id,)).fetchone()
        if not row:
            raise ValueError('Order not found')
        out = dict(row)
        out['record'] = json.loads(out.pop('body'))
        out['totals'] = totals(out['record'])
        return out

    def create(self, record):
        record = validate(record)
        key = digest([record['customer'].casefold(), record['sale_date'], record['order_ref'].casefold()])
        order_id = digest([record['source_hash'], record['order_ref'].casefold()])[:24]
        h = digest(record)
        with self.transaction():
            old = self.db.execute('SELECT id,hash FROM drafts WHERE id=? OR business_key=?', (order_id, key)).fetchone()
            if old:
                if old['hash'] == h:
                    return self.get(old['id'])
                raise ValueError('Duplicate source/order or business key; edit the existing draft')
            self.db.execute('INSERT INTO drafts VALUES(?,?,?,?,?,?,?)',
                            (order_id, key, 1, json.dumps(record, ensure_ascii=False), h, None, None))
            row = self.get(order_id)
            self.event('created_draft', row, 'local_operator')
        return row

    def revise(self, order_id, record, expected_hash):
        record = validate(record)
        with self.transaction():
            old = self.get(order_id)
            if old['hash'] != expected_hash:
                raise ValueError('Stale draft; review current version')
            if any(record[k] != old['record'][k] for k in ('source_hash', 'order_ref', 'customer', 'sale_date')):
                raise ValueError('Identity fields cannot be changed')
            if digest(record) == old['hash']:
                return old
            self.db.execute('UPDATE drafts SET revision=revision+1,body=?,hash=?,approved_hash=NULL,approver=NULL WHERE id=?',
                            (json.dumps(record, ensure_ascii=False), digest(record), order_id))
            row = self.get(order_id)
            self.event('revised_approval_invalidated', row, 'local_operator')
        return row

    def approve(self, order_id, expected_hash, actor):
        actor = required(actor, 'approver')
        with self.transaction():
            row = self.get(order_id)
            if row['hash'] != expected_hash:
                raise ValueError('Stale review hash')
            if row['record'].get('routing', {}).get('status') != 'assigned':
                raise ValueError('Assign a customer route before approval')
            self.db.execute('UPDATE drafts SET approved_hash=hash,approver=? WHERE id=?', (actor, order_id))
            self.event('approved', row, actor)
        return self.get(order_id)

    def publish_mock(self, order_id):
        """No HTTP, credentials or production URL; revision-keyed snapshot upsert."""
        with self.transaction():
            row = self.get(order_id)
            if row['approved_hash'] != row['hash']:
                raise ValueError('Approve the exact current revision before writing')
            if row['record'].get('routing', {}).get('status') != 'assigned':
                raise ValueError('Assign a customer route before writing')
            key = f"{order_id}:{row['revision']}"
            payload = {'connector': 'haisanthinhvuong_mock', 'operation': 'upsert_order',
                       'order_id': order_id, 'revision': row['revision'],
                       'record': row['record'], 'totals': row['totals']}
            cursor = self.db.execute('INSERT OR IGNORE INTO mock_writes VALUES(?,?,?,?)',
                                    (key, order_id, row['revision'], json.dumps(payload, ensure_ascii=False)))
            if cursor.rowcount:
                self.event('mock_upsert', row, row['approver'])
        return {'idempotency_key': key, 'inserted': bool(cursor.rowcount), 'payload': payload}
