"""Tests for the PpmsUser class."""

from pumapy.user import PpmsUser

__author__ = "Niko Ehrenfeuchter"
__copyright__ = __author__
__license__ = "gpl3"


USERNAME = 'pumapy'
LNAME = 'Python'
FNAME = 'PumAPI'
EMAIL = 'does-not-reply@facility.xy'
UNITLOGIN = 'Python Core Facility'
FULLNAME = "%s %s" % (LNAME, FNAME)
EXPECTED = ('username: %s, email: %s, fullname: %s, ppms_group: %s, active: %s'
            % (USERNAME, EMAIL, FULLNAME, UNITLOGIN, 'True'))
API_RESPONSE = (u'login,lname,fname,email,phone,bcode,affiliation,unitlogin,'
                'mustchpwd,mustchbcode,active\r\n'
                '"%s","%s","%s","%s","","","","%s",false,false,true\r\n'
                % (USERNAME, LNAME, FNAME, EMAIL, UNITLOGIN))

def create_user():
    """Helper function to create a PpmsUser object with default values.

    Returns
    -------
    PpmsUser
    """
    return PpmsUser(
        username=USERNAME,
        email=EMAIL,
        fullname=FULLNAME,
        ppms_group=UNITLOGIN,
    )

def test_ppmsuser():
    """Test the PpmsUser constructor."""
    user = create_user()

    assert user.__str__() == USERNAME

def test_details():
    """Test the details() method."""
    user = create_user()

    assert user.details() == EXPECTED

def test_from_response():
    """Test the from_response() method."""
    print API_RESPONSE
    user = PpmsUser.from_response(API_RESPONSE)

    assert user.details() == EXPECTED
