# -*- coding: utf-8 -*-

"""Module representing user objects in PPMS."""

import logging

from .common import dict_from_single_response

LOG = logging.getLogger(__name__)


class PpmsUser(object):

    """Object representing a user in PPMS."""

    # TODO: merge the alternative constructor(s) into __init__() (where applicable)
    # TODO: document instance attributes

    def __init__(self, username, email, fullname='',
                 ppms_group='', active=True):
        """Initialize the user object.

        Parameters
        ----------
        username : str
            The user's account / login name for PPMS.
        email : str
            The user's email address.
        fullname : str, optional
            The full name ("<LASTNAME> <GIVENNAME>") of the user in PPMS, by
            default empty ("").
        ppms_group : str, optional
            The user's PPMS group, by default empty ("").
        active : bool, optional
            The state of the user account in PPMS, by default True.
        """
        self.username = u'%s' % username
        self.email = str(email)
        self.active = active
        self.ppms_group = ppms_group
        self._fullname = u'%s' % fullname

        LOG.debug('PpmsUser initialized: username=[%s], email=[%s], '
                  'ppms_group=[%s], fullname=[%s], active=[%s]',
                  self.username, self.email, self.ppms_group, self._fullname,
                  self.active)

    @classmethod
    def from_response(cls, response_text):
        """Alternative constructor using the text from the PUMAPI response.

        Parameters
        ----------
        response_text : str
            The text returned by a PUMAP `getuser` call.

        Returns
        -------
        PpmsUser
            The object constructed with the details contained in the PUMAPI
            response text.

        Raises
        ------
        ValueError
            Raised in case parsing the PUMAPI response data fails.
        """
        details = dict_from_single_response(response_text, graceful=True)

        user = cls(
            username=details['login'],
            email=details['email'],
            fullname=details['lname'] + ' ' + details['fname'],
            ppms_group=details['unitlogin'],
            active=details['active'],
        )
        return user

    @property
    def fullname(self):
        """The user's full name, falling back to the username if empty.

        Returns
        -------
        str
            The full name ("<LASTNAME> <GIVENNAME>") of the user in PPMS, or the
            user accocunt name if the former one is empty.
        """
        if self._fullname == '':
            return self.username

        return self._fullname

    def details(self):
        return ('username: %s, email: %s, fullname: %s, ppms_group: %s, '
                'active: %s' % (self.username, self.email, self.fullname,
                                self.ppms_group, self.active))

    def __str__(self):
        return str(self.username)
