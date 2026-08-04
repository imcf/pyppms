"""Tests for the PpmsUser class."""

from pyppms.common import set_loglevel
from pyppms.user import PpmsUser

set_loglevel("TRACE")


def test_user_details(user_details, ppms_user):
    """Test the PpmsUser constructor, __str__() and details()."""
    print(user_details["login"])
    print(ppms_user.__str__())
    assert ppms_user.__str__() == user_details["login"]

    print(user_details["expected"])
    print(ppms_user.details())
    assert ppms_user.details() == user_details["expected"]


def test_user_billing_info(user_details, ppms_connection):
    """Test the PpmsUser billing information."""
    user = PpmsUser(user_details["api_response"], conn=ppms_connection)
    assert len(user.billing_info) == 2

    assert user.billing_info[0].billing_code == "pyppms_group_billing_code"
    assert user.billing_info[0].billing_type == "group"

    assert user.billing_info[1].billing_code == "pyppms_user_billing_code"
    assert user.billing_info[1].billing_type == "user"


def test_user_fullname(user_details, ppms_user):
    """Test the PpmsUser fullname property."""
    assert ppms_user.fullname == f"{user_details['lname']} {user_details['fname']}"
    ppms_user._fullname = ""
    assert ppms_user.fullname == user_details["login"]
