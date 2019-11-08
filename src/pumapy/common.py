"""Common functions related to Stratocore's PPMS Utility Management API."""

# pylint: disable-msg=fixme

from datetime import datetime, timedelta
import logging

LOG = logging.getLogger(__name__)


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
    # TODO: use Python's CSV parser that is much more robust than the manual
    # string splitting approach below which will fail as soon as a field
    # contains a comma!
    try:
        lines = text.splitlines()
        if len(lines) != 2:
            LOG.warning("Response expected to have exactly two lines: %s", text)
            if not graceful:
                raise ValueError("Invalid response format!")
        header = lines[0].split(",")
        data = lines[1].split(",")
        process_response_values(data)
        if len(header) != len(data):
            msg = "Parsing CSV failed, mismatch of header vs. data fields count"
            LOG.warning("%s (%s vs. %s)", msg, len(header), len(data))
            if not graceful:
                raise ValueError(msg)
            minimum = min(len(header), len(data))
            if minimum < len(header):
                LOG.warning("Discarding header-fields: %s", header[minimum:])
                header = header[:minimum]
            else:
                LOG.warning("Discarding data-fields: %s", data[minimum:])
                data = data[:minimum]

    except Exception as err:
        msg = "Unable to parse data returned by PUMAPI: %s - ERROR: %s" % (text, err)
        LOG.error(msg)
        raise ValueError(msg)

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
        by the dict_from_single_response() function. Note that when graceful
        mode is requested, consistency among the dicts is not guaranteed.

    Raises
    ------
    ValueError
        Raised when the response text is inconsistent and the `graceful`
        parameter has been set to false, or if parsing fails for any other
        unforeseen reason.
    """
    parsed = list()
    try:
        lines = text.splitlines()
        if len(lines) < 2:
            LOG.warning("Response expected to have two or more lines: %s", text)
            if not graceful:
                raise ValueError("Invalid response format!")
            return parsed

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
                LOG.warning("%s (%s vs. %s)", msg, len(header), len(data))
                if not graceful:
                    raise ValueError(msg)

                minimum = min(len(header), len(data))
                if minimum < len(header):
                    LOG.warning("Discarding header-fields: %s", header[minimum:])
                    header = header[:minimum]
                else:
                    LOG.warning("Discarding data-fields: %s", data[minimum:])
                    data = data[:minimum]

            details = dict(zip(header, data))
            # LOG.debug(details)
            parsed.append(details)

        if lines_min != lines_max:
            msg = (
                "Inconsistent data detected, not all dicts will have the "
                "same number of elements!"
            )
            LOG.warning(msg)

    except Exception as err:
        msg = "Unable to parse data returned by PUMAPI: %s - ERROR: %s" % (text, err)
        LOG.error(msg)
        raise ValueError(msg)

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
