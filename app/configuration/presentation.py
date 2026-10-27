from datetime import datetime
from decimal import Decimal

from app.observability.policies import SECRET_TEXT, safe_details


def public(value):
    """Render validated fields after credential references have been removed.

    Keep legitimate fields such as max_output_tokens and credential-presence flags.
    Free metadata is separately validated; strings still receive credential redaction.
    """
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: public(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [public(item) for item in value]
    if isinstance(value, str):
        return SECRET_TEXT.sub(lambda match: (match[1] or match[2] or match[3])+'[REDACTED]', value)
    return safe_details(value)
