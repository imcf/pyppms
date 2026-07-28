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
    phone :str
        The user's phone number.
    billing_code : str
        The user's billing code (`bcode`). Note that billing codes in PPMS exist
        at three levels: project, user, group (with descending priority).
    fullname : str
        The full name ("``<LASTNAME> <GIVENNAME>``") of the user in PPMS, falling back
        to the ``username`` attribute if empty.
    ppms_group : str
        The user's PPMS group, may be empty ("").
    affiliation : str
        The user's affiliation (institute, ...).
    active : bool
        The ``active`` state of the user account in PPMS, by default True.
    """

    def __init__(self, response_text):
        """Initialize the user object.

        Parameters
        ----------
        response_text : str
            The text returned by a PUMAPI `getuser` call.
        """
        details = dict_from_single_response(response_text, graceful=True)

        self.username = str(details["login"])
        self.email = str(details["email"])
        self.phone = str(details["phone"])
        self.billing_code = str(details["bcode"])
        self.affiliation = str(details["affiliation"])
        self.active = details["active"]
        self.ppms_group = details["unitlogin"]
        self._fullname = f"{details['lname']} {details['fname']}"

        log.trace(
            "PpmsUser initialized: username=[{}], email=[{}], billing_code=[{}], "
            "ppms_group=[{}], fullname=[{}], active=[{}]",
            self.username,
            self.email,
            self.billing_code,
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
            user account name if the former one is empty.
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

    def __str__(self):  # noqa: D105 (undocumented-magic-method)
        return str(self.username)
