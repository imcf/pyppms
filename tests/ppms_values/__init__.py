"""Load and return PPMS values from YAML."""

from os.path import abspath, dirname, join

import yaml


def values():
    """Load YAML and return values."""
    settings_file = join(abspath(dirname(__file__)), "values.yml")

    with open(settings_file, "r", encoding="utf-8") as infile:
        settings = yaml.safe_load(infile)

    return settings


def api_response_getgroup(values):
    """Generate a pseudo API-response from group-details loaded from YAML.

    Parameters
    ----------
    values : dict
        A dict with group-details as loaded by the `values()` function from a
        the YAML test-data.

    Returns
    -------
    str
    """
    header = (
        "unitlogin,"
        "unitname,"
        "headname,"
        "heademail,"
        "unitbcode,"
        "department,"
        "institution,"
        "address,"
        "affiliation,"
        "ext,"
        "active,"
        "admname,"
        "admemail,"
        "creationdate"
    )
    data = (
        f'"{values["unitlogin"]}",'
        f'"{values["unitname"]}",'
        f'"{values["headname"]}",'
        f'"{values["heademail"]}",'
        f'"{values["unitbcode"]}",'
        f'"{values["department"]}",'
        f'"{values["institution"]}",'
        f'"{values["address"]}",'
        f'"{values["affiliation"]}",'
        f'"{values["ext"]}",'
        f'"{values["active"]}",'
        f'"{values["admname"]}",'
        f'"{values["admemail"]}",'
        f'"{values["creationdate"]}",'
        '"",'
    )
    response = f"{header}\n{data}"
    print(f"pseudo API response for 'getgroup': {response}")
    return response
