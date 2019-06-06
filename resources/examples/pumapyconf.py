"""Configuration settings to be imported by pumapy."""

# the URL of the PUMAPI to talk to:
PUMAPI_URL = 'https://ppms.eu/pythonfacility/pumapi/'

# API key with appropriate permissions to run the desired commands in PPMS:
PPMS_API_KEY = 'abcdefghijklmnopqrstuvwxyzABCDEF'

# requests timeout in seconds (default=10)
TIMEOUT = 10

# path where to cache responses (either relative to the repository root or an
# absolute path), can be empty which will disable the cache
CACHE_PATH = 'tests/response-cache'

# TESTING ONLY: path to mocked responses (either relative to the repository root or an
# absolute path)
MOCKS_PATH = 'tests/mocked_responses'
