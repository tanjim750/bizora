"""Query parameter validation helpers for Knowledge API (KB-B1, KB-B2)."""
import re
from typing import Any, Container, Optional
from rest_framework.exceptions import ValidationError

MAX_BIGINT = 2**63 - 1
STATUS_REGEX = re.compile(r"^[A-Z_]{1,30}$")


def reject_unknown(query_params: Any, allowed: Container[str]) -> None:
    """Raise ValidationError for the first parameter key not in allowed."""
    for key in query_params.keys():
        if key not in allowed:
            raise ValidationError({key: "Unsupported parameter."})


def read_int(
    query_params: Any,
    name: str,
    *,
    default: Optional[int] = None,
    minimum: Optional[int] = None,
    maximum: Optional[int] = None,
) -> Optional[int]:
    """Read and validate an integer parameter."""
    if name not in query_params:
        return default

    values = query_params.getlist(name) if hasattr(query_params, "getlist") else [query_params[name]]
    if len(values) > 1:
        raise ValidationError({name: "Repeated parameter."})

    val_str = values[0]
    if val_str is None or val_str == "":
        return default

    try:
        val = int(val_str)
        if str(val) != str(val_str).strip():
            raise ValueError()
    except (ValueError, TypeError):
        raise ValidationError({name: f"Parameter '{name}' must be an integer."})

    if minimum is not None and val < minimum:
        raise ValidationError({name: f"Parameter '{name}' must be at least {minimum}."})

    if maximum is not None and val > maximum:
        raise ValidationError({name: f"Parameter '{name}' must be at most {maximum}."})

    return val


def read_status(query_params: Any) -> Optional[str]:
    """Read and validate an optional uppercase status enum parameter."""
    if "status" not in query_params:
        return None

    values = query_params.getlist("status") if hasattr(query_params, "getlist") else [query_params["status"]]
    if len(values) > 1:
        raise ValidationError({"status": "Repeated parameter."})

    val = values[0]
    if val is None or val == "":
        return None

    if not STATUS_REGEX.match(str(val)):
        raise ValidationError({"status": "Invalid status format."})

    return str(val)
