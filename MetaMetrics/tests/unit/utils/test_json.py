"""Tests for the PHP-compatible JSON encoder."""

from __future__ import annotations

from metametrics.utils.json import php_json_dumps


def test_it_encodes_without_whitespace() -> None:
    assert php_json_dumps(["ACTIVE", "PAUSED"]) == '["ACTIVE","PAUSED"]'


def test_it_escapes_forward_slashes_like_php() -> None:
    assert php_json_dumps(["a/b"]) == '["a\\/b"]'


def test_it_escapes_non_ascii_like_php() -> None:
    assert php_json_dumps(["café"]) == '["caf\\u00e9"]'


def test_it_encodes_a_filter_like_php() -> None:
    assert (
        php_json_dumps([{"field": "campaign.id", "operator": "IN", "value": ["1", "2"]}])
        == '[{"field":"campaign.id","operator":"IN","value":["1","2"]}]'
    )
