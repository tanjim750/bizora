"""Text preview helper for knowledge documents (KB-B1)."""
import re
from typing import Optional

PREVIEW_CHARS = 160


def build_preview(raw_prefix: Optional[str]) -> Optional[str]:
    """Build a collapsed, clean preview up to 160 characters from raw prefix."""
    if not raw_prefix:
        return None

    truncated = len(raw_prefix) > PREVIEW_CHARS
    prefix = raw_prefix[:PREVIEW_CHARS]

    # Remove non-printable characters except whitespace
    cleaned_chars = [c for c in prefix if c.isprintable() or c.isspace()]
    cleaned_str = "".join(cleaned_chars)

    # Collapse all whitespace runs to one space and strip
    collapsed = re.sub(r"\s+", " ", cleaned_str).strip()
    if not collapsed:
        return None

    if truncated:
        return f"{collapsed}…"
    return collapsed
