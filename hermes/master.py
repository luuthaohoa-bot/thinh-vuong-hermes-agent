"""Five local workers coordinated by Master; read-only reporting, no auto approval."""
from decimal import Decimal


def run(store):
    orders = [store.get(r[0]) for r in store.db.execute('SELECT id FROM drafts ORDER BY id')]
    sales, receipts, control, debts = [], [], [], []
    for row in orders:
        record = row['record']
        approved = row['approved_hash'] == row['hash']
        sales.append({'id': row['id'], 'revision': row['revision'], 'customer': record['customer'],
                      'routing': record.get('routing'), 'approved': approved})
        issues = []
        if not approved: issues.append('awaiting_approval')
        if record.get('routing', {}).get('status') != 'assigned': issues.append('awaiting_route')
        if row['totals']['final_total_vnd'] is None: issues.append('awaiting_market_price')
        control.append({'id': row['id'], 'issues': issues})
        receipts.append({'id': row['id'], 'revision': row['revision'],
                         'kind': 'draft_sales_receipt', 'issued': False,
                         'total_vnd': row['totals']['final_total_vnd']})
        debts.append({'id': row['id'], 'sales_total_vnd': row['totals']['final_total_vnd'],
                      'paid_vnd': None, 'balance_vnd': None,
                      'status': 'payment_records_required'})
    return {'mode': 'local_review_only', 'agent01_sales': sales, 'agent02_receipts': receipts,
            'agent03_control': control, 'agent04_receivables': debts,
            'agent05_report': {'orders': len(orders),
                'approved_orders': sum(r['approved_hash'] == r['hash'] for r in orders),
                'known_sales_vnd': str(sum((Decimal(r['totals']['known_total_vnd']) for r in orders), Decimal(0))),
                'pending_price_orders': sum(r['totals']['final_total_vnd'] is None for r in orders),
                'scope': 'current_drafts_not_accounting_revenue',
                'telegram_delivery': 'not_configured'}}
