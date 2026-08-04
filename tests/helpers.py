"""Helper methods for pyppms unit tests."""

import os.path

from loguru import logger

import pyppmsconf


def switch_cache_post_change(conn, suffix):
    """Update the connection's cache path to reflect changes to responses.

    This helper function switches the path used for caching the connection's
    responses to a different (post-update) location, which is required when
    running the same request (again) will result in a different response e.g.
    after updating PUMAPI's state (for example when adjusting booking
    permissions or similar).

    Parameters
    ----------
    conn : ppms.PpmsConnection
        The PPMS connection object.
    suffix : str (or str-like)
        The suffix used to distinguish the different stages, usually an index
        number like `"1"` or similar.
    """
    new_path = os.path.join(pyppmsconf.CACHE_PATH, f"stage_{suffix}")
    logger.debug("Switching response cache path to reflect a PPMS status change.")
    logger.debug(f"New cache path: [{new_path}]")
    conn.cache_path = new_path


def switch_cache_mocks(conn, mocktype, message="<NOT SPECIFIED>"):
    """Update the connection's cache path to use mocked responses.

    Use mocked responses during tests to simulate various invalid replies from PUMAPI
    that will cause downstream errors during parsing etc.

    Parameters
    ----------
    conn : ppms.PpmsConnection
        The PPMS connection object.
    mocktype : str
        Used to distinguish various types of mocks, e.g. ``key_error`` for responses
        that will trigger a `KeyError` exception in *pyppms*.
    message : str, optional
        An explanatory message that will be logged with switching the cache path.
    """
    new_path = os.path.join(pyppmsconf.MOCKS_PATH, mocktype)
    logger.debug(f"Switching response cache path for reason:\n>>> {message} <<<")
    logger.debug(f"New cache path: [{new_path}]")
    conn.cache_path = new_path
