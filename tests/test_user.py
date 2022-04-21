"""Tests for the PpmsUser class."""


def test_user_details(user_details, ppms_user):
    """Test the PpmsUser constructor, __str__() and details()."""
    print(user_details["login"])
    print(ppms_user.__str__())
    assert ppms_user.__str__() == user_details["login"]

    print(user_details["expected"])
    print(ppms_user.details())
    assert ppms_user.details() == user_details["expected"]
