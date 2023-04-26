"""Tests for the PpmsBooking class."""

from datetime import datetime, timedelta
import pytest

from pyppms.booking import PpmsBooking
from pyppms.common import time_rel_to_abs, parse_multiline_response


FMT_DATE = r"%Y-%m-%d"
FMT_TIME = r"%H:%M"
FMT = f"{FMT_DATE} {FMT_TIME}"
DAY = datetime.now().strftime(FMT_DATE)
TIME_START = datetime.now().strftime(FMT_TIME)
TIME_END = (datetime.now() + timedelta(minutes=45)).strftime(FMT_TIME)
START = f"{DAY} {TIME_START}"
END = f"{DAY} {TIME_END}"

USERNAME = "ppmsuser"
SYS_ID = "42"
SESSION_ID = "some_session_id"
EXPECTED = f"PpmsBooking(username=[{USERNAME}], system_id=[{SYS_ID}], "
EXPECTED += f"starttime=[%s], endtime=[%s], session=[{SESSION_ID}])"


def create_booking(
    username=USERNAME,
    system_id=SYS_ID,
    session_id=SESSION_ID,
):
    """Helper function to create a PpmsBooking object with default values.

    Returns
    -------
    PpmsBooking
    """
    time_delta = 45
    response = f"{username}\n{time_delta}\n{session_id}\n"
    return PpmsBooking(text=response, booking_type="get", system_id=system_id)


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

    newtime = "12:45"
    booking.starttime_fromstr(newtime, date=datetime.strptime(START, FMT))

    newstart = f"{DAY} {newtime}"
    assert booking.__str__() == EXPECTED % (newstart, END)


def test_starttime_fromstr__date():
    """Test changing the starting date of a booking."""
    booking = create_booking()

    newdate = "2019-04-01"
    newtime = "12:45"
    startdate = datetime.strptime(newdate, FMT_DATE)
    booking.starttime_fromstr(newtime, startdate)

    newstart = f"{newdate} {newtime}"
    assert booking.__str__() == EXPECTED % (newstart, END)

    # test with date set to 'None' (resulting in current date to be used)
    booking.starttime_fromstr(newtime, date=None)
    newstart = f"{datetime.now().strftime(FMT_DATE)} {newtime}"
    assert booking.__str__() == EXPECTED % (newstart, END)


def test_endtime_fromstr__time():
    """Test changing the ending time of a booking."""
    booking = create_booking()

    newtime = "12:45"
    booking.endtime_fromstr(newtime, date=datetime.strptime(START, FMT))

    newend = f"{DAY} {newtime}"
    assert booking.__str__() == EXPECTED % (START, newend)


def test_endtime_fromstr__date():
    """Test changing the ending date of a booking."""
    booking = create_booking()

    newdate = "2019-06-01"
    newtime = "12:45"
    enddate = datetime.strptime(newdate, FMT_DATE)
    booking.endtime_fromstr(newtime, enddate)

    newend = f"{newdate} {newtime}"
    assert booking.__str__() == EXPECTED % (START, newend)

    # test with date set to 'None' (resulting in current date to be used)
    booking.endtime_fromstr(newtime, date=None)
    newend = f"{datetime.now().strftime(FMT_DATE)} {newtime}"
    assert booking.__str__() == EXPECTED % (START, newend)


def test_noendtime_str():
    """Test the booking object string formatting when no end time is set."""
    booking = create_booking()
    booking.endtime = None
    assert "endtime=[===UNDEFINED===]" in booking.__str__()


def test_booking_from_request():
    """Test the alternative from_booking_request() constructor."""
    time_delta = 15
    time_abs = time_rel_to_abs(time_delta)
    response = f'{USERNAME}\n{time_delta}\n"some_session_id"\n'

    # test parsing a 'getbooking' response
    booking = PpmsBooking(response, "get", SYS_ID)
    print(booking)
    print(time_abs)
    assert booking.endtime == time_abs

    # test parsing a 'nextbooking' response, note that the booking will not have
    # an endtime then as PUMAPI doesn't provide this information
    booking = PpmsBooking(response, "next", SYS_ID)
    print(booking)
    print(time_abs)
    assert booking.starttime == time_abs
    assert booking.endtime is None

    # test with an invalid booking type
    with pytest.raises(ValueError):
        PpmsBooking("", booking_type="", system_id=23)

    # test with an invalid response text
    with pytest.raises(IndexError):
        PpmsBooking("invalid", "next", SYS_ID)

    # test with an invalid text type
    with pytest.raises(AttributeError):
        PpmsBooking(23, "next", SYS_ID)


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
