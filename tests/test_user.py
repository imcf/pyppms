"""Tests for the PpmsUser class."""

__author__ = "Niko Ehrenfeuchter"
__copyright__ = __author__
__license__ = "gpl3"


def test_user_details(user_details, ppms_user):
    """Test the PpmsUser constructor, __str__() and details()."""
    print(user_details["login"])
    print(ppms_user.__str__())
    assert ppms_user.__str__() == user_details["login"]

    print(user_details["expected"])
    print(ppms_user.details())
    assert ppms_user.details() == user_details["expected"]


def test_user_from_response(user_details, ppms_user_from_response):
    """Test the PpmsUser.from_response() constructor."""

    # default
    print(user_details["api_response"])
    print(user_details["expected"])
    user = ppms_user_from_response
    print(user.details())
    assert user.details() == user_details["expected"]

    # fullname fallback if empty
    user2 = ppms_user_from_response
    user2._fullname = ""  # pylint: disable-msg=protected-access
    print(user2.details())

    assert user2.fullname == user_details["login"]
