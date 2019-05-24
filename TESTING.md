# Testing PUMAPY

Automated testing has been a core design goal for `pumapy`, aiming for a
coverage of 100%.

## Requirements

Testing is performed using [pytest][1]. Currently all *request-response* tests
(basically all of the [PpmsConnection](/src/pumapy/ppms.py) class) do require a
valid API-key and a connection to a PUMAPI instance.

### Configuration and API Key

To run those tests, copy the example
[`pumapyconf.py`](/resources/examples/pumapyconf.py) file to the `/tests/`
directory and edit it according to your instance and key.

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

```pytest
========================== test session starts ==========================
platform linux2 -- Python 2.7.15+, pytest-4.5.0, py-1.8.0, pluggy-0.11.0
rootdir: /home/noenc_ehrenfeu/usr/packages/IMCF/pumapy-testing
plugins: cov-2.7.1
collected 32 items

tests/test_booking.py .......                                     [ 21%]
tests/test_common.py ....                                         [ 34%]
tests/test_ppms.py .................                              [ 87%]
tests/test_system.py ..                                           [ 93%]
tests/test_user.py ..                                             [100%]

======================= 32 passed in 6.32 seconds =======================
```

[1]: https://pytest.org
[2]: https://virtualenvwrapper.readthedocs.io/en/latest/
