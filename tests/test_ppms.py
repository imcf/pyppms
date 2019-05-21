"""Tests for the 'ppms' module."""

# TODO: pylint for Python2 complains about redefining an outer scope when using
# pytest fixtures, this is supposed to be fixed in newer versions, so it should
# be checked again after migration to Python3 (see pylint issue #1535):
# pylint: disable-msg=redefined-outer-name
# pylint: disable-msg=consider-iterating-dictionary

import logging
import pytest
from requests.exceptions import ConnectionError

import pumapyconf
from pumapy import ppms

__author__ = "Niko Ehrenfeuchter"
__copyright__ = __author__
__license__ = "gpl3"


@pytest.fixture
def ppms_connection(caplog):
    """Establish a connection to a PPMS / PUMAPI instance."""
    caplog.set_level(logging.DEBUG)
    conn = ppms.PpmsConnection(
        pumapyconf.PUMAPI_URL,
        pumapyconf.PPMS_API_KEY,
        timeout=5
    )
    return conn


def test_ppmsconnection(ppms_connection):
    """Test establishing a PPMS connection."""
    assert ppms_connection.status['auth_state'] == 'good'


def test_ppmsconnection_fail():
    """Test various ways how establishing a connection could fail."""

    # wrong PUMAPI URL:
    with pytest.raises(ConnectionError):
        ppms.PpmsConnection('https://url.example', '')

    # no API key:
    with pytest.raises(ConnectionError):
        ppms.PpmsConnection(pumapyconf.PUMAPI_URL, '')

    # wrong API key (trailing characters):
    with pytest.raises(ConnectionError):
        ppms.PpmsConnection(pumapyconf.PUMAPI_URL,
                            pumapyconf.PPMS_API_KEY + 'appendixx')


def test_get_users(ppms_connection):
    """Test getting a list of user IDs from PPMS."""
    users = ppms_connection.get_users(active=False)
    print users
    assert u'pumapy' in users

    users = ppms_connection.get_users(active=True)
    print users
    assert u'pumapy' in users


def test_get_user_dict(ppms_connection,
                       user_details_raw,
                       user_admin_details_raw):
    """Test fetching details of a specific user."""
    print "Expected dict data: %s" % user_details_raw
    details = ppms_connection.get_user_dict('pumapy')
    print "Retrieved dict data: %s" % details
    assert user_details_raw == details

    print "Expected dict data: %s" % user_admin_details_raw
    details = ppms_connection.get_user_dict('pumapy-adm')
    print "Retrieved dict data: %s" % details
    assert user_admin_details_raw == details

    with pytest.raises(KeyError):
        ppms_connection.get_user_dict('_hopefully_unknown_username_')


def test_get_groups(ppms_connection):
    """Test getting a list of group IDs ("unitlogin") from PPMS."""
    groups = ppms_connection.get_groups()
    print groups
    assert u'pumapy_group' in groups


def test_get_group(ppms_connection, group_details):
    """Test fetching details of a specific group."""
    print "Expected dict data (subset): %s" % group_details
    details = ppms_connection.get_group('pumapy_group')
    print "Retrieved dict data: %s" % details
    for key in group_details.keys():
        assert group_details[key] == details[key]

    with pytest.raises(KeyError):
        ppms_connection.get_group('_hopefully_unknown_unitlogin_name_')


def test_get_user(ppms_connection, ppms_user, ppms_user_admin):
    """Test the get_user() method."""
    user = ppms_connection.get_user('pumapy')
    print user.details()
    print ppms_user.details()
    assert user.details() == ppms_user.details()

    user = ppms_connection.get_user('pumapy-adm')
    print user.details()
    print ppms_user_admin.details()
    assert user.details() == ppms_user_admin.details()

    with pytest.raises(KeyError):
        ppms_connection.get_user('_hopefully_unknown_username_')


def test_get_admins(ppms_connection, ppms_user_admin):
    """Test the get_admins() method."""
    admins = ppms_connection.get_admins()

    usernames = list()
    admin_user = None
    for admin in admins:
        usernames.append(admin.username)
        if admin.username == 'pumapy-adm':
            admin_user = admin

    print usernames
    assert 'pumapy-adm' in usernames

    print admin_user.details()
    assert admin_user.details() == ppms_user_admin.details()


def test_get_group_users(ppms_connection, ppms_user, ppms_user_admin):
    """Test the get_group_users() method."""
    # TODO: that's certainly not the nicest test, it really needs to be
    # refactored once the get_group_users() method returns a dict instead of a
    # list of user objects!
    members = ppms_connection.get_group_users('pumapy_group')
    for user in members:
        print user.details()
        if user.username == 'pumapy':
            assert user.details() == ppms_user.details()
        elif user.username == 'pumapy-adm':
            assert user.details() == ppms_user_admin.details()
        else:
            raise KeyError('Unexpected username: %s' % user.username)

    assert ppms_connection.get_group_users('') == list()


def test_get_user_experience(ppms_connection):
    """Test the get_user_experience() method."""
    # TODO: system IDs are currently hard-coded here, so this will fail on any
    # other PPMS instance!

    # check if we get some experience data after all:
    assert len(ppms_connection.get_user_experience()) > 0

    # check if a user has access to a specific system:
    systems = ppms_connection.get_user_experience(login='pumapy')
    sys_ids = list()
    for system in systems:
        sys_ids.append(system['id'])
    assert '31' in sys_ids

    # check if a system is having a specific user with permission to access it:
    users = ppms_connection.get_user_experience(system_id=31)
    usernames = list()
    for user in users:
        usernames.append(user['login'])
    assert 'pumapy' in usernames

    # check if filtering for user *and* system results in exactly one entry:
    assert len(ppms_connection.get_user_experience('pumapy', 31)) == 1
