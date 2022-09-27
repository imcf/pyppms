"""Core connection module for the PUMAPI communication."""

# pylint: disable-msg=dangerous-default-value

# NOTE: the "pyppms" package is simply a wrapper for the existing API, so we can't make
#       any design decisions here - hence it is pointless to complain about the number
#       of instance attributes, public methods or other stuff:
# pylint: disable-msg=too-many-instance-attributes
# pylint: disable-msg=too-many-public-methods

import logging
import os
import os.path
from io import open

import requests

from .common import dict_from_single_response, parse_multiline_response
from .user import PpmsUser
from .system import PpmsSystem
from .booking import PpmsBooking


LOG = logging.getLogger(__name__)


class PpmsConnection:

    """Connection object to communicate with a PPMS instance.

    Attributes
    ----------
    url : str
        The URL of the PUMAPI instance.
    api_key : str
        The API key used for authenticating against the PUMAPI.
    timeout : float
        The timeout value used in the ``requests.post`` calls.
    cache_path : str
        A path to a local directory used for caching responses.
    users : dict
        A dict with usernames as keys, mapping to the related
        :py:class:`pyppms.user.PpmsUser` object, serves as a cache during the object's
        lifetime (can be empty if no calls to :py:meth:`get_user()` have been done yet).
    fullname_mapping : dict
        A dict mapping a user's *fullname* ("``<LASTNAME> <FIRSTNAME>``") to the
        corresponding username. Entries are filled in dynamically by the
        :py:meth:`get_user()` method.
    systems
        A dict with system IDs as keys, mapping to the related
        :py:class:`pyppms.system.PpmsSystem` object. Serves as a cache during the
        object's lifetime (can be empty if no calls to the :py:meth:`get_systems()` have
        been done yet).
    status : dict
        A dict with keys ``auth_state``, ``auth_response`` and
        ``auth_httpstatus``
    """

    def __init__(self, url, api_key, timeout=10, cache=""):
        """Constructor for the PPMS connection object.

        Open a connection to the PUMAPI defined in `url` and try to authenticate
        against it using the given API key (or use cache-only mode if key is an
        empty string). If an optional path to a caching location is specified,
        responses will be read from that location unless no matching file can be
        found there, in which case an on-line request will be done (with the
        response being saved to the cache path).

        Parameters
        ----------
        url : str
            The URL of the PUMAPI to connect to.
        api_key : str
            The API key to use for authenticating against the PUMAPI. If
            specified as '' authentication will be skipped and the connection is
            running in cache-only (local) mode.
        timeout : float, optional
            How many seconds to wait for the PUMAPI server to send a response
            before giving up, by default 10.
        cache : str, optional
            A path to a local directory for caching responses from PUMAPI in
            individual text files. Useful for testing and for speeding up
            slow requests like 'getusers'. By default empty, which will result
            in no caching being done.

        Raises
        ------
        requests.exceptions.ConnectionError
            Raised in case authentication fails.
        """
        self.url = url
        self.api_key = api_key
        self.timeout = timeout
        self.users = {}
        self.fullname_mapping = {}
        self.systems = {}
        self.status = {
            "auth_state": "NOT_TRIED",
            "auth_response": None,
            "auth_httpstatus": -1,
        }
        self.cache_path = cache

        # run in cache-only mode (e.g. for testing or off-line usage) if no API
        # key has been specified, skip authentication then:
        if api_key != "":
            self.__authenticate()
        elif cache == "":
            raise RuntimeError(
                "Neither API key nor cache path given, at least one is required!"
            )

    def __authenticate(self):
        """Try to authenticate to PPMS using the `auth` request.

        Raises
        ------
        requests.exceptions.ConnectionError
            Raised in case authentication failed for any reason.
        """
        LOG.debug(
            "Attempting authentication against %s with key [%s...%s]",
            self.url,
            self.api_key[:2],
            self.api_key[-2:],
        )
        self.status["auth_state"] = "attempting"
        response = self.request("auth")
        LOG.debug("Authenticate response: %s", response.text)
        self.status["auth_response"] = response.text
        self.status["auth_httpstatus"] = response.status_code

        # NOTE: an unauthorized request has already been caught be the request() method
        # above. Our legacy code was additionally testing for 'error' in the response
        # text - however, it is unclear if PUMAPI ever returns this:
        if "error" in response.text.lower():
            self.status["auth_state"] = "FAILED-ERROR"
            msg = f"Authentication failed with an error: {response.text}"
            LOG.error(msg)
            raise requests.exceptions.ConnectionError(msg)

        status_ok = requests.codes.ok  # pylint: disable-msg=no-member

        if response.status_code != status_ok:
            # NOTE: branch excluded from coverage as we don't have a known way
            # to produce such a response from the API
            LOG.warning(
                "Unexpected combination of response [%s] and status code [%s], it's "
                "unclear if authentication succeeded (assuming it didn't)",
                response.status_code,
                response.text,
            )
            self.status["auth_state"] = "FAILED-UNKNOWN"

            msg = (
                f"Authenticating against {self.url} with key "
                f"[{self.api_key[:2]}...{self.api_key[-2:]}] FAILED!"
            )
            LOG.error(msg)
            raise requests.exceptions.ConnectionError(msg)

        LOG.info("Authentication succeeded, response=[%s]", response.text)
        LOG.debug("HTTP Status: %s", response.status_code)
        self.status["auth_state"] = "good"

    def request(self, action, parameters={}, skip_cache=False):
        """Generic method to submit a request to PPMS and return the result.

        This convenience method deals with adding the API key to a given
        request, submitting it to the PUMAPI and checking the response for some
        specific keywords indicating an error.

        Parameters
        ----------
        action : str
            The command to be submitted to the PUMAPI.
        parameters : dict, optional
            A dictionary with additional parameters to be submitted with the
            request.
        skip_cache : bool, optional
            If set to True the request will NOT be served from the local cache,
            independent whether a matching response file exists there, by
            default False.

        Returns
        -------
        requests.Response
            The response object created by posting the request.

        Raises
        ------
        requests.exceptions.ConnectionError
            Raised in case the request is not authorized.
        """
        req_data = {"action": action, "apikey": self.api_key}
        req_data.update(parameters)
        # LOG.debug("Request parameters: %s", parameters)

        response = None
        read_from_cache = False
        try:
            if skip_cache:  # pragma: no cover
                raise LookupError("Skipping the cache has been requested")
            response = self.__intercept_read(req_data)
            read_from_cache = True
        except LookupError as err:
            LOG.debug("Doing an on-line request: %s", err)
            response = requests.post(self.url, data=req_data, timeout=self.timeout)

        # store the response if it hasn't been read from the cache before:
        if not read_from_cache:  # pragma: no cover
            self.__intercept_store(req_data, response)

        # NOTE: the HTTP status code returned is always `200` even if
        # authentication failed, so we need to check the actual response *TEXT*
        # to figure out if we have succeeded:
        if "request not authorized" in response.text.lower():
            self.status["auth_state"] = "FAILED"
            msg = f"Not authorized to run action `{req_data['action']}`"
            LOG.error(msg)
            raise requests.exceptions.ConnectionError(msg)

        return response

    def __interception_path(self, req_data, create_dir=False):
        """Derive the path for a local cache file from a request's parameters.

        Parameters
        ----------
        req_data : dict
            The request's parameters, used to derive the name of the cache file.
        create_dir : bool, optional
            If set to True the cache directory will be created if necessary.
            Useful when adding responses to the cache. By default False.

        Returns
        -------
        str
            The full path to a file name identified by all parameters of the
            request (except credentials like 'apikey').
        """
        action = req_data["action"]
        intercept_dir = os.path.join(self.cache_path, action)
        if create_dir and not os.path.exists(intercept_dir):  # pragma: no cover
            try:
                os.makedirs(intercept_dir)
                LOG.debug("Created dir to store response: %s", intercept_dir)
            except Exception as err:  # pylint: disable-msg=broad-except
                LOG.warning("Failed creating [%s]: %s", intercept_dir, err)
                return None

        signature = ""
        # different python versions are returning dict items in different order, so
        # simply iterating over them will not always produce the same result - hence we
        # build up a sorted list of keys first and use that one then:
        keylist = list(req_data.keys())
        keylist.sort()
        for key in keylist:
            if key in ["action", "apikey"]:
                continue
            signature += f"__{key}--{req_data[key]}"
        if signature == "":
            signature = "__response"
        signature = signature[2:] + ".txt"
        intercept_file = os.path.join(intercept_dir, signature)
        return intercept_file

    def __intercept_read(self, req_data):
        """Try to read a cached response from a local file.

        Parameters
        ----------
        req_data : dict
            The request's parameters, used to derive the name of the cache file.

        Returns
        -------
        PseudoResponse
            The response text read from the cache file wrapped in a
            PseudoResponse object, or None in case no matching file was found in
            the local cache.

        Raises
        ------
        LookupError
            Raised in case no cache path has been set or no cache file matching
            the request parameters could be found in the cache.
        """

        # pylint: disable-msg=too-few-public-methods
        class PseudoResponse:
            """Dummy response object with attribs 'text' and 'status_code'."""

            def __init__(self, text, status_code):
                self.text = text
                self.status_code = int(status_code)

        if self.cache_path == "":
            raise LookupError("No cache path configured")

        intercept_file = self.__interception_path(req_data, create_dir=False)
        if not os.path.exists(intercept_file):  # pragma: no cover
            raise LookupError(f"No cache hit for [{intercept_file}]")

        with open(intercept_file, "r", encoding="utf-8") as infile:
            text = infile.read()
        LOG.debug("Read intercepted response text from [%s]", intercept_file)

        status_code = 200
        status_file = os.path.splitext(intercept_file)[0] + "_status-code.txt"
        if os.path.exists(status_file):
            with open(status_file, "r", encoding="utf-8") as infile:
                status_code = infile.read()
            LOG.debug("Read intercepted response status code from [%s]", status_file)
        return PseudoResponse(text, status_code)

    def __intercept_store(self, req_data, response):  # pragma: no cover
        """Store the response in a local cache file named after the request.

        Parameters
        ----------
        req_data : dict
            The request's parameters, used to derive the name of the cache file
            so it can be matched later when running the same request again.
        response : requests.Response
            The response object to store in the local cache.
        """
        # NOTE: this method is excluded from coverage measurements as it can only be
        # triggered when testing in online mode with at least one request not being
        # served from the cache (which is orthogonal to off-line testing)
        if self.cache_path == "":
            return

        intercept_file = self.__interception_path(req_data, create_dir=True)
        if not intercept_file:
            # FIXME: switch to loguru, turn into a trace-level message:
            LOG.debug("Not storing intercepted results in cache.")
            return

        try:
            with open(intercept_file, "w", encoding="utf-8") as outfile:
                outfile.write(response.text)
            LOG.debug(
                "Wrote response text to [%s] (%s lines)",
                intercept_file,
                len(response.text.splitlines()),
            )
        except Exception as err:  # pylint: disable-msg=broad-except
            LOG.error("Storing response text in [%s] failed: %s", intercept_file, err)
            LOG.error("Response text was:\n--------\n%s\n--------", response.text)

    def get_admins(self):
        """Get all PPMS administrator users.

        Returns
        -------
        list(pyppms.user.PpmsUser)
            A list with PpmsUser objects that are PPMS administrators.
        """
        response = self.request("getadmins")

        admins = response.text.splitlines()
        users = []
        for username in admins:
            user = self.get_user(username)
            users.append(user)
        LOG.debug("%s admins in the PPMS database: %s", len(admins), ", ".join(admins))
        return users

    def get_booking(self, system_id, booking_type="get"):
        """Get the current or next booking of a system.

        WARNING: if the next booking is requested but it is too far in the future,
        PUMAPI silently ignores it - the response is identical to a system that has no
        future bookings and there is no error reported either. Currently it is unclear
        where the cutoff is (e.g. lookups for a booking that is two years from now still
        work fine, but a booking in about 10 years is silently skipped).

        Parameters
        ----------
        system_id : int or int-like
            The ID of the system in PPMS.
        booking_type : {'get', 'next'}, optional
            The type of booking to request, one of `get` (requesting the
            currently running booking) and `next` (requesting the next upcoming
            booking), by default `get`.

        Returns
        -------
        pyppms.booking.PpmsBooking or None
            The booking object, or None if there is no booking for the system or the
            request is refused by PUMAPI (e.g. "not authorized").

        Raises
        ------
        ValueError
            Raised if the specified `booking_type` is invalid.
        """
        valid = ["get", "next"]
        if booking_type not in valid:
            raise ValueError(
                f"Value for 'booking_type' ({booking_type}) not in {valid}!"
            )

        try:
            response = self.request(booking_type + "booking", {"id": system_id})
        except requests.exceptions.ConnectionError:
            LOG.error("Requesting booking status for system %s failed!", system_id)
            return None

        desc = "any future bookings"
        if booking_type == "get":
            desc = "a currently active booking"
        if not response.text.strip():
            LOG.debug("System [%s] doesn't have %s", system_id, desc)
            return None

        return PpmsBooking(response.text, booking_type, system_id)

    def get_current_booking(self, system_id):
        """Wrapper for `get_booking()` with 'booking_type' set to 'get'."""
        return self.get_booking(system_id, "get")

    def get_group(self, group_id):
        """Fetch group details from PPMS and create a dict from them.

        Parameters
        ----------
        group_id : str
            The group's identifier in PPMS, called 'unitlogin' there.

        Returns
        -------
        dict
            A dict with the group details, keys being derived from the header
            line of the PUMAPI response, values from the data line.
        """
        response = self.request("getgroup", {"unitlogin": group_id})
        LOG.debug("Group details returned by PPMS (raw): %s", response.text)

        if not response.text:
            msg = f"Group [{group_id}] is unknown to PPMS"
            LOG.error(msg)
            raise KeyError(msg)

        details = dict_from_single_response(response.text)

        LOG.debug("Details of group %s: %s", group_id, details)
        return details

    def get_group_users(self, unitlogin):
        """Get all members of a group in PPMS.

        Parameters
        ----------
        unitlogin : str
            The group's login ("unique login or id" in the PPMS web interface).

        Returns
        -------
        list(pyppms.user.PpmsUser)
            A list with PpmsUser objects that are members of this PPMS group.
        """
        response = self.request("getgroupusers", {"unitlogin": unitlogin})

        members = response.text.splitlines()
        users = []
        for username in members:
            user = self.get_user(username)
            users.append(user)
        LOG.debug(
            "%s members in PPMS group [%s]: %s",
            len(members),
            unitlogin,
            ", ".join(members),
        )
        return users

    def get_groups(self):
        """Get a list of all groups in PPMS.

        Returns
        -------
        list(str)
            A list with the group identifiers in PPMS.
        """
        response = self.request("getgroups")

        groups = response.text.splitlines()
        LOG.debug("%s groups in the PPMS database: %s", len(groups), ", ".join(groups))
        return groups

    def get_next_booking(self, system_id):
        """Wrapper for `get_booking()` with 'booking_type' set to 'next'."""
        return self.get_booking(system_id, "next")

    def get_running_sheet(self, core_facility_ref, date, ignore_uncached_users=False):
        """Get the running sheet for a specific day on the given facility.

        The so-called "running-sheet" consists of all bookings / reservations of
        a facility on a specifc day.

        WARNING: PUMAPI doesn't return a proper unique user identifier with the
        'getrunningsheet' request, instead the so called "full name" is given to
        identify the user - unfortunately this can lead to ambiguities as
        multiple different accounts can have the same full name.

        Parameters
        ----------
        core_facility_ref : int or int-like
            The core facility ID for PPMS.
        date : datetime.datetime
            The date to request the running sheet for, e.g. ``datetime.now()`` or
            similar. Note that only the date part is relevant, time will be ignored.
        ignore_uncached_users : bool, optional
            If set to `True` any booking for a user that is not present in the instance
            attribuge `fullname_mapping` will be ignored in the resulting list.

        Returns
        -------
        list(pyppms.booking.PpmsBooking)
            A list with `PpmsBooking` objects for the given day. Empty in case
            there are no bookings or parsing the response failed.
        """
        bookings = []
        parameters = {
            "plateformid": f"{core_facility_ref}",
            "day": date.strftime("%Y-%m-%d"),
        }
        LOG.debug("Requesting runningsheet for %s", parameters["day"])
        response = self.request("getrunningsheet", parameters)
        try:
            entries = parse_multiline_response(response.text, graceful=False)
        except Exception as err:  # pylint: disable-msg=broad-except
            LOG.error("Parsing runningsheet details failed: %s", err)
            # NOTE: in case no future bookings exist the response will be empty!
            LOG.error("Possibly the runningsheet is empty as no bookings exist?")
            LOG.debug("Runningsheet PUMPAI response was: %s", response.text)
            return bookings

        for entry in entries:
            full = entry["User"]
            if full not in self.fullname_mapping:
                if ignore_uncached_users:
                    LOG.debug("Ignoring booking for uncached user [%s]", full)
                    continue

                LOG.info("Booking for an uncached user (%s) found!", full)
                self.update_users()

            if full not in self.fullname_mapping:
                LOG.error("PPMS doesn't seem to know user [%s], skipping", full)
                continue

            LOG.info(
                "Booking for user '%s' (%s) found", self.fullname_mapping[full], full
            )
            booking = PpmsBooking.from_runningsheet(
                entry,
                self._get_system_with_name(entry["Object"]),
                self.fullname_mapping[full],
                date,
            )
            bookings.append(booking)

        return bookings

    def get_systems(self, force_refresh=False):
        """Get a dict with all systems in PPMS.

        Returns
        -------
        dict(pyppms.system.PpmsSystem)
            A dict with `PpmsSystem` objects parsed from the PUMAPI response where
            the system ID (int) is used as the dict's key. If parsing a system
            fails for any reason, the system is skipped entirely.
        """
        if self.systems and not force_refresh:
            LOG.debug("Using cached details for %s systems", len(self.systems))
        else:
            self.update_systems()

        return self.systems

    def get_systems_matching(self, localisation, name_contains):
        """Query PPMS for systems with a specific location and name.

        This method assembles a list of PPMS system IDs whose "localisation"
        (room) field matches a given string and where the system name contains
        at least one of the strings given as the `name_contains` parameter.

        Parameters
        ----------
        localisation : str
            A string that the system's "localisation" (i.e. the "Room" field in
            the PPMS web interface) has to match.
        name_contains : list(str)
            A list of valid names (categories) of which the system's name has to
            match at least one for being included. Supply an empty list for
            skipping this filter.

        Returns
        -------
        list(int)
            A list with PPMS system IDs matching all of the given criteria.
        """
        loc = localisation
        loc_desc = f"with location matching [{localisation}]"
        if localisation == "":
            loc_desc = "(no location filter given)"

        LOG.info(
            "Querying PPMS for systems %s, name matching any of %s",
            loc_desc,
            name_contains,
        )
        system_ids = []
        systems = self.get_systems()
        for sys_id, system in systems.items():
            if loc.lower() not in str(system.localisation).lower():
                LOG.debug(
                    "System [%s] location (%s) is NOT matching (%s), ignoring",
                    system.name,
                    system.localisation,
                    loc,
                )
                continue

            # LOG.debug('System [%s] is matching location [%s], checking if '
            #           'the name is matching any of the valid pattern %s',
            #           system.name, loc, name_contains)
            for valid_name in name_contains:
                if valid_name in system.name:
                    LOG.debug("System [%s] matches all criteria", system.name)
                    system_ids.append(sys_id)
                    break

            # if sys_id not in system_ids:
            #     LOG.debug('System [%s] does NOT match a valid name: %s',
            #               system.name, name_contains)

        LOG.info("Found %s bookable systems %s", len(system_ids), loc_desc)
        LOG.debug("IDs of matching bookable systems %s: %s", loc_desc, system_ids)
        return system_ids

    def get_user(self, login_name, skip_cache=False):
        """Fetch user details from PPMS and create a PpmsUser object from it.

        Parameters
        ----------
        login_name : str
            The user's PPMS login name.
        skip_cache : bool, optional
            Passed as-is to the :py:meth:`request()` method

        Returns
        -------
        pyppms.user.PpmsUser
            The user object created from the PUMAPI response. The object will be
            additionally stored in the self.users dict using the login_name as
            the dict's key.

        Raises
        ------
        KeyError
            Raised if the user doesn't exist in PPMS.
        """
        response = self.request("getuser", {"login": login_name}, skip_cache=skip_cache)

        if not response.text:
            msg = f"User [{login_name}] is unknown to PPMS"
            LOG.error(msg)
            raise KeyError(msg)

        user = PpmsUser(response.text)
        self.users[user.username] = user  # update / add to the cached user objs
        self.fullname_mapping[user.fullname] = user.username
        return user

    def get_user_dict(self, login_name, skip_cache=False):
        """Get details on a given user from PPMS.

        Parameters
        ----------
        login_name : str
            The PPMS account / login name of the user to query.
        skip_cache : bool, optional
            Passed as-is to the :py:meth:`request()` method

        Returns
        -------
        dict
            A dict with the user details returned by the PUMAPI.

        Example
        -------
        >>> conn.get_user_dict('pyppms')
        ... {
        ...     u'active': True,
        ...     u'affiliation': u'',
        ...     u'bcode': u'',
        ...     u'email': u'pyppms@python-facility.example',
        ...     u'fname': u'PumAPI',
        ...     u'lname': u'Python',
        ...     u'login': u'pyppms',
        ...     u'mustchbcode': False,
        ...     u'mustchpwd': False',
        ...     u'phone': u'+98 (76) 54 3210',
        ...     u'unitlogin': u'pyppms'
        ... }

        Raises
        ------
        KeyError
            Raised in case the user account is unknown to PPMS.
        ValueError
            Raised if the user details can't be parsed from the PUMAPI response.
        """
        response = self.request("getuser", {"login": login_name}, skip_cache=skip_cache)

        if not response.text:
            msg = f"User [{login_name}] is unknown to PPMS"
            LOG.error(msg)
            raise KeyError(msg)

        # EXAMPLE:
        # response.text = (
        #     u'login,lname,fname,email,'
        #     u'phone,bcode,affiliation,unitlogin,mustchpwd,mustchbcode,'
        #     u'active\r\n'
        #     u'"pyppms","Python","PumAPI","pyppms@python-facility.example",'
        #     u'"+98 (76) 54 3210","","","pyppms",false,false,'
        #     u'true\r\n'
        # )
        details = dict_from_single_response(response.text)
        LOG.debug("Details for user [%s]: %s", login_name, details)
        return details

    def get_user_experience(self, login=None, system_id=None):
        """Get user experience ("User rights") from PPMS.

        Parameters
        ----------
        login : str, optional
            An optional login name to request the experience / permissions for,
            by default None
        system_id : int, optional
            An optional system ID to request the experience / permissions for,
            by default None

        Returns
        -------
        list(dict)
            A list with dicts parsed from the user experience response.
        """
        data = {}
        if login is not None:
            data["login"] = login
        if system_id is not None:
            data["id"] = system_id
        response = self.request("getuserexp", parameters=data)

        parsed = parse_multiline_response(response.text)
        LOG.debug(
            "Received %s experience entries for filters [user:%s] and [id:%s]",
            len(parsed),
            login,
            system_id,
        )
        return parsed

    def get_user_ids(self, active=False):
        """Get a list with all user IDs in the PPMS system.

        Parameters
        ----------
        active : bool, optional
            Request only users marked as active in PPMS, by default False.
            NOTE: "active" is a tri-state parameter in PPMS: "true", "false"
            or empty!

        Returns
        -------
        list
            A list of all (or active-only) user IDs in PPMS.
        """
        # TODO: describe format of returned list and / or give an example!
        parameters = {}
        if active:
            parameters["active"] = "true"

        response = self.request("getusers", parameters)

        users = response.text.splitlines()
        active_desc = "active " if active else ""
        LOG.info("%s %susers in the PPMS database", len(users), active_desc)
        LOG.debug(", ".join(users))
        return users

    def get_users(self, force_refresh=False):
        """Get user objects for all (or cached) PPMS users.

        Parameters
        ----------
        force_refresh : bool, optional
            Re-request information from PPMS even if user details have been
            cached locally before, by default False.

        Returns
        -------
        dict(pyppms.user.PpmsUser)
            A dict of PpmsUser objects with the username (login) as key.
        """
        if self.users and not force_refresh:
            LOG.debug("Using cached details for %s users", len(self.users))
        else:
            self.update_users()

        return self.users

    def get_users_emails(self, users=None, active=False):
        """Get a list of user email addresses. WARNING - very slow!

        Parameters
        ----------
        users : list(str), optional
            A list of login names to retrieve the email addresses for, if
            omitted addresses for all (or active ones) will be requested.
        active : bool, optional
            Request only addresses of users marked as active in PPMS, by default
            False. Will be ignored if a list of usernames is given explicitly.

        Returns
        -------
        list(str)
            Email addresses of the users requested.
        """
        emails = []
        if users is None:
            users = self.get_user_ids(active=active)
        for user in users:
            email = self.get_user_dict(user)["email"]
            if not email:
                LOG.warning("--- WARNING: no email for user [%s]! ---", user)
                continue
            # LOG.debug("%s: %s", user, email)
            emails.append(email)

        return emails

    def get_users_with_access_to_system(self, system_id):
        """Get a list of usernames allowed to book the system with the given ID.

        Parameters
        ----------
        system_id : int or int-like
            The ID of the system to query permitted users for.

        Returns
        -------
        list(str)
            A list of usernames ('login') with permissions to book the system
            with the given ID in PPMS.

        Raises
        ------
        ValueError
            Raised in case parsing the response failes for any reason.
        """
        users = []

        response = self.request("getsysrights", {"id": system_id})
        # this response has a unique format, so parse it directly here:
        try:
            lines = response.text.splitlines()
            for line in lines:
                permission, username = line.split(":")
                if permission.upper() == "D":
                    LOG.debug(
                        "User [%s] is deactivated for booking system [%s], skipping",
                        username,
                        system_id,
                    )
                    continue

                LOG.debug(
                    "User [%s] has permission to book system [%s]", username, system_id
                )
                users.append(username)

        except Exception as err:
            msg = (
                f"Unable to parse data returned by PUMAPI: {response.text} - "
                f"ERROR: {err}"
            )
            LOG.error(msg)
            raise ValueError(msg) from err

        return users

    def give_user_access_to_system(self, username, system_id):
        """Add permissions for a user to book a given system in PPMS.

        Parameters
        ----------
        username : str
            The username ('login') to allow for booking the system.
        system_id : int or int-like
            The ID of the system to add the permission for.

        Returns
        -------
        bool
            True in case the given username now has the permissions to book the
            system with the specified ID (or if the user already had them
            before), False otherwise.
        """
        return self.set_system_booking_permissions(username, system_id, "A")

    def new_user(  # pylint: disable-msg=too-many-arguments
        self, login, lname, fname, email, ppms_group, phone=None, password=None
    ):
        """Create a new user in PPMS.

        The method is asking PPMS to create a new user account with the given details.
        In case an account with that login name already exists, it will log a warning
        and return without sending any further requests to PPMS.

        Parameters
        ----------
        login : str
            The unique identifier for the user.
        lname : str
            The last name of the user.
        fname : str
            The first name of the user.
        email : str
            The email address of the user.
        ppms_group : str
            The unique identifier of the primary group of the new user. A new group will
            be created if no group with the given name exists.
        phone : str, optional
            The phone number of the user.
        password : str, optional
            The password for the user. If no password is set the user will not be able
            to log on to PPMS.

        Raises
        ------
        RuntimeError
            Will be raised in case creating the user fails.
        """
        if self.user_exists(login):
            LOG.warning("NOT creating user [%s] as it already exists!", login)
            return

        req_data = {
            "login": login,
            "lname": lname,
            "fname": fname,
            "email": email,
            "unitlogin": ppms_group,
        }
        if phone:
            req_data["phone"] = phone
        if password:
            req_data["pwd"] = password

        response = self.request("newuser", req_data)
        if not "OK newuser" in response.text:
            msg = f"Creating new user failed: {response.text}"
            LOG.error(msg)
            raise RuntimeError(msg)

        LOG.info("Created user [%s] in PPMS.", login)
        LOG.debug("Response was: %s", response.text)

    def remove_user_access_from_system(self, username, system_id):
        """Remove permissions for a user to book a given system in PPMS.

        Parameters
        ----------
        username : str
            The username ('login') to remove booking permissions on the system.
        system_id : int or int-like
            The ID of the system to modify the permission for.

        Returns
        -------
        bool
            True in case the given username now has the permissions to book the
            system with the specified ID (or if the user already had them
            before), False otherwise.
        """
        return self.set_system_booking_permissions(username, system_id, "D")

    def set_system_booking_permissions(self, login, system_id, permission):
        """Set permissions for a user on a given system in PPMS.

        Parameters
        ----------
        username : str
            The username ('login') to allow for booking the system.
        system_id : int or int-like
            The ID of the system to add the permission for.
        permission : {'D', 'A', 'N', 'S'}
            The permission level to set for the user, one of:
              - ``D`` : deactivated
              - ``A`` : autonomous
              - ``N`` : novice
              - ``S`` : superuser

        Returns
        -------
        bool
            True in case setting permissions for the given username on the
            system with the specified ID succeeded (or if the user already had
            those permissions before), False otherwise.
        """

        def permission_name(shortname):
            """Closure to validate a permission level and return its long name.

            Parameters
            ----------
            shortname : str
                A single character defining the permission level.

            Returns
            -------
            str
                The long (human-readable) name of the permission level.

            Raises
            ------
            KeyError
                Raised in case an invalid permission level was given.
            """
            mapping = {
                "D": "deactivated",
                "A": "autonomous",
                "N": "novice",
                "S": "superuser",
            }
            try:
                return mapping[shortname]
            except KeyError as err:
                raise KeyError(f"Invalid permission [{shortname}] given") from err

        LOG.debug(
            "Setting permission level [%s] for user [%s] on system [%s]",
            permission_name(permission),
            login,
            system_id,
        )

        parameters = {"id": system_id, "login": login, "type": permission}
        response = self.request("setright", parameters)

        # NOTE: the 'setright' action will accept ANY permission type and return 'done'
        # on the request, so there is no way to check from the response if setting the
        # permission really worked!!
        # LOG.debug('Request returned text: %s', response.text)
        if response.text.lower().strip() == "done":
            LOG.debug(
                "User [%s] now has permission level [%s] on system [%s]",
                login,
                permission_name(permission),
                system_id,
            )
            return True

        if "invalid user" in response.text.lower():
            LOG.warning("User [%s] doesn't seem to exist in PPMS", login)
        elif "system right not authorized" in response.text.lower():
            LOG.error(
                "Unable to set permissions for system %s: %s", system_id, response.text
            )
        else:
            LOG.error("Unexpected response, assuming request failed: %s", response.text)

        return False

    def update_systems(self):
        """Update cached details for all bookable systems from PPMS.

        Get the details on all bookable systems from PPMS and store them in the local
        cache. If parsing the PUMAPI response for a system fails for any reason, the
        system is skipped entirely.
        """
        LOG.debug("Updating list of bookable systems...")
        systems = {}
        parse_fails = 0
        response = self.request("getsystems")
        details = parse_multiline_response(response.text, graceful=False)
        for detail in details:
            try:
                system = PpmsSystem(detail)
            except ValueError as err:
                LOG.error("Error processing `getsystems` response: %s", err)
                parse_fails += 1
                continue

            systems[system.system_id] = system

        LOG.debug(
            "Updated %s bookable systems from PPMS (%s systems failed parsing)",
            len(systems),
            parse_fails,
        )

        self.systems = systems

    def update_users(self, user_ids=[]):
        """Update cached details for a list of users from PPMS.

        Get the user details on a list of users (or all active ones) from PPMS and store
        them in the object's `users` dict. As a side effect, this will also fill the
        cache directory in case the object's `cache_path` attribute is set.

        WARNING - very slow, especially when the PPMS instance has many users!

        Parameters
        ----------
        user_ids : list(str), optional
            A list of user IDs (login names) to request the cache for, by
            default [] which will result in all *active* users to be requested.
        """
        if not user_ids:
            user_ids = self.get_user_ids(active=True)

        LOG.debug("Updating details on %s users", len(user_ids))
        for user_id in user_ids:
            self.get_user(user_id, skip_cache=True)

        LOG.debug("Collected details on %s users", len(self.users))

    def user_exists(self, login):
        """Check if an account with the given login name already exists in PPMS.

        Parameters
        ----------
        login : str
            The login name to check for.

        Returns
        -------
        bool
            True in case an account with that name exists in PPMS, false otherwise.
        """
        try:
            self.get_user(login)
            return True
        except KeyError:
            return False
