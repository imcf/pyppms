"""Module representing user objects in PPMS."""

from loguru import logger as log

from .billing import PpmsBillingInformation
from .common import dict_from_single_response
from .group import PpmsGroup


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
    billing_info : list(pyppms.billing.PpmsBillingInformation)
        All billing information associated to the user. Note that billing codes
        in PPMS exist at three levels: project, user, group (in descending
        priority). In order to contain the group-related billing codes, the
        object's constructor requires the PPMS connection object to be passed
        (see the constructor documentation for more info).
    fullname : str
        The full name ("``<LASTNAME> <GIVENNAME>``") of the user in PPMS,
        falling back to the ``username`` attribute if empty.
    ppms_group_name : str
        The user's PPMS group derived from field `unitlogin`, may be empty ("").
    ppms_group : pyppms.group.PpmsGroup | None
        The PpmsGroup object retrieved through `get_group(self.ppms_group_name)`
        or None in case no group name is present.
    affiliation : str
        The user's affiliation (institute, ...).
    active : bool
        The ``active`` state of the user account in PPMS, by default True.
    """

    def __init__(self, response_text, conn=None):
        """Initialize the user object.

        Parameters
        ----------
        response_text : str
            The text returned by a PUMAPI `getuser` call.
        conn : ppms.PpmsConnection or None, optional
            The PPMS connection object. If given, it will be used to fetch
            the user's group billing code. If omitted (default), only the user
            billing information will be available from the object.
        """
        details = dict_from_single_response(response_text, graceful=True)

        self.billing_info: list[PpmsBillingInformation] = []
        self.ppms_group: PpmsGroup | None = None

        self.ppms_group_name: str = str(details["unitlogin"])
        if self.ppms_group_name and conn:
            log.trace(f"Fetching group details for [{self.ppms_group_name}]...")
            self.ppms_group = conn.get_group(self.ppms_group_name)
            if self.ppms_group:
                group_billing = self.ppms_group.billing_info
                group_billing.description = f"Group: {self.ppms_group_name}"
                self.billing_info.append(group_billing)

        if str(details["bcode"]):
            billing_info = PpmsBillingInformation(
                str(details["bcode"]), "user", "Personal billing code"
            )
            self.billing_info.append(billing_info)

        self.username: str = str(details["login"])
        self.email: str = str(details["email"])
        self.phone: str = str(details["phone"])
        self.affiliation: str = str(details["affiliation"])
        self.active: bool = bool(details["active"])
        self._fullname: str = f"{details['lname']} {details['fname']}"

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
    def fullname(self) -> str:
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

    def details(self) -> str:
        """Generate a string with details on the user object."""
        return (
            f"username: {self.username}, "
            f"email: {self.email}, "
            f"fullname: {self.fullname}, "
            f"ppms_group_name: {self.ppms_group_name}, "
            f"active: {self.active}"
        )

    def __str__(self) -> str:  # noqa: D105 (undocumented-magic-method)
        return str(self.username)
