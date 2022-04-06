"""Load and return PPMS values from YAML."""

from os.path import abspath, dirname, join

import yaml


def values():
    """Load YAML and return values."""
    settings_file = join(abspath(dirname(__file__)), "values.yml")

    with open(settings_file, "r", encoding="utf-8") as infile:
        settings = yaml.safe_load(infile)

    return settings
