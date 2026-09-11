import logging
from collections import defaultdict
from django.db import transaction

logger = logging.getLogger(__name__)

_subscribers = defaultdict(list)


def subscribe(event_name, handler):
    if handler not in _subscribers[event_name]:
        _subscribers[event_name].append(handler)


def _execute_dispatch(event):
    for handler in list(_subscribers[event.name]):
        try:
            handler(event)
        except Exception as exc:
            logger.exception("Error executing event handler %s for %s: %s", handler, event.name, exc)


def dispatch(event):
    try:
        connection = transaction.get_connection()
        if connection.in_atomic_block:
            transaction.on_commit(lambda: _execute_dispatch(event))
            return
    except Exception:
        pass
    _execute_dispatch(event)
