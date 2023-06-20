"""Module representing user objects in PPMS."""

from loguru import logger as log

from .common import dict_from_single_response


class PpmsUser:

    """Object representing a user in PPMS.

    Attributes
    ----------
    username : str
        The user's account / login name in PPMS.
    email : str
        The user's email address.
    fullname : str
        The full name ("``<LASTNAME> <GIVENNAME>``") of the user in PPMS, falling back
        to the ``username`` attribute if empty.
    ppms_group : str
        The user's PPMS group, may be empty ("").
    active : bool
        The ``active`` state of the user account in PPMS, by default True.
    """

    def __init__(self, response_text):
        """Initialize the user object.

        Parameters
        ----------
        response_text : str
            The text returned by a PUMAP `getuser` call.
        """
        details = dict_from_single_response(response_text, graceful=True)

        self.username = str(details["login"])
        self.email = str(details["email"])
        self.active = details["active"]
        self.ppms_group = details["unitlogin"]
        self._fullname = f'{details["lname"]} {details["fname"]}'

        log.trace(
            "PpmsUser initialized: username=[{}], email=[{}], ppms_group=[{}], "
            "fullname=[{}], active=[{}]",
            self.username,
            self.email,
            self.ppms_group,
            self._fullname,
            self.active,
        )

    @property
    def fullname(self):
        """The user's full name, falling back to the username if empty.

        Returns
        -------
        str
            The full name ("<LASTNAME> <GIVENNAME>") of the user in PPMS, or the
            user accocunt name if the former one is empty.
        """
        if self._fullname == "":
            return self.username

        return self._fullname

    def details(self):
        """Generate a string with details on the user object."""
        return (
            f"username: {self.username}, "
            f"email: {self.email}, "
            f"fullname: {self.fullname}, "
            f"ppms_group: {self.ppms_group}, "
            f"active: {self.active}"
        )

    def __str__(self):
        return str(self.username)
