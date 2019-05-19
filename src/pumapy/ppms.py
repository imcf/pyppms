# -*- coding: utf-8 -*-

"""Access Stratocore's PPMS Utility Management API.

Authors: Niko Ehrenfeuchter <nikolaus.ehrenfeuchter@unibas.ch>
         Basil Neff <basil.neff@unibas.ch>
"""

import logging

import requests

from .user import PpmsUser


LOG = logging.getLogger(__name__)


def process_response_values(values):
    """Process (in-place) a list of strings, remove quotes, detect boolean etc.

    Check all (str) elements of the given list, remove surrounding double-quotes
    and convert 'true' / 'false' strings into Python booleans.

    Parameters
    ----------
    values : list(str)
        The list of strings that should be processed.

    Returns
    -------
    None
        Nothing is returned, the list's element are processed in-place.
    """
    # tell pylint that there is no real gain using enumerate here:
    # pylint: disable-msg=consider-using-enumerate
    for i in range(len(values)):
        values[i] = values[i].strip('"')
        if values[i] == 'true':
            values[i] = True
        if values[i] == 'false':
            values[i] = False

def dict_from_single_response(text, graceful=True):
    """Parse a two-line CSV response from PUMAPI and create a dict from it.

    Parameters
    ----------
    text : str
        The PUMAPI response with two lines: a header line and one data line.
    graceful : bool, optional
        Whether to continue in case the response text is inconsistent, i.e.
        having different number of fields in the header line and the data line,
        by default True. In graceful mode, any inconsistency detected in the
        data will be logged as a warning, in non-graceful mode they will raise
        an Exception.

    Returns
    -------
    dict
        A dict with the fields of the header line being the keys and the fields
        of the data line being the values. Values are stripped from quotes
        and converted to Python boolean values where applicable.

    Raises
    ------
    ValueError
        Raised when the response text is inconsistent and the `graceful`
        parameter has been set to false, or if parsing fails for any other
        unforeseen reason.
    """
    # TODO: use Python's CSV parser that is much more robust than the manual
    # string splitting approach below which will fail as soon as a field
    # contains a comma!
    try:
        lines = text.splitlines()
        if len(lines) != 2:
            LOG.warn('Response expected to have exactly two lines: %s', text)
            if not graceful:
                raise ValueError("Invalid response format!")
        header = lines[0].split(',')
        data = lines[1].split(',')
        process_response_values(data)
        if len(header) != len(data):
            msg = 'Splitting CSV data failed'
            LOG.warn('%s, header has %s fields whereas the data has %s fields!',
                     msg, len(header), len(data))
            if not graceful:
                raise ValueError(msg)
            minimum = min(len(header), len(data))
            if minimum < len(header):
                LOG.warn('Discarding header-fields: %s', header[minimum:])
                header = header[:minimum]
            else:
                LOG.warn('Discarding data-fields: %s', data[minimum:])
                data = data[:minimum]

    except Exception as err:
        msg = ('Unable to parse data returned by PUMAPI: %s - ERROR: %s' %
               (text, err))
        LOG.error(msg)
        raise ValueError(msg)

    parsed = dict(zip(header, data))
    return parsed


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
        response = requests.post(self.url, data={'action': 'auth',
                                                 'apikey': self.api_key})
        LOG.debug('Authenticate response: %s', response.text)

        # WARNING: the HTTP status code returned is not correct - it is always
        # `200` even if authentication failed, so we need to check the actual
        # response *TEXT* to check if we have succeeded:
        if 'request not authorized' in response.text.lower():
            LOG.warn('Authentication failed: %s', response.text)
            return False
        elif 'error' in response.text.lower():
            LOG.warn('Authentication failed with an error: %s', response.text)
            return False

        if response.status_code == requests.codes.ok:  # pylint: disable-msg=no-member
            LOG.info('Authentication succeeded, response=[%s]', response.text)
            LOG.debug('HTTP Status: %s', response.status_code)
            return True

        LOG.warn("Unexpected combination of response [%s] and status code [%s],"
                 " it' uncelar if the authentication was successful (assuming "
                 "it wasn't)", response.status_code, response.text)
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
