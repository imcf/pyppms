"""Module representing user objects in PPMS."""

from loguru import logger as log

from .billing import PpmsBillingInformation
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
    billing_info : list(PpmsBillingInformation)
        All billing information associated to the user. Note that billing codes
        in PPMS exist at three levels: project, user, group (in descending
        priority).
    fullname : str
        The full name ("``<LASTNAME> <GIVENNAME>``") of the user in PPMS, falling back
        to the ``username`` attribute if empty.
    ppms_group_name : str
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

        self.billing_info = []

        self.ppms_group_name = str(details["unitlogin"])

        if str(details["bcode"]):
            billing_info = PpmsBillingInformation(str(details["bcode"]), "user")
            self.billing_info.append(billing_info)

        self.username = str(details["login"])
        self.email = str(details["email"])
        self.phone = str(details["phone"])
        self.affiliation = str(details["affiliation"])
        self.active = details["active"]
        self._fullname = f"{details['lname']} {details['fname']}"

        log.trace(
            f"PpmsUser initialized: username=[{self.username}], email=[{self.email}], "
            f"ppms_group_name=[{self.ppms_group_name}], fullname=[{self._fullname}], "
            f"active=[{self.active}]"
        )
        if self.billing_info:
            infos = ""
            for info in self.billing_info:
                infos += f"\n- {str(info)}"
            log.trace(f"PpmsUser [{self.username}] billing information:{infos}")

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
            f"ppms_group_name: {self.ppms_group_name}, "
            f"active: {self.active}"
        )

    def __str__(self):  # noqa: D105 (undocumented-magic-method)
        return str(self.username)
