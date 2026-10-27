"""Pure webhook validation scaffold: no network calls, downloads or approval.

Deploy behind HTTPS; validate the Telegram secret header before parsing updates.
Persist update_id uniquely in a future receiver before downloading attachments.
"""
import hmac


def parse_update(update, supplied_secret, configured_secret, allowed_chat_ids):
    if not configured_secret or not hmac.compare_digest(supplied_secret or '', configured_secret):
        raise ValueError('Invalid webhook secret')
    message = update.get('message', {})
    chat = message.get('chat', {})
    if chat.get('type') != 'private' or str(chat.get('id')) not in {str(x) for x in allowed_chat_ids}:
        raise ValueError('Chat not allowed')
    update_id = update.get('update_id')
    if isinstance(update_id, bool) or not isinstance(update_id, int) or update_id < 0:
        raise ValueError('Invalid update_id')
    document = message.get('document', {})
    if document.get('mime_type') not in {'application/pdf', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'} or not document.get('file_id'):
        raise ValueError('Expected PDF or XLSX document')
    size = document.get('file_size', 0)
    if isinstance(size, bool) or not isinstance(size, int) or not 0 < size <= 25_000_000:
        raise ValueError('Invalid PDF size')
    return {'update_id': update_id, 'chat_id': str(chat['id']),
            'file_id': document['file_id'], 'action': 'queue_for_review_only'}


def enqueue(db, update, supplied_secret, configured_secret, allowed_chat_ids):
    """Durable local receipt; caller supplies an sqlite3 connection."""
    import json
    receipt = parse_update(update, supplied_secret, configured_secret, allowed_chat_ids)
    db.execute('CREATE TABLE IF NOT EXISTS telegram_inbox (update_id INTEGER PRIMARY KEY, receipt TEXT NOT NULL)')
    with db:
        cursor = db.execute('INSERT OR IGNORE INTO telegram_inbox VALUES (?,?)',
                            (receipt['update_id'], json.dumps(receipt)))
    return {'inserted': bool(cursor.rowcount), 'receipt': receipt}
