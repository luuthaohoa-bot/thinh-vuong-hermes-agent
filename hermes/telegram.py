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
    if not isinstance(update_id, int):
        raise ValueError('Invalid update_id')
    document = message.get('document', {})
    if document.get('mime_type') != 'application/pdf' or not document.get('file_id'):
        raise ValueError('Expected PDF document')
    size = document.get('file_size', 0)
    if not isinstance(size, int) or not 0 < size <= 25_000_000:
        raise ValueError('Invalid PDF size')
    return {'update_id': update_id, 'chat_id': str(chat['id']),
            'file_id': document['file_id'], 'action': 'queue_for_review_only'}
