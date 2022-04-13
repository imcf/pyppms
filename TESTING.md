# Testing PyPPMS

Automated testing has been a core design goal for `pyppms`, aiming for a
coverage of 100%. Testing of the project is performed through [pytest][t1].

## Concept of PyPPMS Unit Tests

As proper testing of an HTTP-based API will require interaction with a real instance of
that given API the *complete* suite of tests will only be able to run if you're having
access to PPMS somewhere. Obviously, this should not be done on a production instance
but a separate test setup (contact Stratocore to get one).

To speed up testing, make it more convenient and provide a certain level of robustness
against silent changes of the PPMS API, tests are split into more or less three
categories:

* ***local*** unit tests - they don't need a PPMS / PUMAPI instance
* tests using ***cached*** responses from a real PPMS / PUMAPI
* tests using ***mocked*** responses to simulate specific behavior of PPMS that cannot
  be triggered otherwise

### Development installation through poetry

The project is using [poetry][t2] for packaging and dependency management. To set up a
development environment and prepare for testing use the command below, it will set up a
fresh *virtual environment* with the correct dependencies and install the project in
***editable*** mode:

```bash
git clone https://github.com/imcf/pyppms
cd pyppms
poetry install
```

### Cached Testing

Almost all of the *request-response* tests, which is basically anything in the
[PpmsConnection](/src/pyppms/ppms.py) class, do **NOT** require a valid API-key or a
connection to a PUMAPI instance. Instead, they can be performed using the built-in
response-caching mechanism combined with the mocks and cached responses provided with
the repository.

#### Using the cache

Working with the provided cached responses is the default when running the tests. The
only exception are those tests that do not make sense in such a scenario (i.e. that do
test if interaction with an actual PUMAPI instance is effectively working). Those tests
have to be requested explicitly by adding the "`--online`" flag to the pytest-call.

#### Validating the cache

Validating or re-building the cache requires access to an actual PUMAPI, see the section
on *running online tests* below for details.

### Configuration and API Key

To run the tests, copy the example [`pyppmsconf.py`](/resources/examples/pyppmsconf.py)
file to the `/tests/` directory. For the online tests, please edit it according to your
instance and key - the offline tests will work without modifying the config.

```bash
cp -v resources/examples/pyppmsconf.py tests/
```

To generate an API key a so-called "Super-Admin" needs to log on to your PPMS instance,
navigate to `My PPMS` using the drop-down menu on the top-right, select `API` from the
top bar and finally hit the `Create PUMAPI key` button.

## Running Tests

Once everything is set up, you should be good to simply type `poetry run pytest` on the
command line, the output should look something like this:

```text
poetry run pytest
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

## Running Online Tests

To run those tests requiring access to a real PUMAPI instance in addition to the default
ones, simply add the `--online` flag to the `pytest` command above. Obviously you will
need to have valid settings for `PUMAPI_URL` and `PPMS_API_KEY` in the config file used
for testing.

Please note that this will still run the majority of tests using the cached / mocked
responses!

However, having a cache of the **expected** responses from PUMAPI for a given query (or
a series of queries) allows for checking if the behavior of the API has silently
changed by simply deleting the cache and re-building it afterwards. To do so, the
following steps are required:

* preparing your test instance of PPMS - unfortunately this is a manual operation, but
  it has to be done only once (unless Stratocore resets your test instance)
* removing the cache
* running the tests in online mode to re-populate the cache
* filtering / checking / validating the results

Those steps are described in details in the following sections.

### PPMS Preparations

As the tests assume certain users and systems to exist in the PUMAPI instance used for
testing, your test instance needs to be prepared accordingly. Currently there is not yet
a mechanism to automatically create those items unfortunately - sorry, might come at
some point...

For now, simply run the following command to see what needs to be configured in your
PPMS, then log into the web interface with your browser and manually create the required
items:

```bash
poetry run python tests/show_required_ppms_values.py
```

Remarks / additional details:

* All created users should be members of the previously created group.
* After creating the *admin* user, go to the **Admins** page in PPMS, hit the
  *Create a new administrator* button, then select the correct facility and pick
  the user account. In options, simply check the *System management* box, then
  click *Create administrator*.
* After creating all users, navigate to the **Rights** page, select the newly
  created system and pick the *regular* user, then hit the *Create* button to
  assign booking permissions to the user account. Then repeat this for the admin
  user and the *inactive* user (account needs to be set to *active* for adding
  the permissions).
* In addition to the above, four bookings for the *regular* user on the created
  system need to be made on 2028-12-24:
  * from 09:00 to 10:00
  * from 11:00 to 12:00
  * from 13:00 to 14:00
  * from 15:00 to 16:00

### Removing the Cache

As easy as running:

```bash
rm -r tests/cached_responses
```

### Re-populating and validating the Cache

NOTE: As a test-instance of PPMS usually is a clone of a real one it will contain many
more but the previously created objects. Therefore when re-populating the cache from a
real PPMS instance a few filtering steps have to be done to validate the new cache files
and ignore those "unpredictable" ("instance-specific") elements.

First run the most time-consuming tests that will fetch all users from your PPMS (this
can easily take several minutes, depending on your PPMS instance):

```bash
poetry run pytest --online tests/test_ppms.py::test_get_users
poetry run pytest --online tests/test_ppms.py::test_get_admins
```

As a result, the `tests/cached_responses/stage_0/getuser/` directory will be cluttered
up with plenty of files from users in your PPMS instance that the cache doesn't know
about (and also shouldn't). To clean this, simply remove all corresponding
response-cache files untracked by git:

```bash
git clean -f tests/cached_responses/stage_0/getuser/
```

Now the freshly re-created response files need to be checked if they contain all the
expected values while discarding / ignoring the additional ones introduced by your
specific PPMS instance. To simplify this task use this shortcut function (bash) to show
the `git diff` of a file while discarding all lines that were added to it (as they are
specific to your instance):

```bash
filternew() {
    git diff --no-color "$1" | grep -v '^+' | tail -n +5
}
```

First, this needs to be done for the files created by the two tests from above (active
users and admins). Run the command and compare the output that is expected to look as
shown here:

```bash
filternew "tests/cached_responses/stage_0/getusers/active--true.txt"
 pyppms
 pyppms-adm

filternew "tests/cached_responses/stage_0/getadmins/response.txt"
 pyppms-adm
```

If the output matches, discard the changes to those files:

```bash
git restore \
  "tests/cached_responses/stage_0/getusers/active--true.txt" \
  "tests/cached_responses/stage_0/getadmins/response.txt"
```

Now run all `--online` tests - with the just (re-)created cache files for the users and
admins, this should only take a few seconds:

```bash
poetry run pytest --online
```

Then, check the remaining re-created cache files for their content:

```bash
filternew "tests/cached_responses/stage_0/getusers/response.txt"
 pyppms
 pyppms-adm
 pyppms-deact

filternew "tests/cached_responses/stage_0/getgroups/response.txt"
 pyppms_group

filternew "tests/cached_responses/stage_0/getsysrights/id--*"
 A:pyppms
 A:pyppms-adm
 D:pyppms-deact
 S:pyppms-adm

filternew "tests/cached_responses/stage_1/getsysrights/id--*"
 D:pyppms
 A:pyppms-adm
 D:pyppms-deact
 S:pyppms-adm


filternew "tests/cached_responses/stage_2/getsysrights/id--*"
 D:pyppms
 A:pyppms-adm
 D:pyppms-deact
 S:pyppms-adm
```

Do the same for the systems and user experience responses, taking into account that the
system ID will differ in your case, those lines will then show as missing in the diff:

```bash
filternew "tests/cached_responses/stage_0/getsystems/response.txt"
 Core facility ref,System id,Type,Name,Localisation,Active,Schedules,Stats,Bookable,Autonomy Required,Autonomy Required After Hours
 2,69,"Virtualized Workstation","Python Development System","VDI (Development)",True,True,True,True,True,False

filternew "tests/cached_responses/stage_0/getuserexp/response.txt"
 login,id,booked_hours,used_hours,last_res,last_train
 "pyppms",69,0,0,n/a,n/a
 "pyppms-adm",69,0,0,n/a,n/a
 "pyppms-deact",69,0,0,n/a,n/a
```

The last one to check is the response for the `nextbooking` query, which will differ in
the two additional lines for the remaining time and the session, so the result should
look something like this:

```bash
filternew "tests/cached_responses/stage_0/nextbooking/id--*"
 pyppms
-303520
-31432
```

If all output matches, discard the changes to those files:

```bash
git restore \
  "tests/cached_responses/stage_0/getusers/response.txt" \
  "tests/cached_responses/stage_0/getgroups/response.txt" \
  "tests/cached_responses/stage_0/getsysrights/id--*" \
  "tests/cached_responses/stage_1/getsysrights/id--*" \
  "tests/cached_responses/stage_2/getsysrights/id--*" \
  "tests/cached_responses/stage_0/getsystems/response.txt" \
  "tests/cached_responses/stage_0/getuserexp/response.txt" \
  "tests/cached_responses/stage_0/nextbooking/id--*"
```

[t1]: https://pytest.org
[t2]: https://python-poetry.org
