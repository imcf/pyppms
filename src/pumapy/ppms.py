# -*- coding: utf-8 -*-

"""Access Stratocore's PPMS Utility Management API.

Authors: Niko Ehrenfeuchter <nikolaus.ehrenfeuchter@unibas.ch>
         Basil Neff <basil.neff@unibas.ch>
"""

# pylint: disable-msg=dangerous-default-value

import logging

import requests

from .common import dict_from_single_response, parse_multiline_response
from .user import PpmsUser
from .system import PpmsSystem


LOG = logging.getLogger(__name__)


class PpmsConnection(object):

    """Connection object to communicate with a PPMS instance."""

    # TODO: all methods returning a list of user objects (get_group_users,
    # get_admins, ...) should be refactored to return a dict with those objects
    # instead, having the username ('login') as the key.

    def __init__(self, url, api_key, timeout=10):
        """Constructor for the PPMS connection object.

        Open a connection to the PUMAPI defined in `url` and try to authenticate
        against it using the given API Key.

        Parameters
        ----------
        url : str
            The URL of the PUMAPI to connect to.
        api_key : str
            The API key to use for authenticating against the PUMAPI.
        timeout : float, optional
            How many seconds to wait for the PUMAPI server to send a response
            before giving up, by default 10.

        Raises
        ------
        requests.exceptions.ConnectionError
            Raised in case authentication fails.
        """
        self.url = url
        self.api_key = api_key
        self.timeout = timeout
        self.users = None
        self.systems = None
        self.status = {
            'auth_state': 'NOT_TRIED',
            'auth_response': None,
            'auth_httpstatus': -1,
        }

        self.__authenticate()

    def __authenticate(self):
        """Try to authenticate to PPMS using the `auth` request.

        Raises
        ------
        requests.exceptions.ConnectionError
            Raised in case authentication failed for any reason.
        """
        LOG.debug('Attempting authentication against %s with key [%s...%s]',
                  self.url, self.api_key[:2], self.api_key[-2:])
        self.status['auth_state'] = 'attempting'
        response = self.request('auth')
        LOG.debug('Authenticate response: %s', response.text)
        self.status['auth_response'] = response.text
        self.status['auth_httpstatus'] = response.status_code

        # NOTE: an unauthorized request has already been caught be the request()
        # method above. Our legacy code was additionally testing for 'error' in
        # the response text - however, there doesn't seem to be a way to trigger
        # such a response, so we exclude it from testing (and coverage).
        if 'error' in response.text.lower():  # pragma: no cover
            self.status['auth_state'] = 'FAILED-ERROR'
            msg = 'Authentication failed with an error: %s' % response.text
            LOG.error(msg)
            raise requests.exceptions.ConnectionError(msg)

        status_ok = requests.codes.ok  # pylint: disable-msg=no-member

        if response.status_code != status_ok:  # pragma: no cover
            # NOTE: branch excluded from coverage as we don't have a known way
            # to produce such a response from the API
            LOG.warn("Unexpected combination of response [%s] and status code "
                     "[%s], it's unclear if authentication succeeded (assuming "
                     "it didn't)", response.status_code, response.text)
            self.status['auth_state'] = 'FAILED-UNKNOWN'

            msg = 'Authenticating against %s with key [%s...%s] FAILED!' % (
                self.url, self.api_key[:2], self.api_key[-2:])
            LOG.error(msg)
            raise requests.exceptions.ConnectionError(msg)

        LOG.info('Authentication succeeded, response=[%s]', response.text)
        LOG.debug('HTTP Status: %s', response.status_code)
        self.status['auth_state'] = 'good'
        return

    def request(self, action, parameters={}):
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

        Returns
        -------
        requests.Response
            The response object created by posting the request.

        Raises
        ------
        requests.exceptions.ConnectionError
            Raised in case the request is not authorized.
        """
        req_data = {
            'action': action,
            'apikey': self.api_key,
        }
        req_data.update(parameters)

        response = requests.post(self.url, data=req_data, timeout=self.timeout)
        # NOTE: the HTTP status code returned is always `200` even if
        # authentication failed, so we need to check the actual response *TEXT*
        # to figure out if we have succeeded:
        if 'request not authorized' in response.text.lower():
            self.status['auth_state'] = 'FAILED'
            msg = 'Not authorized to run action `%s`' % req_data['action']
            LOG.error(msg)
            raise requests.exceptions.ConnectionError(msg)

        return response

    ############ users / groups ############

    def get_users(self, active=False):
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
        parameters = dict()
        if active:
            parameters['active'] = 'true'

        response = self.request('getusers', parameters)

        users = response.text.splitlines()
        active_desc = "active " if active else ""
        LOG.info('%s %susers in the PPMS database', len(users), active_desc)
        LOG.debug(', '.join(users))
        return users

    def get_user_dict(self, login_name):
        """Get details on a given user from PPMS.

        Parameters
        ----------
        login_name : str
            The PPMS account / login name of the user to query.

        Returns
        -------
        dict
            A dict with the user details returned by the PUMAPI.

        Example
        -------
        >>> conn.get_user_dict('pumapy')
        ... {
        ...     u'active': True,
        ...     u'affiliation': u'',
        ...     u'bcode': u'',
        ...     u'email': u'pumapy@python-facility.example',
        ...     u'fname': u'PumAPI',
        ...     u'lname': u'Python',
        ...     u'login': u'pumapy',
        ...     u'mustchbcode': False,
        ...     u'mustchpwd': False',
        ...     u'phone': u'+98 (76) 54 3210',
        ...     u'unitlogin': u'pumapy'
        ... }

        Raises
        ------
        KeyError
            Raised in case the user account is unknown to PPMS.
        ValueError
            Raised if the user details can't be parsed from the PUMAPI response.
        """
        response = self.request('getuser', {'login': login_name})

        if not response.text:
            msg = "User [%s] is unknown to PPMS" % login_name
            LOG.error(msg)
            raise KeyError(msg)

        # EXAMPLE:
        # response.text = (
        #     u'login,lname,fname,email,'
        #     u'phone,bcode,affiliation,unitlogin,mustchpwd,mustchbcode,'
        #     u'active\r\n'
        #     u'"pumapy","Python","PumAPI","pumapy@python-facility.example",'
        #     u'"+98 (76) 54 3210","","","pumapy",false,false,'
        #     u'true\r\n'
        # )
        details = dict_from_single_response(response.text)
        LOG.debug("Details for user [%s]: %s", login_name, details)
        return details

    def get_user(self, login_name):
        """Fetch user details from PPMS and create a PpmsUser object from it.

        Parameters
        ----------
        login_name : str
            The user's PPMS login name.

        Returns
        -------
        PpmsUser
            The user object created from the PUMAPI response.

        Raises
        ------
        KeyError
            Raised if the user doesn't exist in PPMS.
        """
        response = self.request('getuser', {'login': login_name})

        if not response.text:
            msg = "User [%s] is unknown to PPMS" % login_name
            LOG.error(msg)
            raise KeyError(msg)

        return PpmsUser.from_response(response.text)

    def get_admins(self):
        """Get all PPMS administrator users.

        Returns
        -------
        list(PpmsUser)
            A list with PpmsUser objects that are PPMS administrators.
        """
        response = self.request('getadmins')

        admins = response.text.splitlines()
        users = []
        for username in admins:
            user = self.get_user(username)
            users.append(user)
        LOG.debug('%s admins in the PPMS database: %s', len(admins),
                  ', '.join(admins))
        return users

    def get_groups(self):
        """Get a list of all groups in PPMS.

        Returns
        -------
        list(str)
            A list with the group identifiers in PPMS.
        """
        response = self.request('getgroups')

        groups = response.text.splitlines()
        LOG.debug('%s groups in the PPMS database: %s', len(groups),
                  ', '.join(groups))
        return groups

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
        response = self.request('getgroup', {'unitlogin': group_id})
        LOG.debug("Group details returned by PPMS (raw): %s", response.text)

        if not response.text:
            msg = "Group [%s] is unknown to PPMS" % group_id
            LOG.error(msg)
            raise KeyError(msg)

        details = dict_from_single_response(response.text)

        LOG.debug('Details of group %s: %s', group_id, details)
        return details

    def get_group_users(self, unitlogin):
        """Get all members of a group in PPMS.

        Parameters
        ----------
        unitlogin : str
            The group's login ("unique login or id" in the PPMS web interface).

        Returns
        -------
        list(PpmsUser)
            A list with PpmsUser objects that are members of this PPMS group.
        """
        response = self.request('getgroupusers', {'unitlogin': unitlogin})

        members = response.text.splitlines()
        users = []
        for username in members:
            user = self.get_user(username)
            users.append(user)
        LOG.debug('%s members in PPMS group [%s]: %s', len(members), unitlogin,
                  ', '.join(members))
        return users

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
        data = dict()
        if login is not None:
            data['login'] = login
        if system_id is not None:
            data['id'] = system_id
        response = self.request('getuserexp', parameters=data)
        
        parsed = parse_multiline_response(response.text)
        LOG.debug('Received %s experience entries for filters [user:%s] and '
                  '[id:%s]', len(parsed), login, system_id)
        return parsed

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
        emails = list()
        # TODO: add a test for the 'users==None' case as soon as we have
        # something like 'betamax' or similar in place that speeds up the
        # requests by caching them locally
        if users is None:  # pragma: no cover
            users = self.get_users(active=active)
        for user in users:
            email = self.get_user_dict(user)['email']
            if not email:  # pragma: no cover
                LOG.warn("--- WARNING: no email for user %s! ---" % user)
                continue
            LOG.debug("%s: %s", user, email)
            emails.append(email)

        return emails

    def get_systems(self):
        """Get a dict with all systems in PPMS.

        Returns
        -------
        dict(PpmsSystem)
            A dict with PpmsSystem objects parsed from the PUMAPI response where
            the system ID (int) is used as the dict's key. If the ID of any
            system cannot be parsed to int, the system is skipped entirely.
        """
        systems = dict()
        response = self.request('getsystems')
        details = parse_multiline_response(response.text, graceful=False)
        for detail in details:
            system = PpmsSystem.from_parsed_response(detail)
            try:
                sys_id = int(system.system_id)
            except ValueError as err:
                LOG.error('Unable to parse system ID: %s - %s',
                          system.system_id, err)
                continue

            systems[sys_id] = system

        LOG.debug('Found %s systems in PPMS', len(systems))

        return systems
