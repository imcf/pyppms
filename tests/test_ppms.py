"""Tests for the 'ppms' module."""

# pylint: disable-msg=fixme
# pylint: disable-msg=protected-access

import logging
import os.path
from datetime import datetime
from shutil import rmtree, copytree

import pyppmsconf
import pytest
import requests.exceptions

from loguru import logger as log

from pyppms import ppms

# TODO: system ID is hard-coded here, so this will fail on any other instance!
__SYS_ID__ = 69


@pytest.fixture
def ppms_connection(caplog):
    """Establish a connection to a PPMS / PUMAPI instance."""
    print(
        "NOTE: some tests require either a *CACHED* response to be present or "
        "valid settings in `pyppmsconf.py` to talk to a real PUMAPI instance."
    )
    caplog.set_level(logging.DEBUG)
    cache_path = os.path.join(pyppmsconf.CACHE_PATH, "stage_0")
    conn = ppms.PpmsConnection(
        url=pyppmsconf.PUMAPI_URL,
        api_key=pyppmsconf.PPMS_API_KEY,
        timeout=pyppmsconf.TIMEOUT,
        cache=cache_path,
    )
    return conn


### common helper functions ###


def switch_cache_post_change(conn, suffix):
    """Update the connection's cache path to reflect changes to responses.

    This helper function switches the path used for caching the connection's
    responses to a different (post-update) location, which is required when
    running the same request (again) will result in a different response e.g.
    after updating PUMAPI's state (for example when adjusting booking
    permissions or similar).

    Parameters
    ----------
    conn : PpmsConnection
    suffix : str (or str-like)
    """
    new_path = os.path.join(pyppmsconf.CACHE_PATH, f"stage_{suffix}")
    log.debug("Switching response cache path to reflect a PPMS status change.")
    log.debug(f"New cache path: [{new_path}]")
    conn.cache_path = new_path


def switch_cache_mocks(conn, mocktype, message="<NOT SPECIFIED>"):
    """Update the connection's cache path to use mocked responses.

    Use mocked responses during tests to simulate various invalid replies from PUMAPI
    that will cause downstream errors during parsing etc.

    Parameters
    ----------
    conn : PpmsConnection
    mocktype : str
        Used to distinguish various types of mocks, e.g. ``key_error`` for responses
        that will trigger a `KeyError` exception in *pyppms*.
    message : str, optional
        An explanatory message that will be logged with switching the cache path.
    """
    new_path = os.path.join(pyppmsconf.MOCKS_PATH, mocktype)
    log.debug(f"Switching response cache path for reason:\n>>> {message} <<<")
    log.debug(f"New cache path: [{new_path}]")
    conn.cache_path = new_path


def logd(msg, *args):
    """Simple logging wrapper for log messages from test functions."""
    log.debug("\n>>> " + msg, *args)


############ connection ############


@pytest.mark.online
def test_ppmsconnection_online(ppms_connection):
    """Test establishing a PPMS connection."""
    assert ppms_connection.status["auth_state"] == "good"


def test_ppmsconnection(ppms_connection, capsys):
    """Instantiate a PpmsConnection object in online or offline mode.

    NOTE: this test either requires a *CACHED* response to be present or valid
    settings in `pyppmsconf.py` to talk to a real PUMAPI instance.
    """
    auth_state = ppms_connection.status["auth_state"]
    print(auth_state)
    assert auth_state in ["good", "NOT_TRIED"]


@pytest.mark.online
def test_ppmsconnection_fail_online():
    """Test how establishing connections to an online PUMAPI could fail."""
    # incomplete (short) API key:
    with pytest.raises(requests.exceptions.ConnectionError):
        ppms.PpmsConnection(pyppmsconf.PUMAPI_URL, api_key=pyppmsconf.PPMS_API_KEY[:5])

    # wrong API key (trailing characters):
    with pytest.raises(requests.exceptions.ConnectionError):
        ppms.PpmsConnection(
            pyppmsconf.PUMAPI_URL, pyppmsconf.PPMS_API_KEY + "appendixx"
        )


def test_ppmsconnection_fail(caplog):
    """Test various ways how establishing a connection could fail."""
    caplog.set_level(logging.DEBUG)

    logd("Testing with a wrong PUMAPI URL")
    with pytest.raises(requests.exceptions.ConnectionError):
        ppms.PpmsConnection("https://url.example", "dummykey")

    logd("Testing with no API key and no cache path")
    with pytest.raises(RuntimeError):
        ppms.PpmsConnection(pyppmsconf.PUMAPI_URL, api_key="", cache="")

    logd("Testing with a mocked auth response containing 'error'")
    with pytest.raises(requests.exceptions.ConnectionError):
        ppms.PpmsConnection(
            pyppmsconf.PUMAPI_URL,
            api_key="dummykey",
            cache=os.path.join(pyppmsconf.MOCKS_PATH, "auth_response_contains_error"),
        )

    logd("Testing with a mocked auth response having a non-standard response code")
    with pytest.raises(requests.exceptions.ConnectionError):
        ppms.PpmsConnection(
            pyppmsconf.PUMAPI_URL,
            api_key="dummykey",
            cache=os.path.join(pyppmsconf.MOCKS_PATH, "auth_wrong_status_code"),
        )
    # assert 0


############ users / groups ############


def test_get_user_ids(ppms_connection):
    """Test getting a list of user IDs from PPMS."""
    users = ppms_connection.get_user_ids(active=False)
    print(users)
    assert "pyppms" in users

    users = ppms_connection.get_user_ids(active=True)
    print(users)
    assert "pyppms" in users


def test_get_user_dict(ppms_connection, user_details_raw, user_admin_details_raw):
    """Test fetching details of a specific user."""
    print(f"Expected dict data: {user_details_raw}")
    details = ppms_connection.get_user_dict("pyppms")
    print(f"Retrieved dict data: {details}")
    assert user_details_raw == details

    print(f"Expected dict data: {user_admin_details_raw}")
    details = ppms_connection.get_user_dict("pyppms-adm")
    print(f"Retrieved dict data: {details}")
    assert user_admin_details_raw == details

    with pytest.raises(KeyError):
        ppms_connection.get_user_dict("invalidlogin")


def test_get_groups(ppms_connection):
    """Test getting a list of group IDs ("unitlogin") from PPMS."""
    groups = ppms_connection.get_groups()
    print(groups)
    assert "pyppms_group" in groups


def test_get_group(ppms_connection, group_details):
    """Test fetching details of a specific group."""
    print(f"Expected dict data (subset): {group_details}")
    details = ppms_connection.get_group("pyppms_group")
    print(f"Retrieved dict data: {details}")
    for key in group_details.keys():
        assert group_details[key] == details[key]

    with pytest.raises(KeyError):
        ppms_connection.get_group("invalid-unitlogin")


def test_get_user(ppms_connection, ppms_user, ppms_user_admin):
    """Test the get_user() method."""
    user = ppms_connection.get_user("pyppms")
    print(user.details())
    print(ppms_user.details())
    assert user.details() == ppms_user.details()

    user = ppms_connection.get_user("pyppms-adm")
    print(user.details())
    print(ppms_user_admin.details())
    assert user.details() == ppms_user_admin.details()

    with pytest.raises(KeyError):
        ppms_connection.get_user("invalidlogin")


def test_get_users(ppms_connection, ppms_user, ppms_user_admin):
    """Test the get_users() method."""
    testusers = [ppms_user, ppms_user_admin]
    testusers_logins = [x.username for x in testusers]

    logd(
        "Requesting users without pre-seeding the connection (WARNING: very "
        "time-consuming when no cache is present!)"
    )
    ppms_connection.get_users()

    logd("Adding users to the connection to avoid the requesting step")
    ppms_connection.update_users(user_ids=testusers_logins)

    logd("Asking the connection for the (pre-seeded / cached) users:")
    users = ppms_connection.get_users()

    # check if the references match:
    for testuser in testusers:
        username = users[testuser.username].username
        print(username)
        assert testuser.username == username
        email = users[testuser.username].email
        print(email)
        assert testuser.email == email
        fullname = users[testuser.username].fullname
        assert testuser.fullname == fullname
        print(f"{username}: {email} ({fullname})")

        # check if the fullname_mapping has been updated correctly:
        assert fullname in ppms_connection.fullname_mapping
        assert ppms_connection.fullname_mapping[fullname] == testuser.username


@pytest.mark.online
def test_get_user__skip_cache(caplog, ppms_connection, ppms_user):
    """Test if the `skip_cache` parameter has the desired effect.

    Steps:

    - switch to a test-specific cache location, make sure it's empty
    - request a user, check if this results in an on-line request
    - check if the user request has been cached locally
    - request the same user again, check if it is served from the cache
    - request the same user again now setting the `skip_cache` parameter to True, check
      if this results in an on-line request despite the cache is present
    """
    # switch to a test-specific cache location:
    switch_cache_post_change(ppms_connection, "test_get_users__forcerefresh")
    # wipe the cache
    rmtree(ppms_connection.cache_path, ignore_errors=True)
    cached = ppms_connection.cache_path + "/getuser/login--pyppms.txt"
    assert os.path.exists(cached) is False

    ppms_connection.get_user(ppms_user.username)
    assert ppms_connection.last_served_from_cache is False
    assert "Read intercepted response text from" not in caplog.text

    assert os.path.exists(cached) is True

    caplog.clear()
    ppms_connection.get_user(ppms_user.username)
    assert ppms_connection.last_served_from_cache is True
    assert "Read intercepted response text from" in caplog.text

    caplog.clear()
    ppms_connection.get_user(ppms_user.username, skip_cache=True)
    assert ppms_connection.last_served_from_cache is False
    assert "Read intercepted response text from" not in caplog.text

    # make sure to clean up the test-specific cache again:
    rmtree(ppms_connection.cache_path, ignore_errors=True)


def test_get_admins(ppms_connection, ppms_user_admin):
    """Test the get_admins() method."""
    admins = ppms_connection.get_admins()

    usernames = []
    admin_user = None
    for admin in admins:
        usernames.append(admin.username)
        if admin.username == "pyppms-adm":
            admin_user = admin

    print(usernames)
    assert "pyppms-adm" in usernames

    print(admin_user.details())
    assert admin_user.details() == ppms_user_admin.details()


def test_get_group_users(ppms_connection, ppms_user, ppms_user_admin):
    """Test the get_group_users() method."""
    # TODO: that's certainly not the nicest test, it really needs to be
    # refactored once the get_group_users() method returns a dict instead of a
    # list of user objects!
    members = ppms_connection.get_group_users("pyppms_group")
    for user in members:
        print(user.details())
        if user.username == "pyppms":
            assert user.details() == ppms_user.details()
        elif user.username == "pyppms-adm":
            assert user.details() == ppms_user_admin.details()
        elif user.username == "pyppms-deact":
            assert not user.active
        else:
            raise KeyError(f"Unexpected username: {user.username}")

    assert ppms_connection.get_group_users("") == []


def test_get_user_experience(ppms_connection):
    """Test the get_user_experience() method."""

    # check if we get some experience data after all:
    assert len(ppms_connection.get_user_experience()) > 0

    # check if a user has access to a specific system:
    systems = ppms_connection.get_user_experience(login="pyppms")
    sys_ids = []
    for system in systems:
        sys_ids.append(system["id"])
    assert str(__SYS_ID__) in sys_ids

    # check if a system is having a specific user with permission to access it:
    users = ppms_connection.get_user_experience(system_id=__SYS_ID__)
    usernames = []
    for user in users:
        usernames.append(user["login"])
    assert "pyppms" in usernames

    # check if filtering for user *and* system results in exactly one entry:
    assert len(ppms_connection.get_user_experience("pyppms", __SYS_ID__)) == 1


def test_get_users_emails(
    ppms_connection, user_details_raw, user_admin_details_raw, caplog
):
    """Test the get_users_emails() method."""
    # caplog.set_level(logging.DEBUG)
    logd("Testing users=None (WARNING: very time-consuming when no cache is present!)")
    ppms_connection.get_users_emails(users=None, active=True)

    logd("Testing with specific users")
    users = [user_details_raw["login"], user_admin_details_raw["login"]]
    print(f"users: {users}")
    emails = ppms_connection.get_users_emails(users)
    print(f"emails: {emails}")
    assert user_details_raw["email"] in emails
    assert user_admin_details_raw["email"] in emails

    logd("Testing with mock-response where some users have no email")
    switch_cache_mocks(ppms_connection, "get_users_emails__no_email")
    emails = ppms_connection.get_users_emails(users)
    raw_email = user_details_raw["email"]
    raw_login = user_details_raw["login"]
    print(f"address [{raw_email}] expected to NOT be in {emails}")
    assert raw_email not in emails
    assert f"no email for user [{raw_login}]" in caplog.text
    assert user_admin_details_raw["email"] in emails


############ resources ############


def test_get_systems(ppms_connection, system_details_raw):
    """Test the get_systems() method."""
    systems = ppms_connection.get_systems()

    # check if we got some systems after all:
    assert len(systems) > 0

    print(system_details_raw)

    found = systems[int(system_details_raw["System id"])]
    print(f"Found system: {found}")

    assert found.system_id == int(system_details_raw["System id"])
    assert found.localisation == system_details_raw["Localisation"]
    assert found.system_type == system_details_raw["Type"]

    # test refreshing the systems cache:
    systems = ppms_connection.get_systems(force_refresh=True)

    # check if we got some systems after all:
    assert len(systems) > 0


def test_update_systems(ppms_connection, caplog):
    """Test the get_systems() method."""
    caplog.set_level(logging.DEBUG)
    switch_cache_mocks(ppms_connection, "update_systems__broken_id")
    assert len(ppms_connection.systems) == 0
    ppms_connection.get_systems()
    # results should contain exaclty one system:
    assert len(ppms_connection.systems) == 1


def test_get_systems_matching(ppms_connection, system_details_raw):
    """Test the get_systems_matching() method."""
    loc = system_details_raw["Localisation"]
    name = system_details_raw["Name"]

    # test with partial matches
    sys_ids = ppms_connection.get_systems_matching(loc[:3], [name[:6]])
    assert sys_ids == [int(system_details_raw["System id"])]

    # test with full matches
    sys_ids = ppms_connection.get_systems_matching(loc, [name])
    assert sys_ids == [int(system_details_raw["System id"])]

    # test with non-existing localisation
    sys_ids = ppms_connection.get_systems_matching("__non_existing__", [name])
    assert sys_ids == []

    # test with non-existing name
    sys_ids = ppms_connection.get_systems_matching(loc, ["__non_existing__"])
    assert sys_ids == []


def test_get_systems_matching__raises(ppms_connection, system_details_raw):
    """Test get_systems_matching() with a wrong parameter type."""
    with pytest.raises(TypeError):
        ppms_connection.get_systems_matching("foo", "wrong-type")

    with pytest.raises(TypeError):
        ppms_connection.get_systems_matching("foo", "")


############ system / user permissions ############


def test_get_users_with_access_to_system(
    ppms_connection, system_details_raw, user_details_raw, user_admin_details_raw
):
    """Test the get_users_with_access_to_system() method."""
    sys_id = system_details_raw["System id"]
    username = user_details_raw["login"]
    username_adm = user_admin_details_raw["login"]

    logd("Testing 'getsysrights' for specific users on a fixed system")
    allowed_users = ppms_connection.get_users_with_access_to_system(sys_id)
    print(allowed_users)
    assert username in allowed_users
    assert username_adm in allowed_users

    logd("Testing 'getsysrights' response that is partially malformed")
    switch_cache_mocks(
        ppms_connection, "get_users_with_access_to_system__invalid_response"
    )
    with pytest.raises(ValueError):
        ppms_connection.get_users_with_access_to_system(sys_id)


def test_system_booking_permissions(ppms_connection):
    """Test the set_system_booking_permissions() method."""
    logd("Testing with an invalid permission level")
    with pytest.raises(KeyError):
        ppms_connection.set_system_booking_permissions("none", 42, "X")

    logd("Testing with an unexpected mock-response")
    switch_cache_mocks(ppms_connection, "setright_unexpected_response")
    success = ppms_connection.set_system_booking_permissions("someuser", 42, "N")
    assert not success


def test_user_access_to_system(ppms_connection, system_details_raw, user_details_raw):
    """Test the (give|remove)_user_access_to_system() methods."""
    sys_id = system_details_raw["System id"]
    username = user_details_raw["login"]

    logd("Testing with a non-existing user")
    success = ppms_connection.give_user_access_to_system("invalidlogin", sys_id)
    assert not success

    logd("Testing with an invalid system ID")
    success = ppms_connection.give_user_access_to_system(username, 0)
    assert not success

    logd("Testing removing permissions of a user to book the system")
    switch_cache_post_change(ppms_connection, 1)
    success = ppms_connection.remove_user_access_from_system(username, sys_id)
    assert success

    logd("Testing if the user is in the list of allowed ones (should NOT be)")
    allowed_users = ppms_connection.get_users_with_access_to_system(sys_id)
    print(allowed_users)
    assert username not in allowed_users

    logd("Testing to restore permissions of the user to book the system")
    switch_cache_post_change(ppms_connection, 2)
    success = ppms_connection.give_user_access_to_system(username, sys_id)
    assert success

    logd("Testing again if the user is in the list of allowed ones (should be now)")
    allowed_users = ppms_connection.get_users_with_access_to_system(sys_id)
    print(allowed_users)
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
    # test with a non-existing system ID:
    sys_id = 0
    assert ppms_connection.get_booking(sys_id) is None

    # test with an invalid system ID (string):
    sys_id = "invalid-id"
    assert ppms_connection.get_booking(sys_id) is None

    sys_id = system_details_raw["System id"]
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
    booking = ppms_connection.get_booking(sys_id, booking_type="next")
    if booking is None:
        raise RuntimeError(
            f"Make sure system [{sys_id}] has at least one booking in the future!"
        )
    assert booking.system_id == int(sys_id)

    # do the same using the get_next_booking() wrapper:
    booking = ppms_connection.get_next_booking(sys_id)
    assert booking.system_id == int(sys_id)

    with pytest.raises(ValueError):
        ppms_connection.get_booking(sys_id, booking_type="invalid")


def test_get_running_sheet(ppms_connection, system_details_raw):
    """Test the `get_running_sheet` method.

    As it is currently impossible to create bookings through PUMAPI, we need to rely on
    either cached / mocked responses or for the selected bookings to actually be created
    manually through the PPMS web interface (which is why the test is using a day that
    is long time in the future so we do not have to adjust this test for too often).

    Still not quite optimal though.
    """
    # take an arbitrary date long time in the future (unfortunately the web interface
    # of PPMS doesn't let us go much beyond 10 years from now):
    date = "2028-12-24"
    # that day is expected to have four 60-minute-bookings, starting at the full hour:
    sessions_start = [9, 11, 13, 15]
    # use the start times to assemble a list of datetime tuples with start and end time
    # of the sessions on that day:
    sessions = []
    for shour in sessions_start:
        ehour = shour + 1
        sessions.append(
            [
                datetime.strptime(f"{date}T{shour}", r"%Y-%m-%dT%H"),
                datetime.strptime(f"{date}T{ehour}", r"%Y-%m-%dT%H"),
            ]
        )
    # hard-coding the list would look like this:
    # pylint: disable-msg=pointless-string-statement
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

    day = datetime.strptime(date, r"%Y-%m-%d")

    logd("Testing runningsheet details for {}", date)
    for booking in ppms_connection.get_running_sheet("2", date=day):
        assert booking.system_id == int(system_details_raw["System id"])
        endtime = find_endtime(sessions, booking.starttime)
        assert endtime is not None
        print(f"matching booking end time: {endtime}")
        assert booking.endtime == endtime
        print(str(booking))

    logd("Testing fullname that cannot be mapped to a user")
    switch_cache_mocks(ppms_connection, "runningsheet_single_unknown_fullname")
    assert len(ppms_connection.get_running_sheet("2", date=day)) == 2


def test_get_running_sheet_fail(ppms_connection):
    """Test cases where no runningsheet can be assembled from the responses."""
    date = "2028-12-24"
    day = datetime.strptime(date, r"%Y-%m-%d")

    switch_cache_mocks(
        ppms_connection,
        "runningsheet_key_error",
        "Testing with mock-response that is missing the key 'User'",
    )
    with pytest.raises(KeyError):
        ppms_connection.get_running_sheet("2", date=day)

    switch_cache_mocks(
        ppms_connection,
        "runningsheet_invalid_multiline_response",
        "using mock that fails parsing, expected result is an empty list of bookings",
    )
    assert ppms_connection.get_running_sheet("2", date=day) == []


############ cache ############


def test_flush_cache(ppms_connection, caplog, tmp_path):
    """Test flushing the on-disk PyPPMS cache.

    - Make sure the temporary test-directory exists but doesn't contain a cache yet.
    - Copy over one of the cache directories provided with the tests.
    - Make sure the test-directory *does* contain a cache now.
    - Update the connection object's `cache_path` to point to the test location.
    - Trigger the `flush_cache()` method.
    - Verify the cache has been removed from the test-directory.
    """
    orig_cache_path = os.path.join(pyppmsconf.CACHE_PATH, "stage_1")
    fresh_cache_path = tmp_path / "pyppms_cache"

    assert os.path.exists(tmp_path)
    assert os.path.exists(orig_cache_path)

    assert not os.path.exists(fresh_cache_path)
    copytree(orig_cache_path, fresh_cache_path)
    assert os.path.exists(fresh_cache_path)
    log.info(f"Cache path created: {fresh_cache_path}")

    ppms_connection.cache_path = fresh_cache_path
    log.info(f"Updated connection cache path: {fresh_cache_path}")
    ppms_connection.flush_cache()
    log.info(f"Flushed connection cache path: {fresh_cache_path}")
    assert not os.path.exists(fresh_cache_path)


def test_flush_cache__keep_users(ppms_connection, caplog, tmp_path):
    """Test flushing the on-disk PyPPMS cache while keeping the user details.

    - Make sure the temporary test-directory exists but doesn't contain a cache yet.
    - Create the cache directory there.
    - Update the connection object's `cache_path` to point to the test location.
    - Copy over the subdirs listed in `to_keep` and `to_flush` from the cache provided
      with the tests.
    - Make sure the copied directories exist at the test-cache location.
    - Trigger the `flush_cache(keep_users=True)` method.
    - Verify the subdirs in `to_keep` have been retained at the test-directory.
    - Verify the subdirs in `to_flush` have been removed from the test-directory.
    """
    to_keep = ["getuser"]
    to_flush = ["auth", "getgroups", "getusers", "getbooking"]

    orig_cache_root = os.path.join(pyppmsconf.CACHE_PATH, "stage_0")
    fresh_cache_path = tmp_path / "pyppms_cache"

    assert os.path.exists(tmp_path)
    assert os.path.exists(orig_cache_root)

    assert not os.path.exists(fresh_cache_path)
    fresh_cache_path.mkdir()
    assert os.path.exists(fresh_cache_path)
    log.info(f"Cache path created: {fresh_cache_path}")

    ppms_connection.cache_path = fresh_cache_path
    log.info(f"Updated connection cache path: {fresh_cache_path}")

    for subdir in to_keep + to_flush:
        srcdir = os.path.join(orig_cache_root, subdir)
        tgt_path = fresh_cache_path / subdir
        assert not os.path.exists(tgt_path)
        copytree(srcdir, tgt_path)
        log.info(f"Copied [{subdir}] to [{tgt_path}]")
        assert os.path.exists(tgt_path)

    ppms_connection.flush_cache(keep_users=True)

    for subdir in to_keep:
        tgt_path = fresh_cache_path / subdir
        log.debug(f"Verifying directory has been KEPT: {tgt_path}")
        assert os.path.exists(tgt_path)

    for subdir in to_flush:
        tgt_path = fresh_cache_path / subdir
        log.debug(f"Verifying directory has been FLUSHED: {tgt_path}")
        assert not os.path.exists(tgt_path)


@pytest.mark.online
def test_flush_cache__keep_users__request_new(ppms_connection, caplog, tmp_path):
    """Test flush_cache() with `keep_users=True` and request a new user after.

    This test has a huge overlap to the `test_flush_cache__keep_users()` one
    (that works offline, unlike this one) with the main difference being that
    after flushing the cache, the cached details of a known user are removed and
    then exactly those details are requested. This will trigger an online
    request for that user while requests for previously existing (cached and
    preserved by the `keep_users` option set to `True`) users will be served
    directly from the cache.

    - Make sure the temporary test-directory exists and has no cache inside.
    - Create the cache directory there.
    - Update the connection object's `cache_path` to point to the test location.
    - Copy over the subdirs listed in `to_keep` and `to_flush` from the cache
      provided with the tests.
    - Trigger the `flush_cache(keep_users=True)` method.
    - Simulate a new user in PPMS that is not yet cached locally:
      - Remove a specific file of previously cached user details from the
        `getuser` cache.
      -
      - Then copy back the `getusers` cache which contains the list of usernames
        known to PPMS, which will include the username whose details have been
        removed explicitly in the previous step.
    - Request details of the preserved user, verify they're being served from
      the cache by inspecting the log messages.
    - Request details of the "pseudo-new" user, verify they're triggering an
      on-line request to PUMAPI.
    """
    to_keep = ["getuser"]
    to_flush = ["auth", "getgroups", "getusers", "getbooking"]

    orig_cache_root = os.path.join(pyppmsconf.CACHE_PATH, "stage_0")
    fresh_cache_path = tmp_path / "pyppms_cache"

    assert os.path.exists(orig_cache_root)

    assert not os.path.exists(fresh_cache_path)
    fresh_cache_path.mkdir()
    assert os.path.exists(fresh_cache_path)
    log.info(f"Cache path created: {fresh_cache_path}")

    ppms_connection.cache_path = fresh_cache_path
    log.info(f"Updated connection cache path: {fresh_cache_path}")

    for subdir in to_keep + to_flush:
        srcdir = os.path.join(orig_cache_root, subdir)
        tgt_path = fresh_cache_path / subdir
        assert not os.path.exists(tgt_path)
        copytree(srcdir, tgt_path)
        log.info(f"Copied [{subdir}] to [{tgt_path}]")
        assert os.path.exists(tgt_path)

    ppms_connection.flush_cache(keep_users=True)

    new_user_name = "pyppms-adm"  # simulated "new" user
    old_user_name = "pyppms"  # previously existing, cached user (preserved)

    log.info(f"Removing preserved user-cache for [{new_user_name}]...")
    new_user_cache = fresh_cache_path / "getuser" / f"login--{new_user_name}.txt"
    old_user_cache = fresh_cache_path / "getuser" / f"login--{old_user_name}.txt"
    assert os.path.isfile(new_user_cache)
    os.unlink(new_user_cache)
    assert not os.path.exists(new_user_cache)
    assert os.path.exists(old_user_cache)

    log.info("Restoring cache of existing user names...")
    users_list = os.path.join(orig_cache_root, "getusers")
    tgt_path = fresh_cache_path / "getusers"
    copytree(users_list, tgt_path)
    assert os.path.exists(tgt_path)
    log.info(f"Restored user names cache to [{tgt_path}].")

    log.info(f"Requesting details from PUMAPI for cached user [{old_user_name}]")
    ppms_connection.get_user(old_user_name)
    assert ppms_connection.last_served_from_cache is True
    # assert "No cache hit" not in caplog.text  # served from the cache

    log.info(f"Requesting details from PUMAPI for 'new' user [{new_user_name}]")
    ppms_connection.get_user(new_user_name)
    assert ppms_connection.last_served_from_cache is False
    # assert "No cache hit" in caplog.text  # requires an on-line request
    assert os.path.exists(new_user_cache)
