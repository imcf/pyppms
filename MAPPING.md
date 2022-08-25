# Mapping of PUMAPI to `pyppms` commands

Assuming you have instantiated a connection object like:

```Python
import pyppmsconf
from pyppms import ppms

conn = ppms.PpmsConnection(
        url=pyppmsconf.PUMAPI_URL,
        api_key=pyppmsconf.PPMS_API_KEY,
        timeout=pyppmsconf.TIMEOUT,
)
```

| PUMAPI                | `pyppms`                                 |
|-----------------------|------------------------------------------|
| addprojectentry       |                                          |
| addrebateonsession    |                                          |
| addsampleresult       |                                          |
| addvalidbcode         |                                          |
| auth                  | (done in `conn`'s constructor)           |
| createinc             |                                          |
| createorder           |                                          |
| createprojectmember   |                                          |
| createsys             |                                          |
| deleteprojectmember   |                                          |
| delvalidbcode         |                                          |
| getadmins             | `conn.get_admins()`                      |
| getaffiliationsummary |                                          |
| getbcodes             |                                          |
| getbooking            |                                          |
| getgroup              | `conn.get_group()`                       |
| getgroupprojects      |                                          |
| getgroups             | `conn.get_groups()`                      |
| getgroupusers         | `conn.get_group_users()`                 |
| getinc                |                                          |
| getint                |                                          |
| getinvoice            |                                          |
| getinvoicedetails     |                                          |
| getinvoicelist        |                                          |
| getinvtracklist       |                                          |
| getmanifest           |                                          |
| getmanifestlist       |                                          |
| getorderlines         |                                          |
| getorders             |                                          |
| getprepaidaccounts    |                                          |
| getpriceslist         |                                          |
| getprojectgroups      |                                          |
| getprojectmember      |                                          |
| getprojects           |                                          |
| getprojectusers       |                                          |
| getrunningsheet       | `conn.get_running_sheet()`               |
| getservices           |                                          |
| getsessionnote        |                                          |
| getsysrights          | `conn.get_users_with_access_to_system()` |
| getsystems            | `conn.get_systems()`                     |
| getuser               | `conn.get_user()`                        |
| getuserexp            | `conn.get_user_experience()`             |
| getuserprojects       |                                          |
| getuserrights         |                                          |
| getusers              | `conn.get_user_ids()`                    |
| getvalidbcodes        |                                          |
| listpubmed            |                                          |
| newgroup              |                                          |
| newproject            |                                          |
| newuser               | `conn.new_user()`                        |
| nextbooking           |                                          |
| rightcheck            |                                          |
| setinvtracksent       |                                          |
| setright              | `conn.set_system_booking_permissions()`  |
| setsessionnote        |                                          |
| updateorderphase      |                                          |
| updatesys             |                                          |
| updgroup              |                                          |
| updproject            |                                          |
| upduser               |                                          |
