# PUMAPY

## PPMS Utility Management API - Python Interface

[Stratocore][3]'s *PPMS* booking system offers an API for fetching information from
the booking system as well as changing its state and properties.

This is a Python 3 package for talking to the so-called *PUMAPI*.

## Usage Instructions

TODO! Until then you may have a look at the testing instructions.

## Testing

Automated testing is described in the [`TESTING` document on github][2].

## Note

The PPMS API is not super clean and sometimes quite inconsistent. During
development of the package, we came across several issues (this list is
certainly incomplete):

* HTTP status return code is always `200`, even on failed authentication.
* Results of queries are a mixture of CSV (with headers) and and text with
  newlines (with no headers and therefore without structural information on
  the data). JSON is implemented in some cases only.
* The CSV headers sometimes do contain spaces between the colons, sometimes
  they don't.
* Some fields are quoted in the CSV output, some are not. Difficult to separate
  the values since there are colons in the values too.
* Semantics of keys is not consistent. Sometimes `user` is the user id,
  sometimes it refers to the user's full name.
* Using an invalid permission level (e.g. `Z`) with the `setright` action is
  silently ignored by PUMAPI, the response is still `done` even though this
  doesn't make any sense.
* There is no (obvious) robust way to derive the user id from the user's full
  name that is returned e.g. by `getrunningsheet`, making it very hard to
  cross-reference it with data from `getuser`.
* The result of the `getrunningsheet` query in general is not suited very well
  for automated processing, it seems to be rather tailored for humans and
  subject to (mis-) interpretation.
* Unfortunately `Username` and `Systemname` are not the unique id, they are
  rather the full description. Therefore sometimes looping over all users and
  systems is necessary.
* Some results have a very strange format - for example, the starting time of
  the next booking is given as *minutes from now* instead of an absolute time.
* Official documentation is rather rudimentary, i.e. it contains almost no
  information on what is returned in case wrong / invalid parameters are
  supplied and similar situations.

## References

* [Imagopole PPMS Java client][1]

[1]: https://github.com/imagopole/ppms-http-client/blob/master/src/main/java/org/imagopole/ppms/api/PumapiRequest.java
[2]: https://github.com/imcf/pumapy/blob/master/TESTING.md
[3]: https://www.stratocore.com/
