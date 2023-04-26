# PyPPMS Development ToDos

- add an option to the `flush_cache()` method to keepthe user details (as this
  is clearly the most expensive operation when no local cache is present)
- all methods returning a list of user objects (get_group_users, get_admins, ...) should
  be refactored to return a dict with those objects instead, having the username
  ('login') as the key.
- run tests in a true *offline* environment and validate they're working
- find a better solution than hard-coding a system ID in `test_ppms.__SYS_ID__`
