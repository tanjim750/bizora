import logging
from collections import defaultdict

from django.db import transaction

logger = logging.getLogger(__name__)

_subscribers = defaultdict(list)


def subscribe(event_name, handler):
    if handler not in _subscribers[event_name]:
        _subscribers[event_name].append(handler)


def _execute_dispatch(event):
    event_name = getattr(event, "name", getattr(event, "type", str(event)))
    for handler in list(_subscribers[event_name]):
        try:
            handler(event)
        except Exception:
            logger.exception(
                "Error executing event handler %s for %s", handler, event_name
            )


def dispatch(event):
    try:
        connection = transaction.get_connection()
        if connection.in_atomic_block:
            transaction.on_commit(lambda: _execute_dispatch(event))
            return
    except Exception:  # noqa: BLE001, S110 - direct execution fallback if transaction context unavailable
        pass
    _execute_dispatch(event)
