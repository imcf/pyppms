"""Module representing group objects in PPMS."""

from loguru import logger as log

from .billing import PpmsBillingInformation
from .common import dict_from_single_response


class PpmsGroup:
    """Object representing a group in PPMS.

    Attributes
    ----------
    gid : str
        The group's account / login name (`unitlogin`) in PPMS.
    name : str
        The group's name (`unitname`).
    head_name : str
        The name of the group's head / PI (`headname`).
    head_email : str
        The email address of the group's head / PI (`heademail`).
    billing_info : pyppms.billing.PpmsBillingInformation
        The group's billing information (derived from field `unitbcode`). Note
        that billing codes in PPMS exist at three levels: project, user, group
        (in descending priority).
    department : str
        The group's department.
    institution : str
        The group's institution.
    address : str
        The group's postal address.
    affiliation : str
        The group's affiliation
    external : bool
        The group's _external_ status (`ext`).
    active : bool
        The `active` state of the group account in PPMS.
    admin_name : str
        The name of the group's administrative person (`admname`).
    admin_email : str
        The email address of the group's administrative person (`admemail`).

    Notes
    -----
    - The PUMAPI response contains two extra data fields at the end that are not
      present in the header line. As they were empty in all responses received
      from real PUMAPI instances, they will be ignored.
    - The meaning of the following fields is unclear or misleading, hence they
      will be ignored as well:
      - `creationdate`: this **seems to be** the date of the last update,
        despite its label - discarded until further clarification.
    """

    def __init__(self, response_text):
        """Initialize the group object.

        Parameters
        ----------
        response_text : str
            The text returned by a PUMAPI `getgroup` call.
        """
        details = dict_from_single_response(response_text, graceful=True)
        self.gid: str = str(details["unitlogin"])
        self.name: str = str(details["unitname"])
        self.head_name: str = str(details["headname"])
        self.head_email: str = str(details["heademail"])
        self.billing_info: PpmsBillingInformation = PpmsBillingInformation(
            str(details["unitbcode"]), "group"
        )
        self.department: str = str(details["department"])
        self.institution: str = str(details["institution"])
        self.address: str = str(details["address"])
        self.affiliation: str = str(details["affiliation"])
        self.external: bool = True if details["ext"] == "true" else False
        self.active: bool = True if details["active"] == "true" else False
        self.admin_name: str = str(details["admname"])
        self.admin_email: str = str(details["admemail"])

        log.trace(
            "PpmsGroup initialized: gid=[{}], name=[{}], head_name=[{}], "
            "billing_info=[{}], department=[{}], institution=[{}] "
            "external=[{}], active=[{}]",
            self.gid,
            self.name,
            self.head_name,
            self.billing_info,
            self.department,
            self.institution,
            self.external,
            self.active,
        )

    def details(self) -> str:
        """Generate a string with details on the group object."""
        return (
            f"gid: {self.gid}, "
            f"name: {self.name}, "
            f"head_name: {self.head_name}, "
            f"department: {self.department}, "
            f"institution: {self.institution}, "
            f"external: {self.external}, "
            f"active: {self.active}"
        )

    def __str__(self) -> str:  # noqa: D105 (undocumented-magic-method)
        return str(self.gid)

    def __eq__(self, other) -> bool:  # noqa: D105 (undocumented-magic-method)
        if not isinstance(other, PpmsGroup):
            return False
        if other is None:
            return False

        return (
            self.gid == other.gid
            and self.name == other.name
            and self.head_name == other.head_name
            and self.head_email == other.head_email
            and self.billing_info == other.billing_info
            and self.department == other.department
            and self.institution == other.institution
            and self.address == other.address
            and self.affiliation == other.affiliation
            and self.external == other.external
            and self.active == other.active
            and self.admin_name == other.admin_name
            and self.admin_email == other.admin_email
        )
