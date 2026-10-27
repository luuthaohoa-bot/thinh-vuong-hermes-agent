"""Explicit customer routing. No fuzzy matching or external calls."""
import unicodedata
from .model import required, digest


def key(value):
    return unicodedata.normalize('NFC', required(value, 'customer')).casefold()


def route(customer, config):
    if not isinstance(config, dict) or not isinstance(config.get('rules'), list):
        raise ValueError('Routing config requires a rules list')
    routes = {}
    for rule in config['rules']:
        name = key(rule.get('customer'))
        destination = required(rule.get('destination'), 'destination')
        if name in routes:
            raise ValueError('Duplicate customer routing rule')
        routes[name] = destination
    destination = routes.get(key(customer))
    return {'destination': destination, 'status': 'assigned' if destination else 'pending',
            'rules_hash': digest(config)}
