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


def test_get_user_dict(ppms_connection):
    """Test fetching details of a specific user."""
    expected = {
        u'active': True,
        u'affiliation': u'',
        u'bcode': u'',
        u'email': u'pumapy@python-facility.example',
        u'fname': u'PumAPI',
        u'lname': u'Python',
        u'login': u'pumapy',
        u'mustchbcode': False,
        u'mustchpwd': False,
        u'phone': u'+98 (76) 54 3210',
        u'unitlogin': u'pumapy_group'
    }
    print "Expected dict data: %s" % expected

    details = ppms_connection.get_user_dict('pumapy')
    print "Retrieved dict data: %s" % details
    assert expected == details

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


def test_get_user(ppms_connection, ppms_user):
    """Test the get_user() method."""
    user = ppms_connection.get_user('pumapy')
    print user.details()
    print ppms_user.details()
    assert user.details() == ppms_user.details()

    with pytest.raises(KeyError):
        ppms_connection.get_user('_hopefully_unknown_username_')

