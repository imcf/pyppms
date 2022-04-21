"""Module representing bookable systems in PPMS."""

# pylint: disable-msg=too-many-instance-attributes
# pylint: disable-msg=too-many-arguments

import logging

LOG = logging.getLogger(__name__)


class PpmsSystem:

    """Object representing a bookable system in PPMS.

    Attributes
    ----------
    system_id : int
        The ID of the system in PPMS (the system's unique identifier).
    name : str
        The system's (human friendly) name.
    localisation : str
        The location of the system, corresponds to ``Room`` in the PPMS web interface.
    system_type : str
        The ``System Type`` field in PPMS, e.g. "`Confocal Microscopes`" or "`Virtual
        Machine class PowerWorkstations`".
    core_facility_ref : str
        The core facility reference of the system, for example ``2``.
    schedules : bool
        Indicates whether to list this system in the (read-only) resources and schedules
        pages of PPMS.
    active : bool
        Indicates whether the system is active in PPMS.
    stats : bool
        Indicates whether to integrate this system in the PPMS global usage statistics.
    bookable : bool
        Indicates whether the system is actually bookable in PPMS. A system that's not
        bookable can still be used in incident management.
    autonomy_required : bool
        Indicates whether explicit permissions are required for a user for being allowed
        to book the system. Corresponds to the field ``User right/training required`` in
        the PPMS web interface.
    autonomy_required_after_hours : bool
        Corresponds to the field ``User right/training required only after hours`` in
        the PPMS web interface. Unfortunately there is no description given what that
        actually means - probably it refers to the "after hours" / "non-peak hours".
    """

    def __init__(self, details):
        """Initialize the system object.

        Parameters
        ----------
        details : dict
            A dict with the parsed response from a `getsystems` request.
        """
        try:
            self.system_id = int(details["System id"])
        except ValueError as err:
            LOG.error("Unable to parse system ID: %s - %s", details["System id"], err)
            raise

        self.name = details["Name"]
        self.localisation = details["Localisation"]
        self.system_type = details["Type"]
        self.core_facility_ref = details["Core facility ref"]
        self.schedules = details["Schedules"]
        self.active = details["Active"]
        self.stats = details["Stats"]
        self.bookable = details["Bookable"]
        self.autonomy_required = details["Autonomy Required"]
        self.autonomy_required_after_hours = details["Autonomy Required After Hours"]
        LOG.debug(
            "PpmsSystem created: id=%s, name=[%s], localisation=[%s], system_type=[%s]",
            self.system_id,
            self.name,
            self.localisation,
            self.system_type,
        )
        # LOG.debug('PpmsSystem details: core_facility_ref=%s, schedules=%s, '
        #           'active=%s, stats=%s, bookable=%s, autonomy_required=%s, '
        #           'autonomy_required_after_hours=%s', core_facility_ref,
        #           schedules, active, stats, bookable, autonomy_required,
        #           autonomy_required_after_hours)

    def __str__(self):
        return (
            f"system_id: {self.system_id}, "
            f"name: {self.name}, "
            f"localisation: {self.localisation}, "
            f"system_type: {self.system_type}, "
            f"core_facility_ref: {self.core_facility_ref}, "
            f"schedules: {self.schedules}, "
            f"active: {self.active}, "
            f"stats: {self.stats}, "
            f"bookable: {self.bookable}, "
            f"autonomy_required: {self.autonomy_required}, "
            f"autonomy_required_after_hours: {self.autonomy_required_after_hours}"
        )
