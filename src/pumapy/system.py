# -*- coding: utf-8 -*-

"""Module representing bookable systems in PPMS."""

import logging

LOG = logging.getLogger(__name__)


class PpmsSystem(object):

    """Object representing a bookable system in PPMS."""

    # TODO: merge the alternative constructor(s) into __init__() (where applicable)
    # TODO: document instance attributes

    def __init__(self, system_id, name, localisation, system_type,
                 core_facility_ref, schedules, active, stats, bookable,
                 autonomy_required, autonomy_required_after_hours):
        """Initialize the system object.

        Parameters
        ----------
        system_id : int or int-like
            The ID of the system in PPMS (the system's unique identifier).
        name : str
            The system's (human friendly) name.
        localisation : str
            The location of the system, corresponds to the "Room" field in the
            PPMS web interface.
        system_type : str
            The "System Type" field in PPMS, e.g. "Confocal Microscopes" or
            "Virtual Machine class PowerWorkstations"
        core_facility_ref : str
            The core facility reference of the system.
        schedules : bool
            Flag indicating whether to list this system in the read-only
            resources and schedules pages of PPMS.
        active : bool
            Flag indicating whether the system is active in PPMS.
        stats : bool
            Flag indicating whether to integrate this system in the global usage
            statistics of PPMS or not.
        bookable : bool
            Flag indicating whether the system is actually bookable in PPMS. A
            system that's not bookable can still be used in incident management.
        autonomy_required : bool
            Flag indiciating whether explicit permissions are required for a
            user for being allowed to book the system. Corresponds to the field
            "User right/training required" in the PPMS web interface.
        autonomy_required_after_hours : bool
            Corresponds to the field "User right/training required only after
            hours" in the PPMS web interface. Unfortunately there is no
            description given what that actually means - probably it refers to
            the "after hours" / "non-peak hours".
        """
        try:
            self.system_id = int(system_id)
        except ValueError as err:
            LOG.error('Unable to parse system ID: %s - %s', system_id, err)
            raise

        self.name = name
        self.localisation = localisation
        self.system_type = system_type
        self.core_facility_ref = core_facility_ref
        self.schedules = schedules
        self.active = active
        self.stats = stats
        self.bookable = bookable
        self.autonomy_required = autonomy_required
        self.autonomy_required_after_hours = autonomy_required_after_hours
        self.machine_catalogue = None
        LOG.debug('PpmsSystem initialized: id=%s, name=[%s], localisation=[%s], '
                  'system_type=[%s]', system_id, name, localisation,
                  system_type)
        # LOG.debug('PpmsSystem details: core_facility_ref=%s, schedules=%s, '
        #           'active=%s, stats=%s, bookable=%s, autonomy_required=%s, '
        #           'autonomy_required_after_hours=%s', core_facility_ref,
        #           schedules, active, stats, bookable, autonomy_required,
        #           autonomy_required_after_hours)

    @classmethod
    def from_parsed_response(cls, details):
        """Alternative constructor using a parsed dict with system details.

        Parameters
        ----------
        details : dict
            A dict with the parsed response from a `getsystems` request.

        Returns
        -------
        PpmsSystem
            The object constructed with the given details.
        """
        system = cls(
            details['System id'],
            details['Name'],
            details['Localisation'],
            details['Type'],
            details['Core facility ref'],
            details['Schedules'],
            details['Active'],
            details['Stats'],
            details['Bookable'],
            details['Autonomy Required'],
            details['Autonomy Required After Hours']
        )
        return system

    def __str__(self):
        return ('system_id: %s, name: %s, localisation: %s, system_type: %s, '
                'core_facility_ref: %s, schedules: %s, active: %s, '
                'stats: %s, bookable: %s, autonomy_required: %s, '
                'autonomy_required_after_hours: %s' %
                (self.system_id, self.name, self.localisation, self.system_type,
                 self.core_facility_ref, self.schedules, self.active,
                 self.stats, self.bookable, self.autonomy_required,
                 self.autonomy_required_after_hours))
