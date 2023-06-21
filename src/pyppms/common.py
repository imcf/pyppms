"""Common functions related to Stratocore's PPMS Utility Management API."""

# pylint: disable-msg=fixme

from datetime import datetime, timedelta
import csv
from io import StringIO

from loguru import logger as log

from .exceptions import NoDataError


def process_response_values(values):
    """Process (in-place) a list of strings, remove quotes, detect boolean etc.

    Check all (str) elements of the given list, remove surrounding double-quotes
    and convert 'true' / 'false' strings into Python booleans.

    Parameters
    ----------
    values : list(str)
        The list of strings that should be processed.

    Returns
    -------
    None
        Nothing is returned, the list's element are processed in-place.
    """
    # tell pylint that there is no real gain using enumerate here:
    # pylint: disable-msg=consider-using-enumerate
    for i in range(len(values)):
        values[i] = values[i].strip('"')
        if values[i] == "true":
            values[i] = True
        if values[i] == "false":
            values[i] = False


def dict_from_single_response(text, graceful=True):
    """Parse a two-line CSV response from PUMAPI and create a dict from it.

    Parameters
    ----------
    text : str
        The PUMAPI response with two lines: a header line and one data line.
    graceful : bool, optional
        Whether to continue in case the response text is inconsistent, i.e.
        having different number of fields in the header line and the data line,
        by default True. In graceful mode, any inconsistency detected in the
        data will be logged as a warning, in non-graceful mode they will raise
        an Exception.

    Returns
    -------
    dict
        A dict with the fields of the header line being the keys and the fields
        of the data line being the values. Values are stripped from quotes
        and converted to Python boolean values where applicable.

    Raises
    ------
    ValueError
        Raised when the response text is inconsistent and the `graceful`
        parameter has been set to false, or if parsing fails for any other
        unforeseen reason.
    """

    # check if we got an empty response (only two newlines) and return a dict
    # with two empty strings only
    # TODO: this should probably rather raise a ValueError but we need to test
    # all effects on existing code first!
    if text == "\n\n":
        return {"": ""}
    try:
        lines = list(csv.reader(StringIO(text), delimiter=","))
        if len(lines) != 2:
            log.warning("Response expected to have exactly two lines: {}", text)
            if not graceful:
                raise ValueError("Invalid response format!")
        header = lines[0]
        data = lines[1]
        process_response_values(data)
        if len(header) != len(data):
            msg = "Parsing CSV failed, mismatch of header vs. data fields count"
            log.warning("{} ({} vs. {})", msg, len(header), len(data))
            if not graceful:
                raise ValueError(msg)
            minimum = min(len(header), len(data))
            if minimum < len(header):
                log.warning("Discarding header-fields: {}", header[minimum:])
                header = header[:minimum]
            else:
                log.warning("Discarding data-fields: {}", data[minimum:])
                data = data[:minimum]

    except Exception as err:
        msg = f"Unable to parse data returned by PUMAPI: {text} - ERROR: {err}"
        log.error(msg)
        raise ValueError(msg) from err

    parsed = dict(zip(header, data))
    return parsed


def parse_multiline_response(text, graceful=True):
    """Parse a multi-line CSV response from PUMAPI.

    Parameters
    ----------
    text : str
        The PUMAPI response with two or more lines, where the first line
        contains the header field names and the subsequent lines contain data.
    graceful : bool, optional
        Whether to continue in case the response text is inconsistent, i.e.
        having different number of fields in the header line and the data lines,
        by default True. In graceful mode, any inconsistency detected in the
        data will be logged as a warning, in non-graceful mode they will raise
        an Exception.

    Returns
    -------
    list(dict)
        A list with dicts where the latter ones have the same form as produced
        by the dict_from_single_response() function. May be empty in case the
        PUMAPI response didn't contain any useful data. Note that when graceful
        mode is requested, consistency among the dicts is not guaranteed.

    Raises
    ------
    NoDataError
        Raised when the response text was too short (less than two lines) and
        the `graceful` parameter has been set to false.
    ValueError
        Raised when the response text is inconsistent and the `graceful`
        parameter has been set to false, or if parsing fails for any other
        unforeseen reason.
    """
    parsed = []
    try:
        lines = text.splitlines()
        if len(lines) < 2:
            log.info("Response has less than TWO lines: >>>{}<<<", text)
            if not graceful:
                raise NoDataError("Invalid response format!")
            return []

        header = lines[0].split(",")
        for i, entry in enumerate(header):
            header[i] = entry.strip()

        lines_max = lines_min = len(header)
        for line in lines[1:]:
            data = line.split(",")
            process_response_values(data)
            lines_max = max(lines_max, len(data))
            lines_min = min(lines_min, len(data))
            if len(header) != len(data):
                msg = "Parsing CSV failed, mismatch of header vs. data fields count"
                log.warning("{} ({} vs. {})", msg, len(header), len(data))
                if not graceful:
                    raise ValueError(msg)

                minimum = min(len(header), len(data))
                if minimum < len(header):
                    log.warning("Discarding header-fields: {}", header[minimum:])
                    header = header[:minimum]
                else:
                    log.warning("Discarding data-fields: {}", data[minimum:])
                    data = data[:minimum]

            details = dict(zip(header, data))
            # log.debug(details)
            parsed.append(details)

        if lines_min != lines_max:
            msg = (
                "Inconsistent data detected, not all dicts will have the "
                "same number of elements!"
            )
            log.warning(msg)

    except NoDataError as err:
        raise err

    except Exception as err:
        msg = f"Unable to parse data returned by PUMAPI: {text} - ERROR: {err}"
        log.error(msg)
        raise ValueError(msg) from err

    return parsed


def time_rel_to_abs(minutes_from_now):
    """Convert a relative time given in minutes from now to a datetime object.

    Parameters
    ----------
    minutes_from_now : int or int-like
        The relative time in minutes to be converted.

    Returns
    -------
    datetime
        The absolute time point as a datetime object.
    """
    now = datetime.now().replace(second=0, microsecond=0)
    abstime = now + timedelta(minutes=int(minutes_from_now))
    return abstime


def fmt_time(time):
    """Format a `datetime` or `None` object to string.

    This is useful to apply it to booking times as they might be `None` e.g. in
    case they have been created from a "nextbooking" response.

    Parameters
    ----------
    time : datetime.datetime or None

    Returns
    -------
    str
        The formatted time, or a specific string in case the input was `None`.
    """
    if time is None:
        return "===UNDEFINED==="
    return datetime.strftime(time, "%Y-%m-%d %H:%M")
