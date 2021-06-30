#!/usr/bin/env python

"""Example script on how to use the 'pumapy' package."""

# pylint: disable-msg=multiple-imports
# pylint: disable-msg=wrong-import-order

import pumapy, pumapyconf


conn = pumapy.ppms.PpmsConnection(
    url=pumapyconf.PUMAPI_URL,
    api_key=pumapyconf.PPMS_API_KEY,
    timeout=pumapyconf.TIMEOUT,
)


conn.new_user(
    "pumapy",
    "Python",
    "PumAPI",
    "pumapy@python-facility.example",
    "pumapy_group",
    phone="+98 (76) 54 3210",
)

conn.new_user(
    "pumapy-adm",
    "Python",
    "PumAPI (Administrator)",
    "pumapy-adm@python-facility.example",
    "pumapy_group",
    phone="+98 (76) 54 3112",
)
