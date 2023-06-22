"""Core connection module for the PUMAPI communication."""

# pylint: disable-msg=dangerous-default-value

# NOTE: the "pyppms" package is simply a wrapper for the existing API, so we can't make
#       any design decisions here - hence it is pointless to complain about the number
#       of instance attributes, public methods or other stuff:
# pylint: disable-msg=too-many-instance-attributes
# pylint: disable-msg=too-many-public-methods

import os
import os.path
import shutil
from io import open

import requests
from loguru import logger as log

from .common import dict_from_single_response, parse_multiline_response
from .user import PpmsUser
from .system import PpmsSystem
from .booking import PpmsBooking
from .exceptions import NoDataError


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
    cache_users_only : bool
        Flag indicating that only PPMS user details will be stored in the
        on-disk cache, nothing else.
    last_served_from_cache
        Indicates if the last request was served from the cache or on-line.
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

    def __init__(self, url, api_key, timeout=10, cache="", cache_users_only=False):
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
        cache_users_only : bool, optional
            If set to `True`, only `getuser` requests will be cached on disk.
            This can be used in to speed up the slow requests (through the
            cache), while everything else will be handled through online
            requests. By default `False`.

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
        self.cache_users_only = cache_users_only
        self.last_served_from_cache = False
        """Indicates if the last request was served from the cache or on-line."""

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
        log.trace(
            "Attempting authentication against {} with key [{}...{}]",
            self.url,
            self.api_key[:2],
            self.api_key[-2:],
        )
        self.status["auth_state"] = "attempting"
        response = self.request("auth")
        log.trace(f"Authenticate response: {response.text}")
        self.status["auth_response"] = response.text
        self.status["auth_httpstatus"] = response.status_code

        # NOTE: an unauthorized request has already been caught be the request() method
        # above. Our legacy code was additionally testing for 'error' in the response
        # text - however, it is unclear if PUMAPI ever returns this:
        if "error" in response.text.lower():
            self.status["auth_state"] = "FAILED-ERROR"
            msg = f"Authentication failed with an error: {response.text}"
            log.error(msg)
            raise requests.exceptions.ConnectionError(msg)

        status_ok = requests.codes.ok  # pylint: disable-msg=no-member

        if response.status_code != status_ok:
            # NOTE: branch excluded from coverage as we don't have a known way
            # to produce such a response from the API
            log.warning(
                "Unexpected combination of response [{}] and status code [{}], it's "
                "unclear if authentication succeeded (assuming it didn't)",
                response.status_code,
                response.text,
            )
            self.status["auth_state"] = "FAILED-UNKNOWN"

            msg = (
                f"Authenticating against {self.url} with key "
                f"[{self.api_key[:2]}...{self.api_key[-2:]}] FAILED!"
            )
            log.error(msg)
            raise requests.exceptions.ConnectionError(msg)

        log.debug(
            "Authentication succeeded, response=[{}], http_status=[{}]",
            response.text,
            response.status_code,
        )
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
        # log.debug("Request parameters: {}", parameters)

        response = None
        try:
            if skip_cache:  # pragma: no cover
                raise LookupError("Skipping the cache has been requested")
            response = self.__intercept_read(req_data)
            self.last_served_from_cache = True
        except LookupError as err:
            log.trace(f"Doing an on-line request: {err}")
            response = requests.post(self.url, data=req_data, timeout=self.timeout)
            self.last_served_from_cache = False

        # store the response if it hasn't been read from the cache before:
        if not self.last_served_from_cache:  # pragma: no cover
            self.__intercept_store(req_data, response)

        # NOTE: the HTTP status code returned is always `200` even if
        # authentication failed, so we need to check the actual response *TEXT*
        # to figure out if we have succeeded:
        if "request not authorized" in response.text.lower():
            self.status["auth_state"] = "FAILED"
            msg = f"Not authorized to run action `{req_data['action']}`"
            log.error(msg)
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

        if self.cache_users_only and action != "getuser":
            log.trace(f"NOT caching '{action}' (cache_users_only is set)")
            return None

        intercept_dir = os.path.join(self.cache_path, action)
        if create_dir and not os.path.exists(intercept_dir):  # pragma: no cover
            try:
                os.makedirs(intercept_dir)
                log.trace(f"Created dir to store response: {intercept_dir}")
            except Exception as err:  # pylint: disable-msg=broad-except
                log.warning(f"Failed creating [{intercept_dir}]: {err}")
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
        if not intercept_file or not os.path.exists(intercept_file):  # pragma: no cover
            raise LookupError(f"No cache hit for [{intercept_file}]")

        with open(intercept_file, "r", encoding="utf-8") as infile:
            text = infile.read()
        log.debug(
            "Read intercepted response text from [{}]",
            intercept_file[len(str(self.cache_path)) :],
        )

        status_code = 200
        status_file = os.path.splitext(intercept_file)[0] + "_status-code.txt"
        if os.path.exists(status_file):
            with open(status_file, "r", encoding="utf-8") as infile:
                status_code = infile.read()
            log.debug(f"Read intercepted response status code from [{status_file}]")
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
            log.trace("Not storing intercepted results in cache.")
            return

        try:
            with open(intercept_file, "w", encoding="utf-8") as outfile:
                outfile.write(response.text)
            log.debug(
                "Wrote response text to [{}] ({} lines)",
                intercept_file,
                len(response.text.splitlines()),
            )
        except Exception as err:  # pylint: disable-msg=broad-except
            log.error("Storing response text in [{}] failed: {}", intercept_file, err)
            log.error("Response text was:\n--------\n{}\n--------", response.text)

    def flush_cache(self, keep_users=False):
        """Flush the PyPPMS on-disk cache.

        Optionally flushes everything *except* the `getuser` cache if the
        `keep_users` flag is set to `True`, as this is clearly the most
        time-consuming operation when fetching data from PUMAPI and therefore
        might want to be retained.

        Please note that the `getusers` cache (plural, including the `s` suffix)
        will be flushed no matter what, as this is simply a list of user IDs
        that can be fetched with a single request. In consequence this means
        that using the `keep_users` flag will allow you to have reasonably fast
        reaction times while still getting information on *new* users live from
        PUMAPI at the only cost of possibly having outdated information on
        *existing* users.

        Parameters
        ----------
        keep_users : bool, optional
            If set to `True` the `getuser` sub-directory in the cache location
            will be kept, by default `False`.
        """
        if self.cache_path == "":
            log.debug("No cache path configured, not flushing!")
            return

        dirs_to_remove = [self.cache_path]  # by default remove the entire cache dir
        keep_msg = ""
        if keep_users:
            keep_msg = " (keeping user details dirs)"
            dirs_to_remove = []
            cache_dirs = os.listdir(self.cache_path)
            for subdir in cache_dirs:
                if subdir == "getuser":
                    continue
                dirs_to_remove.append(os.path.join(self.cache_path, subdir))

        log.debug("Flushing the on-disk cache at [{}] {}...", self.cache_path, keep_msg)
        for directory in dirs_to_remove:
            try:
                shutil.rmtree(directory)
                log.trace("Removed directory [{}].", directory)
            except Exception as ex:  # pylint: disable-msg=broad-except
                log.warning("Removing the cache at [{}] failed: {}", directory, ex)

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
        log.trace("{} admins in the PPMS database: {}", len(admins), ", ".join(admins))
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
            NOTE: if `next` is requested the resulting booking object will **NOT** have
            an end time (`endtime` will be `None`) as PUMAPI doesn't provide one in that
            case!

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
            log.error("Requesting booking status for system {} failed!", system_id)
            return None

        desc = "any future bookings"
        if booking_type == "get":
            desc = "a currently active booking"
        if not response.text.strip():
            log.trace("System [{}] doesn't have {}", system_id, desc)
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
        log.trace("Group details returned by PPMS (raw): {}", response.text)

        if not response.text:
            msg = f"Group [{group_id}] is unknown to PPMS"
            log.error(msg)
            raise KeyError(msg)

        details = dict_from_single_response(response.text)

        log.trace("Details of group {}: {}", group_id, details)
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
        log.trace(
            "{} members in PPMS group [{}]: {}",
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
        log.trace("{} groups in the PPMS database: {}", len(groups), ", ".join(groups))
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
            attribute `fullname_mapping` will be ignored in the resulting list.

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
        log.trace("Requesting runningsheet for {}", parameters["day"])
        response = self.request("getrunningsheet", parameters)
        try:
            entries = parse_multiline_response(response.text, graceful=False)
        except NoDataError:
            # in case no bookings exist the response will be empty!
            log.trace("Runningsheet for the given day was empty!")
            return []
        except Exception as err:  # pylint: disable-msg=broad-except
            log.error("Parsing runningsheet details failed: {}", err)
            log.trace("Runningsheet PUMPAI response was: >>>{}<<<", response.text)
            return []

        for entry in entries:
            full = entry["User"]
            if full not in self.fullname_mapping:
                if ignore_uncached_users:
                    log.debug("Ignoring booking for uncached user [{}]", full)
                    continue

                log.debug("Booking for an uncached user ({}) found!", full)
                self.update_users()

            if full not in self.fullname_mapping:
                log.error("PPMS doesn't seem to know user [{}], skipping", full)
                continue

            log.trace(
                "Booking for user '{}' ({}) found", self.fullname_mapping[full], full
            )
            system_name = entry["Object"]
            system_ids = self.get_systems_matching("", [system_name])
            if len(system_ids) != 1:
                # NOTE: more than one result should not happen as PPMS doesn't allow for
                # multiple systems having the same name - no result might happen though!
                log.error("Ignoring booking for unknown system [{}]", system_name)
                continue

            booking = PpmsBooking.from_runningsheet(
                entry,
                system_ids[0],
                self.fullname_mapping[full],
                date,
            )
            bookings.append(booking)

        return bookings

    def get_systems(self, force_refresh=False):
        """Get a dict with all systems in PPMS.

        Parameters
        ----------
        force_refresh : bool, optional
            If `True` the list of systems will be refreshed even if the object's
            attribute `self.systems` is non-empty, by default `False`. Please
            note that this will NOT skip the on-disk cache in case that exists!

        Returns
        -------
        dict(pyppms.system.PpmsSystem)
            A dict with `PpmsSystem` objects parsed from the PUMAPI response where
            the system ID (int) is used as the dict's key. If parsing a system
            fails for any reason, the system is skipped entirely.
        """
        if self.systems and not force_refresh:
            log.trace("Using cached details for {} systems", len(self.systems))
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
            the PPMS web interface) has to match. Can be an empty string which
            will result in no filtering being done on the "Room" attribute.
        name_contains : list(str)
            A list of valid names (categories) of which the system's name has to
            match at least one for being included. Supply an empty list for
            skipping this filter.

        Returns
        -------
        list(int)
            A list with PPMS system IDs matching all of the given criteria.

        Raises
        ------
        TypeError
            Raised in case the `name_contains` parameter is of type `str` (it
            needs to be `list(str)` instead).
        """
        if isinstance(name_contains, str):
            raise TypeError("`name_contains` must be a list of str, not str!")

        loc = localisation
        loc_desc = f"with location matching [{localisation}]"
        if localisation == "":
            loc_desc = "(no location filter given)"

        log.trace(
            "Querying PPMS for systems {}, name matching any of {}",
            loc_desc,
            name_contains,
        )
        system_ids = []
        systems = self.get_systems()
        for sys_id, system in systems.items():
            if loc.lower() not in str(system.localisation).lower():
                log.trace(
                    "System [{}] location ({}) is NOT matching ({}), ignoring",
                    system.name,
                    system.localisation,
                    loc,
                )
                continue

            # log.trace('System [{}] is matching location [{}], checking if '
            #           'the name is matching any of the valid pattern {}',
            #           system.name, loc, name_contains)
            for valid_name in name_contains:
                if valid_name in system.name:
                    log.trace("System [{}] matches all criteria", system.name)
                    system_ids.append(sys_id)
                    break

            # if sys_id not in system_ids:
            #     log.trace('System [{}] does NOT match a valid name: {}',
            #               system.name, name_contains)

        log.trace("Found {} bookable systems {}", len(system_ids), loc_desc)
        log.trace("IDs of matching bookable systems {}: {}", loc_desc, system_ids)
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
            log.debug(msg)
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
            log.error(msg)
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
        log.trace("Details for user [{}]: {}", login_name, details)
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
        log.trace(
            "Received {} experience entries for filters [user:{}] and [id:{}]",
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
        log.trace("{} {}users in the PPMS database", len(users), active_desc)
        log.trace(", ".join(users))
        return users

    def get_users(self, force_refresh=False, active_only=True):
        """Get user objects for all (or cached) PPMS users.

        Parameters
        ----------
        force_refresh : bool, optional
            Re-request information from PPMS even if user details have been
            cached locally before, by default False.
        active_only : bool, optional
            If set to `False` also "inactive" users will be fetched from PPMS,
            by default `True`.

        Returns
        -------
        dict(pyppms.user.PpmsUser)
            A dict of PpmsUser objects with the username (login) as key.
        """
        if self.users and not force_refresh:
            log.trace("Using cached details for {} users", len(self.users))
        else:
            self.update_users(active_only=active_only)

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
                log.warning("--- WARNING: no email for user [{}]! ---", user)
                continue
            # log.trace("{}: {}", user, email)
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
                    log.trace(
                        "User [{}] is deactivated for booking system [{}], skipping",
                        username,
                        system_id,
                    )
                    continue

                log.trace(
                    "User [{}] has permission to book system [{}]", username, system_id
                )
                users.append(username)

        except Exception as err:
            msg = (
                f"Unable to parse data returned by PUMAPI: {response.text} - "
                f"ERROR: {err}"
            )
            log.error(msg)
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
            log.warning("NOT creating user [{}] as it already exists!", login)
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
            log.error(msg)
            raise RuntimeError(msg)

        log.debug("Created user [{}] in PPMS.", login)
        log.trace("Response was: {}", response.text)

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

        log.debug(
            "Setting permission level [{}] for user [{}] on system [{}]",
            permission_name(permission),
            login,
            system_id,
        )

        parameters = {"id": system_id, "login": login, "type": permission}
        response = self.request("setright", parameters)

        # NOTE: the 'setright' action will accept ANY permission type and return 'done'
        # on the request, so there is no way to check from the response if setting the
        # permission really worked!!
        # log.trace('Request returned text: {}', response.text)
        if response.text.lower().strip() == "done":
            log.trace(
                "User [{}] now has permission level [{}] on system [{}]",
                login,
                permission_name(permission),
                system_id,
            )
            return True

        if "invalid user" in response.text.lower():
            log.warning("User [{}] doesn't seem to exist in PPMS", login)
        elif "system right not authorized" in response.text.lower():
            log.error(
                "Unable to set permissions for system {}: {}", system_id, response.text
            )
        else:
            log.error("Unexpected response, assuming request failed: {}", response.text)

        return False

    def update_systems(self):
        """Update cached details for all bookable systems from PPMS.

        Get the details on all bookable systems from PPMS and store them in the local
        cache. If parsing the PUMAPI response for a system fails for any reason, the
        system is skipped entirely.
        """
        log.trace("Updating list of bookable systems...")
        systems = {}
        parse_fails = 0
        response = self.request("getsystems")
        details = parse_multiline_response(response.text, graceful=False)
        for detail in details:
            try:
                system = PpmsSystem(detail)
            except ValueError as err:
                log.error("Error processing `getsystems` response: {}", err)
                parse_fails += 1
                continue

            systems[system.system_id] = system

        log.trace(
            "Updated {} bookable systems from PPMS ({} systems failed parsing)",
            len(systems),
            parse_fails,
        )

        self.systems = systems

    def update_users(self, user_ids=[], active_only=True):
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
        active_only : bool, optional
            If set to `False` also "inactive" users will be fetched from PPMS,
            by default `True`.
        """
        if not user_ids:
            user_ids = self.get_user_ids(active=active_only)

        log.trace("Updating details on {} users", len(user_ids))
        for user_id in user_ids:
            self.get_user(user_id, skip_cache=True)

        log.debug("Collected details on {} users", len(self.users))

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
