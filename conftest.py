"""
This module contains fixtures for pytest that are globally available to all
test functions.

These fixtures are used to modify or replace functionality during tests to
ensure that the tests are not dependent on external factors such as actual
API calls or the state of a database/cache.

Fixtures:
- `no_update_cache`: Automatically patches the `update_cache` function from
  the `app` module to prevent it from running during tests.
- `mock_requests_get`: Patches the `requests.get` function to return a mock
  response, thus avoiding actual HTTP requests during tests.
"""
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(scope="session", autouse=True)
def no_update_cache():
    """
    A fixture that patches the 'update_cache' function from the 'app' module
    for all tests.
    
    This prevents the update_cache function from making unwanted changes to the
    cache state or performing any actions when the 'app' module is imported.
    
    The patch is started before any tests run and stopped after all tests are
    complete.
    """
    # Start the patch
    patcher = patch('app.update_cache')
    patcher.start()
    # This will run before any tests

    yield

    # This will run after all tests are done
    patcher.stop()


@pytest.fixture(autouse=True)
def mock_requests_get():
    """
    A fixture that patches 'requests.get' to return a mock response for all
    tests.
    
    This ensures that tests do not make actual HTTP requests and allows for
    the simulation of different responses from external services. The mock
    response text can be customized as needed for specific tests.
    """
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.text = "Your mock response here"
        mock_get.return_value = mock_response
        yield mock_get
