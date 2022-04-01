# Testing PUMAPY

Automated testing has been a core design goal for `pumapy`, aiming for a
coverage of 100%.

## Requirements

Testing is performed using [pytest][t1]. Almost all *request-response* tests
(basically anything in the [PpmsConnection](/src/pumapy/ppms.py) class) do **NOT**
require a valid API-key or a connection to a PUMAPI instance but can be performed using
the built-in response-caching mechanism combined with the mocks and cached responses
provided with the tests. The only exception are those tests that do not make sense in
such a scenario (i.e. that do test if interaction with an actual PUMAPI instance is
effectively working). Those tests have to be requested explicitly by adding the
"`--online`" flag to the pytest-call.

### Configuration and API Key

To run the tests, copy the example [`pumapyconf.py`](/resources/examples/pumapyconf.py)
file to the `/tests/` directory. For the online tests, please edit it according to your
instance and key - the offline tests work without config modifications.

To generate an API key a so-called "Super-Admin" needs to log on to your PPMS instance,
navigate to `My PPMS` using the drop-down menu on the top-right, then selecting `API`
from the top bar and finally clicking the `Create PUMAPI key` button.

### PPMS Preparations

The tests assume certain users and systems to exist in the PUMAPI instance used
for testing. Currently there is not yet a mechanism to automatically create
those items unfortunately - sorry, working on it...

The details on how to set them up can be looked up in the corresponding test
fixtures in [`conftest.py`](/tests/conftest.py):

- `user_details_raw`
- `user_admin_details_raw`
- `group_details`
- `system_details_raw`

### Virtualenv Installation

It is strongly recommended to create a virtualenv for running the tests and
install `pumapy` there. Here are the steps to do this using
[virtualenvwrapper][2]:

```bash
mkvirtualenv pumapy-testing
pip install pytest pytest-cov
pip install --editable .
```

## Running Tests

Once everything is set up, you should be good to simply type `pytest` on the
command line and give it a go. The output should look something like this:

```text
pytest -rs
============================ test session starts =============================
platform linux -- Python 3.7.3, pytest-5.2.2, py-1.8.0, pluggy-0.13.0
rootdir: /tmp/imcf/pumapy-testing, inifile: pytest.ini
plugins: cov-2.8.1
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
[2]: https://virtualenvwrapper.readthedocs.io/en/latest/
