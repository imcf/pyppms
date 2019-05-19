# -*- coding: utf-8 -*-

"""Access Stratocore's PPMS Utility Management API.

Authors: Niko Ehrenfeuchter <nikolaus.ehrenfeuchter@unibas.ch>
         Basil Neff <basil.neff@unibas.ch>
"""

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
        if values[i] == 'true':
            values[i] = True
        if values[i] == 'false':
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
            LOG.warn('Response expected to have exactly two lines: %s', text)
            if not graceful:
                raise ValueError("Invalid response format!")
        header = lines[0].split(',')
        data = lines[1].split(',')
        process_response_values(data)
        if len(header) != len(data):
            msg = 'Splitting CSV data failed'
            LOG.warn('%s, header has %s fields whereas the data has %s fields!',
                     msg, len(header), len(data))
            if not graceful:
                raise ValueError(msg)
            minimum = min(len(header), len(data))
            if minimum < len(header):
                LOG.warn('Discarding header-fields: %s', header[minimum:])
                header = header[:minimum]
            else:
                LOG.warn('Discarding data-fields: %s', data[minimum:])
                data = data[:minimum]

    except Exception as err:
        msg = ('Unable to parse data returned by PUMAPI: %s - ERROR: %s' %
               (text, err))
        LOG.error(msg)
        raise ValueError(msg)

    parsed = dict(zip(header, data))
    return parsed
