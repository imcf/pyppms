"""Tests for the 'ppms.common' module."""

import pytest

from pumapy import common

__author__ = "Niko Ehrenfeuchter"
__copyright__ = __author__
__license__ = "gpl3"


def test_dict_from_single_response():
    """Test the two-line-response-to-dict converter."""
    valid = 'one,two,thr,fou,fiv,six,sev\nasdf,"qwr",true,"true",false,,"false"'
    valid_dict = {
        'one': 'asdf',
        'two': 'qwr',
        'thr': True,
        'fou': True,
        'fiv': False,
        'six': '',
        'sev': False,
    }

    # testing valid input:
    parsed = common.dict_from_single_response(valid, graceful=False)
    assert parsed == valid_dict

    # testing input with too few lines:
    with pytest.raises(ValueError):
        common.dict_from_single_response('\n', graceful=True)

    # testing empty input:
    assert common.dict_from_single_response('\n\n') == {'': ''}

    # testing input with too many lines, otherwise valid:
    valid_graceful = valid + "\nsomething in line three\nand four!"
    with pytest.raises(ValueError):
        common.dict_from_single_response(valid_graceful, graceful=False)
    parsed = common.dict_from_single_response(valid_graceful, graceful=True)
    assert parsed == valid_dict

    # testing input with too many header fields:
    invalid_header = 'zero,' + valid
    parsed = common.dict_from_single_response(invalid_header, graceful=True)
    with pytest.raises(ValueError):
        common.dict_from_single_response(invalid_header, graceful=False)

    # testing input with too many data fields:
    invalid_data = valid + ',"eight"'
    parsed = common.dict_from_single_response(invalid_data, graceful=True)
    with pytest.raises(ValueError):
        common.dict_from_single_response(invalid_data, graceful=False)
