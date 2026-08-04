"""Tests for the PpmsBillingInformation class."""

import pytest

from pyppms.common import set_loglevel
from pyppms.billing import PpmsBillingInformation

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
