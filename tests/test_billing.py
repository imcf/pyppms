"""Tests for the PpmsBillingInformation class."""

import pytest

from pyppms.billing import PpmsBillingInformation
from pyppms.common import set_loglevel

set_loglevel("TRACE")


def test_billing_code_empty():
    """Test the constructor with an empty billing code."""
    with pytest.raises(ValueError):
        PpmsBillingInformation("", "")


def test_billing_type_invalid():
    """Test the constructor with an invalid billing type."""
    with pytest.raises(ValueError):
        PpmsBillingInformation("007", "unknown_type")


def test_billing_info_description():
    """Test the constructor with description."""
    info = PpmsBillingInformation("007", "user", "billing info description")
    assert info.description == "billing info description"


def test_billing_info_equality():
    """Test the equality built-in method for edge cases."""
    info = PpmsBillingInformation("007", "user")
    assert info.__eq__("a random string") is False
    assert info.__eq__(None) is False


def test_get_billing_codes(ppms_connection):
    """Test get_billing_codes()."""
    codes = ppms_connection.get_billing_codes()

    assert codes["projects"][7] == {
        "billing_code": "proj.bcode.7",
        "subsidy": "",
        "charges": 2550.55,
    }

    assert codes["users"]["pyppms"] == {
        "billing_code": "pyppms_user_billing_code",
        "subsidy": "",
        "charges": 36363.1111,
    }
