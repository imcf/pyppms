"""Tests for the PpmsBooking class."""

import pytest
from datetime import datetime
from pumapy.booking import PpmsBooking

__author__ = "Niko Ehrenfeuchter"
__copyright__ = __author__
__license__ = "gpl3"


FMT_DATE = r'%Y-%m-%d'
FMT_TIME = r'%H:%M:%S'
FMT = '%s %s' % (FMT_DATE, FMT_TIME)
DAY = '2019-05-18'
TIME_START = '12:30:00'
TIME_END = '13:15:00'
START = '%s %s' % (DAY, TIME_START)
END = '%s %s' % (DAY, TIME_END)

USERNAME = 'ppmsuser'
SYS_ID = '42'
EXPECTED = 'username: %s - system: %s - ' % (USERNAME, SYS_ID)
EXPECTED += 'reservation_start: %s - reservation_end: %s'


def create_booking(username=USERNAME,
                   system_id=SYS_ID,
                   starttime=datetime.strptime(START, FMT),
                   endtime=datetime.strptime(END, FMT)):
    """Helper function to create a PpmsBooking object with default values.

    Returns
    -------
    PpmsBooking
    """
    return PpmsBooking(username, system_id, starttime, endtime)


def test_ppmsbooking():
    """Test the PpmsBooking constructor."""
    # run constructor with 'system_id' being a str
    booking = create_booking()
    assert booking.__str__() == EXPECTED % (START, END)

    # run constructor with 'system_id' being an int
    booking = create_booking(system_id=42)
    assert booking.__str__() == EXPECTED % (START, END)

    # run constructor with 'system_id' being something not int-like
    with pytest.raises(ValueError):
        create_booking(system_id='eleven')


def test_starttime_fromstr__time():
    """Test changing the starting time of a booking."""
    booking = create_booking()

    newtime = '12:45:00'
    booking.starttime_fromstr(newtime, date=datetime.strptime(START, FMT))

    newstart = '%s %s' % (DAY, newtime)
    assert booking.__str__() == EXPECTED % (newstart, END)


def test_starttime_fromstr__date():
    """Test changing the starting date of a booking."""
    booking = create_booking()

    newdate = '2019-04-01'
    newtime = '12:45:00'
    startdate = datetime.strptime(newdate, FMT_DATE)
    booking.starttime_fromstr(newtime, startdate)

    newstart = '%s %s' % (newdate, newtime)
    assert booking.__str__() == EXPECTED % (newstart, END)


def test_endtime_fromstr__time():
    """Test changing the ending time of a booking."""
    booking = create_booking()

    newtime = '12:45:00'
    booking.endtime_fromstr(newtime, date=datetime.strptime(START, FMT))

    newend = '%s %s' % (DAY, newtime)
    assert booking.__str__() == EXPECTED % (START, newend)


def test_endtime_fromstr__date():
    """Test changing the ending date of a booking."""
    booking = create_booking()

    newdate = '2019-06-01'
    newtime = '12:45:00'
    enddate = datetime.strptime(newdate, FMT_DATE)
    booking.endtime_fromstr(newtime, enddate)

    newend = '%s %s' % (newdate, newtime)
    assert booking.__str__() == EXPECTED % (START, newend)


def test_booking_with_session():
    """Test adding a session string to a booking."""
    session = '123456789'
    booking = create_booking()

    booking.session = session
    expected = EXPECTED + ' - session: ' + session

    assert booking.__str__() == expected % (START, END)
