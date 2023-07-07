# PyPPMS Changelog

<!-- markdownlint-disable MD024 (no-duplicate-header) -->

NOTE: potentially breaking changes are flagged with a 🧨 symbol.

## 3.3.0

### Added

- `pyppms.ppms.get_running_sheet()` now has an optional parameter `localisation`
  (defaulting to an empty `str`) that will be passed to the call to
  `pyppms.ppms.get_systems_matching()`, allowing to restrict the runningsheet to
  systems of a given "room".

## 3.2.1

### Fixed

- 🕛🌃 end time: `pyppms.booking.PpmsBooking.endtime_fromstr()` contained a bug
  where the end time of a booking finishing at midnight got wrongly assigned to
  the *start* of the given day (instead of the end). This is now fixed by
  setting the end time to the start of the following day.

## 3.2.0

### Added

- `pyppms.ppms.PpmsConnection.last_served_from_cache` has been added to indicate
  if the last request was served from the cache or on-line.

### Changed

- Several log messages have been demoted to lower levels for further reducing
  logging clutter.

## 3.1.0

### Added

- `pyppms.common.fmt_time()` to string-format a datetime object that might also
  be None (in which case a fixed string is returned).
- `pyppms.booking.PpmsBooking.desc` has been added as a property to retrieve a
  shorter description of the object than calling `str()` on it.
- `pyppms.exceptions.NoDataError` has been added to indicate a PUMAPI response
  did *not* contain any useful data.
- `pyppms.common.parse_multiline_response()` will now raise the newly added
  `NoDataError` in case the requested *runningsheet* for a day doesn't contain
  any bookings to allow for properly dealing with "empty" days.

### Changed

- Several log messages have been demoted from `debug` to `trace` level and might
  have been shortened / combined to reduce logging clutter.

## 3.0.0

### Changed

- 🧨 Minimum required Python version is now `3.9`.
- Dependencies have been updated to their latest (compatible) versions.
- Logging is now done through [Loguru](https://pypi.org/project/loguru/).

## 2.3.0

### Added

- `pyppms.ppms.PpmsConnection()` now takes an optional parameter
  `cache_users_only` that will prevent any request but `getuser` from being
  stored in the local cache. This is useful in scenarios where frequent requests
  to PPMS are being done to fetch booking states and such that would be slowed
  down enormously if no user caching was present. Obviously the cached users
  need to be refreshed explicitly on a regular basis then. Defaults to `False`
  which will result in the same behavior as before.
  Please note that several things are implicitly being cached (in memory) during
  the lifetime of the `PpmsConnection` object (e.g. the PPMS systems) unless
  their corresponding method is being called with `force_refresh=True`.
- `pyppms.ppms.PpmsConnection.update_users()` and
  `pyppms.ppms.PpmsConnection.get_users()` now both have an optional parameter
  `active_only` (defaulting to `True`) that can be used to also request users
  that are marked as *inactive* in PPMS.

### Changed

- `pyppms.ppms.PpmsConnection.get_user()` is only logging a `DEBUG` level
  message (before: `ERROR`) in case the requested user can't be found since it
  also raises a `KeyError`. This is done to prevent cluttering up the logs of
  calling code that might use this method to figure out if an account exists in
  PPMS and properly deals with the exception raised.

## 2.2.0

### Added

- `pyppms.ppms.PpmsConnection.flush_cache()` to flush the on-disk cache with an
  optional argument `keep_users` (defaulting to `False`) that allows for
  flushing the entire cache **except** for the user **details**. This provides
  the opportunity of refreshing the cache on everything but *existing* users.
  Note that this will **not** affect **new** users, they will still be
  recognized and fetched from PUMAPI (and stored in the cache).

### Changed

- `pyppms.ppms.PpmsConnection.get_systems_matching()` now raises a `TypeError`
  in case the parameter `name_contains` is accidentially as `str` instead of a
  list.
- `pyppms.ppms.PpmsConnection.get_running_sheet()` now has an optional parameter
  `ignore_uncached_users` (defaulting to `False`) that allows to process the
  running sheet even if it contains users that are not in the `fullname_mapping`
  attribute.
- If the `cache_path` attribute is set for an `pyppms.ppms.PpmsConnection`
  instance but creating the actual subdir for an intercepted response fails
  (e.g. due to permission problems) the response-cache will not be updated.
  Before, the exception raised by the underlying code (e.g. a `PermissionError`)
  was passed on.
- Methods of `pyppms.ppms.PpmsConnection` are now sorted in alphabetical order,
  making it easier to locate them e.g. in the API documentation.

### Removed

- The following previously deprecated (or not even implemented) methods of
  `pyppms.ppms.PpmsConnection` have been removed in favor of
  `pyppms.ppms.PpmsConnection.get_systems_matching()`:
  - `_get_system_with_name()`
  - `_get_machine_catalogue_from_system()`
  - `get_bookable_ids()`
- Removed the stub `pyppms.ppms.PpmsConnection.get_system()` that was only
  raising a `NotImplementedError`.

## 2.1.0

### Changed

- [API] `pyppms.ppms.PpmsConnection.get_user()` and
  `pyppms.ppms.PpmsConnection.get_user_dict()` now both accept an optional
  parameter `skip_cache` that is passed on to the
  `pyppms.ppms.PpmsConnection.request()` call
- [FIX] `pyppms.ppms.PpmsConnection.update_users()` now explicitly asks for the
  cache to be skipped

## 2.0.0

### Changed

- [API] 🧨 the signature for `pyppms.user.PpmsUser` has been changed and now
  expects a single argument (the PUMAPI response text)
- [API] 🧨 the constructor signature for `pyppms.system.PpmsSystem()` has been
  changed and now expects a single argument (a dict as generated by
  `pyppms.common.parse_multiline_response()`)
- [API] 🧨 the constructor signature for `pyppms.booking.PpmsBooking()` has been
  changed and now expects the PUMAPI response text, the booking type (if the
  booking is currently running or upcoming) and the system ID
- [API] 🧨 the following methods have been removed as their behavior is now
  achieved by the corresponding default constructor of the respective class:
  - `pyppms.user.PpmsUser.from_response()`
  - `pyppms.system.PpmsSystem.from_parsed_response()`
  - `pyppms.booking.PpmsBooking.from_booking_request()`
