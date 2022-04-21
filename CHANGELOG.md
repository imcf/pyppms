# PyPPMS Changelog

## 2.0.0

- [CHANGE] the constructor signature for `PpmsUser()` has been changed and now expects
  a single argument (the PUMAPI response text)
- [CHANGE] `PpmsUser.from_response()` has been removed as its behavior is now achieved
  by the default constructor
