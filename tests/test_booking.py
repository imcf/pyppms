"""Tests for the PpmsBooking class."""

from datetime import datetime, timedelta
import pytest

from pumapy.booking import PpmsBooking
from pumapy.common import time_rel_to_abs, parse_multiline_response

__author__ = "Niko Ehrenfeuchter"
__copyright__ = __author__
__license__ = "gpl3"


FMT_DATE = r"%Y-%m-%d"
FMT_TIME = r"%H:%M:%S"
FMT = "%s %s" % (FMT_DATE, FMT_TIME)
DAY = "2019-05-18"
TIME_START = "12:30:00"
TIME_END = "13:15:00"
START = "%s %s" % (DAY, TIME_START)
END = "%s %s" % (DAY, TIME_END)

USERNAME = "ppmsuser"
SYS_ID = "42"
EXPECTED = "username: %s - system: %s - " % (USERNAME, SYS_ID)
EXPECTED += "reservation start / end: [ %s / %s ]"


def create_booking(
    username=USERNAME,
    system_id=SYS_ID,
    starttime=datetime.strptime(START, FMT),
    endtime=datetime.strptime(END, FMT),
):
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
        create_booking(system_id="eleven")


def test_starttime_fromstr__time():
    """Test changing the starting time of a booking."""
    booking = create_booking()

    newtime = "12:45:00"
    booking.starttime_fromstr(newtime, date=datetime.strptime(START, FMT))

    newstart = "%s %s" % (DAY, newtime)
    assert booking.__str__() == EXPECTED % (newstart, END)


def test_starttime_fromstr__date():
    """Test changing the starting date of a booking."""
    booking = create_booking()

    newdate = "2019-04-01"
    newtime = "12:45:00"
    startdate = datetime.strptime(newdate, FMT_DATE)
    booking.starttime_fromstr(newtime, startdate)

    newstart = "%s %s" % (newdate, newtime)
    assert booking.__str__() == EXPECTED % (newstart, END)

    # test with date set to 'None' (resulting in current date to be used)
    booking.starttime_fromstr(newtime, date=None)
    newstart = "%s %s" % (datetime.now().strftime(FMT_DATE), newtime)
    assert booking.__str__() == EXPECTED % (newstart, END)


def test_endtime_fromstr__time():
    """Test changing the ending time of a booking."""
    booking = create_booking()

    newtime = "12:45:00"
    booking.endtime_fromstr(newtime, date=datetime.strptime(START, FMT))

    newend = "%s %s" % (DAY, newtime)
    assert booking.__str__() == EXPECTED % (START, newend)


def test_endtime_fromstr__date():
    """Test changing the ending date of a booking."""
    booking = create_booking()

    newdate = "2019-06-01"
    newtime = "12:45:00"
    enddate = datetime.strptime(newdate, FMT_DATE)
    booking.endtime_fromstr(newtime, enddate)

    newend = "%s %s" % (newdate, newtime)
    assert booking.__str__() == EXPECTED % (START, newend)

    # test with date set to 'None' (resulting in current date to be used)
    booking.endtime_fromstr(newtime, date=None)
    newend = "%s %s" % (datetime.now().strftime(FMT_DATE), newtime)
    assert booking.__str__() == EXPECTED % (START, newend)


def test_booking_with_session():
    """Test adding a session string to a booking."""
    session = "123456789"
    booking = create_booking()

    booking.session = session
    expected = EXPECTED + " - session: " + session

    assert booking.__str__() == expected % (START, END)


def test_booking_from_request():
    """Test the alternative from_booking_request() constructor."""
    time_delta = 15
    time_abs = time_rel_to_abs(time_delta)
    response = "%s\n%s\n%s\n" % (USERNAME, time_delta, "some_session_id")

    # test parsing a 'getbooking' response
    booking = PpmsBooking.from_booking_request(response, "get", SYS_ID)
    print(booking)
    print(time_abs)
    assert booking.endtime == time_abs

    # test parsing a 'nextbooking' response, note that the booking will not have
    # an endtime then as PUMAPI doesn't provide this information
    booking = PpmsBooking.from_booking_request(response, "next", SYS_ID)
    print(booking)
    print(time_abs)
    assert booking.starttime == time_abs
    assert booking.endtime is None

    # test with an invalid booking type
    with pytest.raises(ValueError):
        PpmsBooking.from_booking_request("", booking_type="", system_id=23)

    # test with an invalid response text
    with pytest.raises(IndexError):
        PpmsBooking.from_booking_request("invalid", "next", SYS_ID)

    # test with an invalid text type
    with pytest.raises(AttributeError):
        PpmsBooking.from_booking_request(23, "next", SYS_ID)


def test_runningsheet(
    runningsheet_response,
    user_details_raw,
    system_details_raw,
    fullname_mapping,
    systemname_mapping,
):
    """Test the PpmsBooking.from_runningsheet() constructor."""
    d_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    d_end = d_start + timedelta(days=1)

    print(fullname_mapping)
    print(runningsheet_response)
    print(systemname_mapping)
    parsed = parse_multiline_response(runningsheet_response)
    for entry in parsed:
        booking = PpmsBooking.from_runningsheet(
            entry=entry,
            system_id=systemname_mapping[entry["Object"]],
            username=fullname_mapping[entry["User"]],
            date=datetime.now(),
        )
        print(booking.__str__())
        assert booking.username == user_details_raw["login"]
        assert booking.system_id == int(system_details_raw["System id"])
        assert booking.starttime > d_start
        assert booking.endtime < d_end
        assert booking.starttime < booking.endtime


def test_runningsheet_fail(runningsheet_response):
    """Test the runningsheet constructor with a malformed dict."""
    parsed = parse_multiline_response(runningsheet_response)
    for entry in parsed:
        entry.pop("Start time")  # required by the constructor, will fail:
        with pytest.raises(Exception):
            # NOTE: system ID and username don't matter here
            PpmsBooking.from_runningsheet(
                entry=entry, system_id=42, username="someone", date=datetime.now()
            )
