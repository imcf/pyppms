"""Module representing bookings / reservations in PPMS."""

import logging
from datetime import datetime

from .common import time_rel_to_abs

LOG = logging.getLogger(__name__)


class PpmsBooking:

    """Object representing a booking (reservation) in PPMS.

    Attributes
    ----------
    username : str
        The user's account / login name the booking is linked to.
    system_id : int
        The PPMS system ID to which this booking refers to.
    starttime : datetime.date
        The booking's starting time.
    endtime : datetime.date or NoneType
        The booking's ending time, can be 'None'.
    session : str
        A string referring to a session ID in PPMS, can be empty.
    """

    def __init__(self, text, booking_type, system_id):
        r"""Initialize the booking object.

        Parameters
        ----------
        text : str
            The response text of a PUMAPI `getbooking` or `nextbooking` request,
            should consist of three lines: username, time_delta, session.
            Example: ``pyppms\n42\n12345\n``
        booking_type : str
            Either ``get`` (for a currently running booking) or ``next`` (for
            the next upcoming booking).
        system_id : int or int-like
            The ID of the system the booking refers to.
        """
        valid = ["get", "next"]
        if booking_type not in valid:
            raise ValueError(
                f"Value for 'booking_type' ({booking_type}) not in {valid}!"
            )

        try:
            lines = text.splitlines()
            starttime = time_rel_to_abs(lines[1])
            endtime = None

            if booking_type == "get":
                endtime = starttime
                starttime = datetime.now().replace(second=0, microsecond=0)

            self.username = lines[0]
            self.system_id = system_id
            self.starttime = starttime
            self.endtime = endtime
            self.session = lines[2]
        except Exception as err:
            LOG.error("Parsing booking response failed (%s), text was:\n%s", err, text)
            raise

        LOG.debug(
            "PpmsBooking initialized: username=[%s], system=[%s], "
            "reservation start=[%s] end=[%s]",
            username,
            system_id,
            starttime,
            endtime,
        )

    @classmethod
    def from_runningsheet(cls, entry, system_id, username, date):
        """Alternative constructor using a (parsed) getrunningsheet response.

        Parameters
        ----------
        entry : dict
            One item of a 'getrunningsheet' response processed by the
            parse_multiline_response function.
        system_id : int or int-like
            The system ID to which this booking refers to.
        username : str
            The user's account / login name for PPMS.
        date : datetime.date
            The date object of the *DAY* this booking is linked to. Note that
            the exact start- and end-time of the booking will be taken from the
            ``entry`` dict above.

        Returns
        -------
        PpmsBooking
            The object constructed with the parsed response.
        """
        try:
            booking = cls(
                username=username, system_id=system_id, starttime=date, endtime=date
            )
            booking.starttime_fromstr(entry["Start time"], date)
            booking.endtime_fromstr(entry["End time"], date)
        except Exception as err:
            LOG.error(
                "Parsing runningsheet entry failed (%s), text was:\n%s", err, entry
            )
            raise

        return booking

    def starttime_fromstr(self, time_str, date=None):
        """Change the starting time and / or day of a booking.

        Parameters
        ----------
        time_str : str
            The new starting time in format ``%H:%M:%S`` (e.g. ``13:45:00``).
        date : datetime.date, optional
            The new starting day, by default ``None`` which will result in the
            current date to be used.
        """
        if date is None:
            date = datetime.now()
        start = date.replace(
            hour=int(time_str.split(":")[0]),
            minute=int(time_str.split(":")[1]),
            second=0,
            microsecond=0,
        )
        self.starttime = start
        LOG.debug("Updated booking starttime: %s", self)

    def endtime_fromstr(self, time_str, date=None):
        """Change the ending time and / or day of a booking.

        Parameters
        ----------
        time_str : str
            The new ending time in format ``%H:%M:%S`` (e.g. ``13:45:00``).
        date : datetime.date, optional
            The new ending day, by default ``None`` which will result in the
            current date to be used.
        """
        if date is None:
            date = datetime.now()
        end = date.replace(
            hour=int(time_str.split(":")[0]),
            minute=int(time_str.split(":")[1]),
            second=0,
            microsecond=0,
        )
        self.endtime = end
        LOG.debug("Updated booking endtime: %s", self)

    def __str__(self):
        msg = (
            f"username: {self.username} - system: {self.system_id} - "
            f"reservation start / end: [ {self.starttime} / {self.endtime} ]"
        )
        if self.session:
            msg += f" - session: {self.session}"

        return msg
