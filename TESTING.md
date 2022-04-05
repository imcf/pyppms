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

To generate an API key a so-called "Super-Admin" needs to log on to your PPMS instance,
navigate to `My PPMS` using the drop-down menu on the top-right, then selecting `API`
from the top bar and finally clicking the `Create PUMAPI key` button.

### PPMS Preparations

The tests assume certain users and systems to exist in the PUMAPI instance used
for testing. Currently there is not yet a mechanism to automatically create
those items unfortunately - sorry, might come at some point...

The details on how to set them up can be looked up in the corresponding test
fixtures in [`conftest.py`](/tests/conftest.py). Basically the following steps
need to be done manually in the PPMS instance to be used for testing:

- Create a group with the settings from `group_details`.
- Create a regular user as denoted in `user_details_raw` that is a member of the
  previously created group.
- Create a user that has *administrator permissions* with the details denoted in
  `user_admin_details_raw`, also make sure it is a member of the same group.
- Create a system using the details from `system_details_raw`, and make sure the
  regular user created above has permissions to book it. **NOTE**: currently the
  system ID is hardcoded in that fixture, this will need to be adapted to your
  PPMS instance and should be done in a smarter way in general...
- Create a booking for the regular user on that system that is at some point in
  the future.

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
- TODO: run a test that creates
  `tests/cached_responses/stage_0/getusers/active--true.txt`
- check if the result contains `pyppms` and `pyppms-adm` (mandatory)
- reset the file to the state in git
- rename `tests/mocked_responses/get_users_with_access_to_system__invalid_response/getsysrights/id--31.txt` to match the ID of the above created system


## Running Tests

Once everything is set up, you should be good to simply type `poetry run pytest`
on the command line, the output should look something like this:

```text
pytest -rs
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
