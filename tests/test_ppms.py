"""Tests for the 'ppms' module."""

# pylint: disable-msg=fixme

# TODO: pylint for Python2 complains about redefining an outer scope when using
# pytest fixtures, this is supposed to be fixed in newer versions, so it should
# be checked again after migration to Python3 (see pylint issue #1535):
# pylint: disable-msg=redefined-outer-name
# pylint: disable-msg=invalid-name
# pylint: disable-msg=consider-iterating-dictionary
# pylint: disable-msg=len-as-condition
# pylint: disable-msg=protected-access

from __future__ import print_function

import logging
from datetime import datetime
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


############ connection ############

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

    # no API key and no cache path:
    with pytest.raises(RuntimeError):
        ppms.PpmsConnection(pumapyconf.PUMAPI_URL, api_key=None, cache=None)


############ users / groups ############

def test_get_user_ids(ppms_connection):
    """Test getting a list of user IDs from PPMS."""
    users = ppms_connection.get_user_ids(active=False)
    print users
    assert u'pumapy' in users

    users = ppms_connection.get_user_ids(active=True)
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


def test_get_users(ppms_connection, ppms_user, ppms_user_admin):
    """Test the get_users() method."""
    testusers = [ppms_user, ppms_user_admin]
    testusers_logins = [x.username for x in testusers]

    # first add some users to the connection object to avoid the
    # ultra-time-consuming requesting step:
    ppms_connection.update_users(user_ids=testusers_logins)

    # now ask the connection object for the (cached) user objects:
    users = ppms_connection.get_users()

    # check if the references match:
    for testuser in testusers:
        username = users[testuser.username].username
        print username
        assert testuser.username == username
        email = users[testuser.username].email
        print email
        assert testuser.email == email
        fullname = users[testuser.username].fullname
        assert testuser.fullname == fullname
        print "%s: %s (%s)" % (username, email, fullname)

        # check if the fullname_mapping has been updated correctly:
        assert fullname in ppms_connection.fullname_mapping
        assert ppms_connection.fullname_mapping[fullname] == testuser.username


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
        elif user.username == 'pumapy-deact':
            assert not user.active
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


def test_get_users_emails(ppms_connection,
                          user_details_raw,
                          user_admin_details_raw):
    """Test the get_users_emails() method."""
    users = [
        user_details_raw['login'],
        user_admin_details_raw['login'],
    ]
    print "users: %s" % users
    emails = ppms_connection.get_users_emails(users)
    print "emails: %s" % emails
    assert user_details_raw['email'] in emails
    assert user_admin_details_raw['email'] in emails


############ resources ############

def test_get_systems(ppms_connection, system_details_raw):
    """Test the get_systems() method."""
    systems = ppms_connection.get_systems()

    # check if we got some systems after all:
    assert len(systems) > 0

    print system_details_raw

    found = systems[int(system_details_raw['System id'])]
    print "Found system: %s" % found

    assert found.system_id == int(system_details_raw['System id'])
    assert found.localisation == system_details_raw['Localisation']
    assert found.system_type == system_details_raw['Type']


def test_get_systems_matching(ppms_connection, system_details_raw):
    """Test the get_systems_matching() method."""
    loc = system_details_raw['Localisation']
    name = system_details_raw['Name']

    # test with partial matches
    sys_ids = ppms_connection.get_systems_matching(loc[:3], [name[:6]])
    assert sys_ids == [int(system_details_raw['System id'])]

    # test with full matches
    sys_ids = ppms_connection.get_systems_matching(loc, [name])
    assert sys_ids == [int(system_details_raw['System id'])]

    # test with non-existing localisation
    sys_ids = ppms_connection.get_systems_matching('__non_existing__', [name])
    assert sys_ids == []

    # test with non-existing name
    sys_ids = ppms_connection.get_systems_matching(loc, ['__non_existing__'])
    assert sys_ids == []


############ system / user permissions ############

@pytest.mark.online
def test_get_users_with_access_to_system(ppms_connection,
                                         system_details_raw,
                                         user_details_raw,
                                         user_admin_details_raw):
    """Test the get_users_with_access_to_system() method."""
    sys_id = system_details_raw['System id']
    username = user_details_raw['login']
    username_adm = user_admin_details_raw['login']

    # get the list of usernames allowed to access the system:
    allowed_users = ppms_connection.get_users_with_access_to_system(sys_id)
    print allowed_users
    assert username in allowed_users
    assert username_adm in allowed_users


@pytest.mark.online
def test_system_booking_permissions(ppms_connection,
                                    system_details_raw,
                                    user_details_raw):
    """Test the set_system_booking_permissions() method."""
    sys_id = system_details_raw['System id']
    username = user_details_raw['login']

    with pytest.raises(KeyError):
        ppms_connection.set_system_booking_permissions('none', 42, 'X')

    success = ppms_connection.give_user_access_to_system('_invalidusr_', sys_id)
    assert not success

    success = ppms_connection.remove_user_access_from_system(username, sys_id)
    assert success

    allowed_users = ppms_connection.get_users_with_access_to_system(sys_id)
    print allowed_users
    assert username not in allowed_users

    success = ppms_connection.give_user_access_to_system(username, sys_id)
    assert success

    allowed_users = ppms_connection.get_users_with_access_to_system(sys_id)
    print allowed_users
    assert username in allowed_users


############ bookings ############

def test_get_booking(ppms_connection, system_details_raw):
    """Test the get_booking() method.

    Raises
    ------
    RuntimeError
        Raised in case no booking in PPMS could be found so one can be created
        manaully (the API doesn't provide a way to do this).
    """
    # test with a (hopefully) non-existing system ID:
    sys_id = 7777777
    assert ppms_connection.get_booking(sys_id) is None

    sys_id = system_details_raw['System id']
    # try to get the current booking, usually this will be None, but it depends
    # on the system state in PPMS, so we don't assert any result here but rather
    # run the code to see if it raises any exception (which it shouldn't)
    ppms_connection.get_booking(sys_id)
    # do the same using the get_current_booking() wrapper:
    ppms_connection.get_current_booking(sys_id)

    # this is a difficult one: in best case we would be able to create a
    # booking in PPMS, but the PUMAPI doesn't provide a way to do this - so the
    # only reasonable thing to do is to check if the 'next' booking is None and
    # give instructions to the tester (which will of course be useless in any
    # automated / CI scenario...)
    booking = ppms_connection.get_booking(sys_id, booking_type='next')
    if booking is None:
        raise RuntimeError('Please make sure system [%s] has at least one '
                           'booking in the future!' % sys_id)
    assert booking.system_id == int(sys_id)

    # do the same using the get_next_booking() wrapper:
    booking = ppms_connection.get_next_booking(sys_id)
    assert booking.system_id == int(sys_id)

    with pytest.raises(ValueError):
        ppms_connection.get_booking(sys_id, booking_type='invalid')


def test_get_running_sheet(ppms_connection, ppms_user, system_details_raw):
    """Test the `get_running_sheet` method.

    As it is currently impossible to create bookings through PUMAPI, we need to rely on
    either cached / mocked responses or for the selected bookings to actually be created
    manually through the PPMS web interface (which is why the test is using a day that
    is long time in the future so we do not have to adjust this test for too often).

    Still not quite optimal though.
    """
    # take an arbitrary date long time in the future (unfortunately the web interface
    # of PPMS doesn't let us go much beyond 10 years from now):
    date = '2028-12-24'
    # that day is expected to have four 60-minute-bookings, starting at the full hour:
    sessions_start = [9, 11, 13, 15]
    # use the start times to assemble a list of datetime tuples with start and end time
    # of the sessions on that day:
    sessions = list()
    for shour in sessions_start:
        sessions.append(
            [
                datetime.strptime("%sT%s" % (date, shour), r'%Y-%m-%dT%H'),
                datetime.strptime("%sT%s" % (date, shour + 1), r'%Y-%m-%dT%H')
            ]
        )
    # hard-coding the list would look like this:
    """Example:
    >>> sessions = [
    ...     [datetime(2028, 12, 24, 9, 0), datetime(2028, 12, 24, 10, 0)],
    ...     [datetime(2028, 12, 24, 11, 0), datetime(2028, 12, 24, 12, 0)],
    ...     [datetime(2028, 12, 24, 13, 0), datetime(2028, 12, 24, 14, 0)],
    ...     [datetime(2028, 12, 24, 15, 0), datetime(2028, 12, 24, 16, 0)],
    ... ]
    """

    def find_endtime(session_times, start_time):
        """Scan a list of tuples for the first elements, return the second on match.

        Parameters
        ----------
        session_times : list([datetime.datetime, datetime.datetime])
            A list of tuples of datetime objects.
        start_time : datetime.datetime
            The datetime object to be matched against the first element of the tuples.

        Returns
        -------
        datetime.datetime or None
            The second element of the first matching tuple, None when nothing matches.
        """
        for times in session_times:
            if start_time == times[0]:
                return times[1]
        return None

    day = datetime.strptime(date, r'%Y-%m-%d')
    testusers = [ppms_user]
    testusers_logins = [x.username for x in testusers]

    # first add some users to the connection object to avoid the
    # ultra-time-consuming requesting step:
    ppms_connection.update_users(user_ids=testusers_logins)

    for booking in ppms_connection.get_running_sheet('2', date=day):
        assert booking.system_id == int(system_details_raw['System id'])
        endtime = find_endtime(sessions, booking.starttime)
        assert endtime is not None
        print("matching booking end time: %s" % endtime)
        assert booking.endtime == endtime
        print(booking.__str__())


############ deprecated methods ############

def test__get_system_with_name(ppms_connection, system_details_raw):
    """Test the (deprecated) _get_system_with_name() method."""
    name = system_details_raw['Name']
    sys_id = ppms_connection._get_system_with_name(name)
    print "_get_system_with_name: %s" % sys_id
    assert sys_id == int(system_details_raw['System id'])


def test__get_machine_catalogue_from_system(ppms_connection,
                                            system_details_raw):
    """Test the (deprecated) _get_machine_catalogue_from_system() method."""
    name = system_details_raw['Name']

    # define a list of categories we are interested in:
    categories = ['VDI (Development)', 'VDI (CAD)', 'VDI (BigMemory)']

    # ask to which one the given machine belongs:
    cat = ppms_connection._get_machine_catalogue_from_system(name, categories)

    # expected be the first one:
    assert cat == categories[0]

    # test when no category is found:
    cat = ppms_connection._get_machine_catalogue_from_system(name,
                                                             categories[1:])
    assert cat == ''

    # test with a system name that doesn't exist
    name = '_invalid_pumapy_system_name_'
    cat = ppms_connection._get_machine_catalogue_from_system(name, categories)
    assert cat == ''
