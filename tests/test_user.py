"""Tests for the PpmsUser class."""

from pyppms.common import set_loglevel
from pyppms.user import PpmsUser

from helpers import switch_cache_mocks

set_loglevel("TRACE")


def test_user_details(user_details, ppms_user):
    """Test the PpmsUser constructor, __str__() and details()."""
    print(user_details["login"])
    print(ppms_user.__str__())
    assert ppms_user.__str__() == user_details["login"]

    print(user_details["expected"])
    print(ppms_user.details())
    assert ppms_user.details() == user_details["expected"]


def test_user_billing_info(user_details, ppms_connection, group_details):
    """Test the PpmsUser billing information."""
    user = PpmsUser(user_details["api_response"], conn=ppms_connection)
    assert len(user.billing_info) == 3

    assert user.billing_info[0].billing_code == user_details["bcode"]
    assert user.billing_info[0].billing_type == "user"

    assert user.billing_info[1].billing_code == group_details.billing_info.billing_code
    assert user.billing_info[1].billing_type == group_details.billing_info.billing_type

    assert user.billing_info[2].billing_code == "proj.bcode.6"
    assert user.billing_info[2].billing_type == "project"
    assert user.billing_info[2].description == "[6]: Project Six"


def test_user_fullname(user_details, ppms_user):
    """Test the PpmsUser fullname property."""
    assert ppms_user.fullname == f"{user_details['lname']} {user_details['fname']}"
    ppms_user._fullname = ""
    assert ppms_user.fullname == user_details["login"]


def test_user_project_fails(user_details, ppms_connection, caplog):
    """Test user instantiation when one of its projects fails."""
    switch_cache_mocks(
        ppms_connection, "project_missing", "non-existing user project referenced"
    )
    # trigger the "getuserprojects" request
    ppms_connection.get_user_projects(user_details["login"])
    PpmsUser(user_details["api_response"], conn=ppms_connection)
    assert "Processing project 42 failed" in caplog.text
