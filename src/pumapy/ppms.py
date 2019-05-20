# -*- coding: utf-8 -*-

"""Access Stratocore's PPMS Utility Management API.

Authors: Niko Ehrenfeuchter <nikolaus.ehrenfeuchter@unibas.ch>
         Basil Neff <basil.neff@unibas.ch>
"""

import logging

import requests

from .common import dict_from_single_response
from .user import PpmsUser


LOG = logging.getLogger(__name__)


class PpmsConnection(object):

    """Connection object to communicate with a PPMS instance."""

    def __init__(self, url, api_key):
        """Constructor for the PPMS connection object.

        Open a connection to the PUMAPI defined in `url` and try to authenticate
        against it using the given API Key.

        Parameters
        ----------
        url : str
            The URL of the PUMAPI to connect to.
        api_key : str
            The API key to use for authenticating against the PUMAPI.

        Raises
        ------
        requests.exceptions.ConnectionError
            Raised in case authentication fails.
        """
        self.url = url
        self.api_key = api_key
        self.users = None
        self.systems = None
        self.status = {
            'auth_state': 'NOT_TRIED',
            'auth_response': None,
            'auth_httpstatus': -1,
        }

        if not self.__authenticate():
            msg = 'Authenticating against %s with key [%s...%s] FAILED!' % (
                url, api_key[:2], api_key[-2:])
            LOG.error(msg)
            raise requests.exceptions.ConnectionError(msg)

    def __authenticate(self):
        """Try to authenticate to PPMS using the `auth` request.

        Returns
        -------
        bool
            True if authentication was successful, False otherwise.
        """
        LOG.debug('Attempting authentication against %s with key [%s...%s]',
                  self.url, self.api_key[:2], self.api_key[-2:])
        self.status['auth_state'] = 'attempting'
        response = self.request('auth')
        LOG.debug('Authenticate response: %s', response.text)
        self.status['auth_response'] = response.text
        self.status['auth_httpstatus'] = response.status_code

        # WARNING: the HTTP status code returned is not correct - it is always
        # `200` even if authentication failed, so we need to check the actual
        # response *TEXT* to check if we have succeeded:
        if 'request not authorized' in response.text.lower():
            LOG.warn('Authentication failed: %s', response.text)
            self.status['auth_state'] = 'FAILED'
            return False
        elif 'error' in response.text.lower():
            LOG.warn('Authentication failed with an error: %s', response.text)
            self.status['auth_state'] = 'FAILED-ERROR'
            return False

        status_ok = requests.codes.ok  # pylint: disable-msg=no-member
        if response.status_code == status_ok:
            LOG.info('Authentication succeeded, response=[%s]', response.text)
            LOG.debug('HTTP Status: %s', response.status_code)
            self.status['auth_state'] = 'good'
            return True

        LOG.warn("Unexpected combination of response [%s] and status code [%s],"
                 " it's uncelar if the authentication was successful (assuming "
                 "it wasn't)", response.status_code, response.text)
        self.status['auth_state'] = 'FAILED-UNKNOWN'
        return False

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

        response = requests.post(self.url, data=req_data)
        if 'request not authorized' in response.text.lower():
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
        >>> conn.get_user('pumapy')
        ... {u'active': u'true',
        ...  u'affiliation': u'""',
        ...  u'bcode': u'""',
        ...  u'email': u'"does-not-reply@facility.xy"',
        ...  u'fname': u'"PumAPI"',
        ...  u'lname': u'"Python"',
        ...  u'login': u'"pumapy"',
        ...  u'mustchbcode': u'false',
        ...  u'mustchpwd': u'false',
        ...  u'phone': u'"+98 (76) 54 3210"',
        ...  u'unitlogin': u'"Python Core Facility"'}

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
        #     u'login,lname,fname,email,phone,bcode,affiliation,unitlogin,'
        #     u'mustchpwd,mustchbcode,active\r\n'
        #     u'"pumapy","Python","PumAPI","does-not-reply@facility.xy","","",'
        #     u'"","Python Core Facility",false,false,true\r\n'
        # )
        fields, values = response.text.splitlines()
        fields = fields.split(',')
        values = values.split(',')
        if len(fields) != len(values):
            msg = 'Unable to parse user details: %s' % response.text
            LOG.warn(msg)
            raise ValueError(msg)

        details = dict(zip(fields, values))
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

        details = dict_from_single_response(response.text)

        LOG.debug('Details of group %s: %s', group_id, details)
        return details
