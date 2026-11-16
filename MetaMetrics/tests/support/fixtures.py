"""Shared pytest fixtures and helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FIXTURE_ROOT = Path(__file__).parent.parent / "fixtures"


def load_request_fixture(name: str) -> dict[str, Any]:
    """Load a golden request fixture by name (without the ``.json`` suffix)."""
    path = FIXTURE_ROOT / "requests" / f"{name}.json"

    with path.open(encoding="utf-8") as handle:
        data: dict[str, Any] = json.load(handle)
        return data


def load_meta_fixture(name: str) -> Any:
    """Load a Meta response fixture by name (without the ``.json`` suffix)."""
    path = FIXTURE_ROOT / "meta" / f"{name}.json"

    with path.open(encoding="utf-8") as handle:
        return json.load(handle)

