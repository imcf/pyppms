# -*- coding: utf-8 -*-

"""Module representing bookings / reservations in PPMS."""

import logging
from datetime import datetime

LOG = logging.getLogger(__name__)


class PpmsBooking(object):

    """Object representing a booking (reservation) in PPMS."""

    def __init__(self, username, system_id, starttime, endtime):
        """Initialize the booking object.

        Parameters
        ----------
        username : str
            The user's account / login name for PPMS.
        system_id : int or int-like
            The system ID to which this booking refers to.
        starttime : datetime.date
            The booking's starting time.
        endtime : datetime.date
            The booking's ending time.
        """
        # TODO: add a constructor dealing with a PUMAPI response
        self.username = username
        self.system_id = int(system_id)
        self.starttime = starttime
        self.endtime = endtime
        self.session = None

        LOG.debug('PpmsBooking initialized: username=[%s], system=[%s], '
                  'reservation start=[%s] end=[%s]', username, system_id,
                  starttime, endtime)

    def starttime_fromstr(self, time_str, date=datetime.now()):
        """Change the starting time and / or day of a booking.

        Parameters
        ----------
        time_str : str
            The new starting time in format '%H:%M:%S' (e.g. "13:45:00").
        date : datetime.date, optional
            The new starting day, by default datetime.now()
        """
        start = date.replace(
            hour=int(time_str.split(':')[0]),
            minute=int(time_str.split(':')[1]),
            second=0,
            microsecond=0
        )
        self.starttime = start
        LOG.debug("Updated booking starttime: %s", self)

    def endtime_fromstr(self, time_str, date=datetime.now()):
        """Change the ending time and / or day of a booking.

        Parameters
        ----------
        time_str : str
            The new ending time in format '%H:%M:%S' (e.g. "13:45:00").
        date : datetime.date, optional
            The new ending day, by default datetime.now()
        """
        end = date.replace(
            hour=int(time_str.split(':')[0]),
            minute=int(time_str.split(':')[1]),
            second=0,
            microsecond=0
        )
        self.endtime = end
        LOG.debug("Updated booking endtime: %s", self)

    def __str__(self):
        msg = ('username: %s - system: %s - reservation_start: %s - '
               'reservation_end: %s' % (self.username, self.system_id,
                                        self.starttime, self.endtime))
        if self.session is not None:
            msg += ' - session: %s' % self.session

        return msg
