"""Tracking configuration helper for integration connections.

The supported location for tracking settings is ``provider_settings.tracking``;
the top-level ``tracking`` key is a legacy fallback that the product configuration
API cannot set directly.
"""
import copy
from typing import Any, Dict


def get_tracking_config(connection: Any) -> Dict[str, Any]:
    """Extract tracking configuration section from an IntegrationConnection.

    Precedence:
    1. config["provider_settings"]["tracking"] if it is a dict.
    2. config["tracking"] (legacy) if it is a dict.
    3. Empty dict {} otherwise.

    Always returns a copy of the dictionary so mutating the result does
    not affect the stored connection configuration.
    """
    config = getattr(connection, "config", None)
    if not isinstance(config, dict):
        return {}

    provider_settings = config.get("provider_settings")
    if isinstance(provider_settings, dict):
        t_cfg = provider_settings.get("tracking")
        if isinstance(t_cfg, dict):
            return copy.deepcopy(t_cfg)

    legacy_cfg = config.get("tracking")
    if isinstance(legacy_cfg, dict):
        return copy.deepcopy(legacy_cfg)

    return {}
