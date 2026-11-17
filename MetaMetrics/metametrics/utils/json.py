"""JSON encoding that matches PHP's ``json_encode`` defaults.

PHP escapes forward slashes (``/`` becomes ``\\/``) unless
``JSON_UNESCAPED_SLASHES`` is passed, and it never inserts whitespace. The
Python standard library does neither, so query parameters would otherwise
differ from the strings the PHP library produces.
"""

from __future__ import annotations

import json
from typing import Any

__all__ = ["php_json_dumps"]


def php_json_dumps(value: Any) -> str:
    """Encode a value the way PHP's ``json_encode`` does by default."""
    encoded = json.dumps(value, separators=(",", ":"), ensure_ascii=True)

    return encoded.replace("/", "\\/")
