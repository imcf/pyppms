"""Tests for the 'ppms.common' module."""

# pylint: disable-msg=len-as-condition

from datetime import datetime, timedelta

import pytest

from pumapy import common

__author__ = "Niko Ehrenfeuchter"
__copyright__ = __author__
__license__ = "gpl3"


def test_dict_from_single_response():
    """Test the two-line-response-to-dict converter."""
    valid = 'one,two,thr,fou,fiv,six,sev\nasdf,"qwr",true,"true",false,,"false"'
    valid_dict = {
        "one": "asdf",
        "two": "qwr",
        "thr": True,
        "fou": True,
        "fiv": False,
        "six": "",
        "sev": False,
    }

    # testing valid input:
    parsed = common.dict_from_single_response(valid, graceful=False)
    assert parsed == valid_dict

    # testing input with too few lines:
    with pytest.raises(ValueError):
        common.dict_from_single_response("\n", graceful=True)

    # testing empty input:
    assert common.dict_from_single_response("\n\n") == {"": ""}

    # testing input with too many lines, otherwise valid:
    valid_graceful = valid + "\nsomething in line three\nand four!"
    with pytest.raises(ValueError):
        common.dict_from_single_response(valid_graceful, graceful=False)
    parsed = common.dict_from_single_response(valid_graceful, graceful=True)
    assert parsed == valid_dict

    # testing input with too many header fields:
    invalid_header = "zero," + valid
    parsed = common.dict_from_single_response(invalid_header, graceful=True)
    with pytest.raises(ValueError):
        common.dict_from_single_response(invalid_header, graceful=False)

    # testing input with too many data fields:
    invalid_data = valid + ',"eight"'
    parsed = common.dict_from_single_response(invalid_data, graceful=True)
    with pytest.raises(ValueError):
        common.dict_from_single_response(invalid_data, graceful=False)


def test_process_response_values():
    """Test the data-fields-processing function."""
    values = ['"doubles"', "'singles'", "0", "'1'", '"2"', "true", "false"]
    results = ["doubles", "'singles'", "0", "'1'", "2", True, False]

    common.process_response_values(values)

    for i, val in enumerate(values):
        print("val (%s) == results[%s] (%s)" % (val, i, results[i]))
        assert val == results[i]

    common.process_response_values([])

    with pytest.raises(TypeError):
        common.process_response_values("a string")

    with pytest.raises(TypeError):
        common.process_response_values(None)


def test_parse_multiline_response():
    """Test the multiline response parsing function."""
    # testing empty input, non-graceful:
    with pytest.raises(ValueError):
        common.parse_multiline_response("", graceful=False)

    # testing empty input, graceful:
    assert len(common.parse_multiline_response("", graceful=True)) == 0

    # testing valid input:
    valid = 'one,two,thr\nasdf,"qwr",true\n"true","nothing","eleven"'
    valid_parsed = [
        {"one": "asdf", "two": "qwr", "thr": True,},
        {"one": True, "two": "nothing", "thr": "eleven",},
    ]
    assert common.parse_multiline_response(valid, graceful=True) == valid_parsed

    # testing input with too many header fields:
    invalid_header = "zero," + valid
    parsed = common.parse_multiline_response(invalid_header, graceful=True)
    print(parsed)
    with pytest.raises(ValueError):
        common.parse_multiline_response(invalid_header, graceful=False)

    # testing input with too many data fields:
    invalid_data = valid + ',"evenmore"'
    parsed = common.parse_multiline_response(invalid_data, graceful=True)
    print(parsed)
    with pytest.raises(ValueError):
        common.parse_multiline_response(invalid_data, graceful=False)

    # testing leading / trailing whitespace in header fields:
    text = 'foo , bar\n"some","thing"'
    expected = {"foo": "some", "bar": "thing"}
    parsed = common.parse_multiline_response(text)
    assert parsed[0].keys() == expected.keys()
    text = 'foo,bar\n"some","thing"'
    parsed = common.parse_multiline_response(text)
    assert parsed[0].keys() == expected.keys()


def test_time_rel_to_abs():
    """Test the relatitve-to-absolute timestamp converter function."""
    expected = datetime.now().replace(second=0, microsecond=0)

    converted = common.time_rel_to_abs(0)
    assert converted == expected

    delta_min = 23
    expected += timedelta(minutes=delta_min)

    converted = common.time_rel_to_abs(delta_min)
    assert converted == expected

    converted = common.time_rel_to_abs(str(delta_min))
    assert converted == expected

    with pytest.raises(ValueError):
        common.time_rel_to_abs("seven")
