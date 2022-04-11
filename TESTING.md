# Testing PyPPMS

Automated testing has been a core design goal for `pyppms`, aiming for a
coverage of 100%.

## Requirements

Testing is performed using [pytest][t1]. Almost all *request-response* tests
(basically anything in the [PpmsConnection](/src/pyppms/ppms.py) class) do **NOT**
require a valid API-key or a connection to a PUMAPI instance but can be performed using
the built-in response-caching mechanism combined with the mocks and cached responses
provided with the tests. The only exception are those tests that do not make sense in
such a scenario (i.e. that do test if interaction with an actual PUMAPI instance is
effectively working). Those tests have to be requested explicitly by adding the
"`--online`" flag to the pytest-call.

### Configuration and API Key

To run the tests, copy the example [`pyppmsconf.py`](/resources/examples/pyppmsconf.py)
file to the `/tests/` directory. For the online tests, please edit it according to your
instance and key - the offline tests work without config modifications.

```bash
cp -v resources/examples/pyppmsconf.py tests/
```

To generate an API key a so-called "Super-Admin" needs to log on to your PPMS instance,
navigate to `My PPMS` using the drop-down menu on the top-right, then selecting `API`
from the top bar and finally clicking the `Create PUMAPI key` button.

### PPMS Preparations

The tests assume certain users and systems to exist in the PUMAPI instance used for
testing. Currently there is not yet a mechanism to automatically create those items
unfortunately - sorry, might come at some point...

For now, simply run the following command to see what has to be configured in your PPMS
test-instance, then log into the web interface with your browser and manually create the
required items:

```bash
poetry run python tests/show_required_ppms_values.py
```

Remarks / additional details:

- All created users should be members of the previously created group.
- After creating the *admin* user, go to the **Admins** page in PPMS, hit the
  *Create a new administrator* button, then select the correct facility and pick
  the user account. In options, simply check the *System management* box, then
  click *Create administrator*.
- After creating all users, navigate to the **Rights** page, select the newly
  created system and pick the *regular* user, then hit the *Create* button to
  assign booking permissions to the user account. Then repeat this for the admin
  user and the *inactive* user (account needs to be set to *active* for adding
  the permissions).
- In addition to the above, four bookings for the *regular* user on the created
  system need to be made on 2028-12-24:
  - from 09:00 to 10:00
  - from 11:00 to 12:00
  - from 13:00 to 14:00
  - from 15:00 to 16:00

### Development installation through poetry

The project is using [poetry][t2] for packaging and dependency management. To set up a
development environment use this command, it will set up a fresh *virtual environment*
with the correct dependencies and install the project in ***editable*** mode:

```bash
git clone https://github.com/imcf/pyppms
cd pyppms
poetry install
```

## Preparing or updating the cached responses

As a test-instance of PPMS usually is a clone of a real one it will contain many
more but the above created objects. To make the tests ignore those "unexpected"
elements, a few filtering steps have to be done each time the local response
cache will be (re-)created.

**TODO** Rough outline **TODO**

- `rm -r tests/cached_responses`
- either run all tests or the selected ones below to (re-)create the cached responses:
  - `tests/test_ppms.py::test_get_systems` (`stage_0/getsystems/response.txt`)
  - `tests/test_ppms.py::test_get_user_experience` (`stage_0/getuserexp/`)
- run tests (TODO: figure out which ones!) that will create
  - `tests/cached_responses/stage_0/getusers/active--true.txt`
  - `tests/cached_responses/stage_0/getadmins/response.txt`
  - `tests/cached_responses/stage_0/getgroup/unitlogin--pyppms_group.txt`
  - `tests/cached_responses/stage_0/getgroups/response.txt`
- `git diff` them to see if the newly cached responses contain are having
  changes that are reasonable (i.e. still contain the created users / systems or
  only differ in creation / booking dates etc.)
- `git restore` those files
- rename `tests/mocked_responses/get_users_with_access_to_system__invalid_response/getsysrights/id--31.txt` to match the ID of the above created system


## Running Tests

Once everything is set up, you should be good to simply type `poetry run pytest`
on the command line, the output should look something like this:

```text
poetry run pytest --online
============================ test session starts =============================
platform linux -- Python 3.8.10, pytest-7.1.1, pluggy-1.0.0
cachedir: .pytest_cache
rootdir: /tmp/imcf/pyppms, configfile: pyproject.toml
plugins: cov-3.0.0
collected 43 items

tests/test_booking.py .........                                        [ 20%]
tests/test_common.py ....                                              [ 30%]
tests/test_ppms.py s.s.......................                          [ 90%]
tests/test_system.py ..                                                [ 95%]
tests/test_user.py ..                                                  [100%]

========================== short test summary info ===========================
SKIPPED [1] tests/test_ppms.py:95: need --online option to run
SKIPPED [1] tests/test_ppms.py:108: need --online option to run
======================= 41 passed, 2 skipped in 0.14s ========================
```

[t1]: https://pytest.org
[t2]: https://python-poetry.org
