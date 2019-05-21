"""Module-wide fixtures for testing pumapy."""

# TODO: pylint for Python2 complains about redefining an outer scope when using
# pytest fixtures, this is supposed to be fixed in newer versions, so it should
# be checked again after migration to Python3 (see pylint issue #1535):
# pylint: disable-msg=redefined-outer-name

import pytest

from pumapy.user import PpmsUser

__author__ = "Niko Ehrenfeuchter"
__copyright__ = __author__
__license__ = "gpl3"


@pytest.fixture(scope="module")
def user_details():
    """Helper function providing a dict with default user details.

    Returns
    -------
    dict
    """
    username = 'pumapy'
    lname = 'Python'
    fname = 'PumAPI'
    fullname = "%s %s" % (lname, fname)
    email = 'pumapy@python-facility.example'
    unitlogin = 'pumapy_group'

    return {
        'username': username,
        'lname': lname,
        'fname': fname,
        'email': email,
        'unitlogin': unitlogin,
        'fullname': fullname,
        'expected': (
            'username: %s, email: %s, fullname: %s, ppms_group: %s, '
            'active: True' % (username, email, fullname, unitlogin)
        ),
        'api_response': (
            u'login,lname,fname,email,phone,bcode,affiliation,'
            u'unitlogin,mustchpwd,mustchbcode,active\r\n'
            '"%s","%s","%s","%s","","","","%s",false,false,true\r\n' %
            (username, lname, fname, email, unitlogin)
        ),
    }


@pytest.fixture(scope="module")
def group_details():
    """Helper function providing a dict with default group details.

    Returns
    -------
    dict
    """
    return {
        u'heademail': u'group-leader@python-facility.example',
        u'unitname': u'Python Core Facility',
        u'unitlogin': u'pumapy_group',
        u'unitbcode': u'pumapy_group',
        u'department': u'Scientific Software Support',
        u'headname': u'PythonGroup Supervisor',
        u'active': True,
        u'institution': u'Famous Research Foundation',
    }


@pytest.fixture(scope="module")
def ppms_user(user_details):
    """Helper function to create a PpmsUser object with default values.

    Parameters
    ----------
    user_details : dict
        A dictionary with user details.

    Returns
    -------
    pumapy.user.PpmsUser
    """
    return PpmsUser(
        username=user_details['username'],
        email=user_details['email'],
        fullname=user_details['fullname'],
        ppms_group=user_details['unitlogin']
    )


@pytest.fixture(scope="module")
def ppms_user_from_response(user_details):
    """Helper function to create a PpmsUser object with default values.

    Parameters
    ----------
    user_details : dict
        A dictionary with user details.

    Returns
    -------
    pumapy.user.PpmsUser
    """
    return PpmsUser.from_response(user_details['api_response'])
