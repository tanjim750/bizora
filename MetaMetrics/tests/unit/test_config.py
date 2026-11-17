"""Tests for the client configuration.

Ported from ``tests/Unit/Config/MetaConfigTest.php``.
"""

from __future__ import annotations

import dataclasses
import pickle

import pytest

from metametrics.config import MetaConfig
from metametrics.exceptions import InvalidConfigurationError

SECRET = "secret-token-that-must-not-leak"


def test_it_creates_a_valid_configuration() -> None:
    config = MetaConfig(access_token="valid-access-token", ad_account_id="act_123456789", api_version="v23.0")

    assert config.access_token == "valid-access-token"
    assert config.ad_account_id == "act_123456789"
    assert config.api_version == "v23.0"


def test_it_is_immutable() -> None:
    config = MetaConfig(access_token="token", ad_account_id="act_123456789", api_version="v23.0")

    with pytest.raises(dataclasses.FrozenInstanceError):
        config.access_token = "other"  # type: ignore[misc]


def test_it_preserves_the_access_token_exactly() -> None:
    config = MetaConfig(
        access_token="  token-with-whitespace\n",
        ad_account_id="act_123456789",
        api_version="v24.0",
    )

    assert config.access_token == "  token-with-whitespace\n"


def test_it_normalizes_a_numeric_ad_account_id() -> None:
    config = MetaConfig(access_token="token", ad_account_id="00123456789", api_version="v23.0")

    assert config.ad_account_id == "act_00123456789"


@pytest.mark.parametrize("access_token", ["", "   ", "\t\n"])
def test_it_rejects_an_invalid_access_token(access_token: str) -> None:
    with pytest.raises(InvalidConfigurationError, match="Meta Access Token"):
        MetaConfig(access_token=access_token, ad_account_id="act_123456789", api_version="v23.0")


@pytest.mark.parametrize(
    "ad_account_id",
    ["", "act_", "act_abc", "abc123", "act_123_456", " act_123456789 "],
)
def test_it_rejects_an_invalid_ad_account_id(ad_account_id: str) -> None:
    with pytest.raises(InvalidConfigurationError, match="Meta Ad Account ID"):
        MetaConfig(access_token="token", ad_account_id=ad_account_id, api_version="v23.0")


@pytest.mark.parametrize(
    "api_version",
    ["", "23", "23.0", "version23", "v23", "v23.x", " v23.0 "],
)
def test_it_rejects_an_invalid_api_version(api_version: str) -> None:
    with pytest.raises(InvalidConfigurationError, match="Meta Marketing API Version"):
        MetaConfig(access_token="token", ad_account_id="act_123456789", api_version=api_version)


def test_validation_exceptions_never_expose_the_access_token() -> None:
    with pytest.raises(InvalidConfigurationError) as error:
        MetaConfig(access_token=SECRET, ad_account_id="invalid-account", api_version="v23.0")

    assert SECRET not in str(error.value)


def test_debug_output_redacts_the_access_token() -> None:
    config = MetaConfig(access_token=SECRET, ad_account_id="act_123456789", api_version="v23.0")

    debug_output = repr(config)

    assert SECRET not in debug_output
    assert "[REDACTED]" in debug_output


def test_serialized_output_redacts_the_access_token() -> None:
    config = MetaConfig(access_token=SECRET, ad_account_id="act_123456789", api_version="v23.0")

    serialized = pickle.dumps(config)

    assert SECRET not in serialized.decode("latin-1")
    assert "[REDACTED]" in serialized.decode("latin-1")


def test_a_redacted_configuration_cannot_be_restored() -> None:
    config = MetaConfig(access_token=SECRET, ad_account_id="act_123456789", api_version="v23.0")

    with pytest.raises(RuntimeError, match="cannot be deserialized"):
        pickle.loads(pickle.dumps(config))
