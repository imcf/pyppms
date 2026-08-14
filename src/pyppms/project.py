"""Module representing a project in PPMS."""

from loguru import logger as log


class PpmsProject:
    """Object representing a project in PPMS.

    Attributes
    ----------
    id : int
        The project ID in PPMS.
    name : str
        The name of the project.
    core_facility_ref : int
        The core facility the project is associated to.
    phase : int
        The project phase.
    active : bool
        The ``active`` state of the project in PPMS.
    billing_code : str
        Financial billing code used for the project.
    affiliation : str
        The project's affiliation.
    type : str
        The project type.
    group : str
        The group associated with the project.
    description : str
        The project's description.

    Notes
    -----
    Raw CSV header fields from PUMAPI:

    - `Core facility ref.`
    - `Project name`
    - `Phase`
    - `Active`
    - `Bcode`
    - `Project ref.`
    - `Affiliation`
    - `Project Type`
    - `Project Group`
    - `Descr`
    """

    def __init__(self, details):
        """Initialize the project object.

        Parameters
        ----------
        details : dict
            A dict with the parsed response from a `getprojects` request.
        """

        self.id = int(details["Project ref."])
        self.name = details["Project name"]
        self.core_facility_ref = details["Core facility ref."]
        self.phase = details["Phase"]
        self.active = details["Active"]
        self.billing_code = details["Bcode"]
        self.affiliation = details["Affiliation"]
        self.type = details["Project Type"]
        self.group = details["Project Group"]
        self.description = details["Descr"]

        log.trace(f"PpmsProject initialized: {self.details()}")

    def details(self):
        """Generate a string with details on the project object."""
        return (
            f"id=[{self.id}], "
            f"name=[{self.name}], "
            f"core_facility_ref=[{self.core_facility_ref}], "
            f"active=[{self.active}], "
            f"type=[{self.type}], "
            f"group=[{self.group}], "
            f"phase=[{self.phase}], "
            f"billing_code=[{self.billing_code}], "
            f"affiliation=[{self.affiliation}], "
            f"description=[{self.description}]"
        )

    def __str__(self):  # noqa: D105 (undocumented-magic-method)
        return f"PpmsProject [{self.id}] '{self.name}'"
