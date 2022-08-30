"""Tests for the package's __init__ file."""

from pyppms import __version__


def test_version():
    """Ensure we're running against the expected package version."""
    assert __version__ == "2.1.0"
