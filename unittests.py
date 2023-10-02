"""
This module contains unit tests for verifying the functionality of the app.
"""
# pytest -v unittests.py
from datetime import datetime
from unittest.mock import patch, Mock, MagicMock, call, ANY
import logging

import pytest

from app import app, update_cache, rss_feed

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@pytest.fixture(name='test_client')
def client_fixture():
    """
    Create a test client for the Flask app.
    
    Yields:
        FlaskClient: An instance of the app's test client.
    """
    with app.test_client() as client:
        yield client


@pytest.fixture(name='mock_get_release')
def mock_get_latest_release_fixture():
    """
    Mock the get_latest_release function, simulating its behavior for testing.
    
    Yields:
        MagicMock: A mock object simulating the get_latest_release function.
    """
    with patch('app.get_latest_release') as mock:
        # Example mock data
        mock.return_value = ('1.0.0', '2023-10-01T12:00:00Z')
        yield mock


@pytest.fixture(name='mock_cache')
def mock_release_cache_fixture():
    """
    Mock the release_cache object, simulating its behavior for testing.
    
    Yields:
        MagicMock: A mock object simulating the release_cache object.
    """
    with patch('app.release_cache', MagicMock()) as mock:
        yield mock


@pytest.fixture(name='mock_dt_now')
def mock_datetime_now_fixture():
    """
    Mock the datetime module's now method, controlling the returned current time.
    
    Yields:
        Mock: A mock object simulating the now method of the datetime module.
    """
    class MockDateTime(datetime):
        """
        A subclass of datetime, used to override the now() method for testing purposes.
        
        This class is intended to be used within testing environments where control over
        the current date and time returned by datetime.now() is required. It allows tests
        to simulate different points in time and observe how the code under test behaves.
        
        Methods:
        --------
        now(cls) -> datetime:
            Overrides the datetime.now() method to return a mock datetime object.
            The actual datetime returned is controlled by the mock_now function.
            
        Example:
        --------
        >>> with patch('datetime.datetime', new=MockDateTime):
        ...     assert datetime.now() == mock_now()  # mock_now() returns the mock datetime object.
        """
        @classmethod
        def now(cls, tz=None):
            """
            Override the now method to return a mock datetime.
            
            Returns:
            --------
            datetime:
                A datetime object representing the current date and time,
                as determined by the mock_now function.
            """
            return mock_now()

    mock_now = Mock(return_value=datetime(2023, 10, 1, 0, 0, 0))

    with patch('datetime.datetime', new=MockDateTime):
        yield mock_now


def test_rss_feed(test_client):
    """
    Test the /rss route of the app.
    
    Args:
        client (FlaskClient): An instance of the app's test client.
        mock_get_latest_release (MagicMock): Mock of the get_latest_release function.
        mock_release_cache (MagicMock): Mock of the release_cache object.
    """
    response = test_client.get('/rss')

    # Assert that the response status code is 200 (OK)
    assert response.status_code == 200


def test_update_cache(mock_get_release, mock_cache):
    """
    Test the update_cache function of the app.
    
    Args:
        mock_get_latest_release (MagicMock): Mock of the get_latest_release function.
        mock_release_cache (MagicMock): Mock of the release_cache object.
    """
    update_cache()

    # Log interactions with mocks
    logger.debug('Mock get_latest_release called with: %s',
                 mock_get_release.call_args_list)

    logger.debug('Mock release_cache.set called with: %s',
                 mock_cache.set.call_args_list)

    # Assert that the get_latest_release was called with the expected arguments
    # for each product
    calls_get_latest_release = [
        call({
            'product': 'mcr',
            'repository': 'https://repos.mirantis.com',
            'channel': 'stable',
            'component': 'docker',
            'fetch_function': ANY  # use ANY since the actual function 
                                   # reference may not be easily available
        }),
        call({
            'product': 'mke',
            'repository': 'mirantis/ucp',
            'registry': 'https://hub.docker.com',
            'fetch_function': ANY
        }),
        call({
            'product': 'msr',
            'repository': 'msr/msr',
            'registry': 'https://registry.mirantis.com',
            'branch': '3.1',
            'fetch_function': ANY
        }),
    ]
    mock_get_release.assert_has_calls(
        calls_get_latest_release, any_order=True)

    # Assert that the cache was updated with the expected data using set method
    calls_set = [
        call('mcr_https://repos.mirantis.com_stable_docker',
             ('1.0.0', '2023-10-01T12:00:00Z')),
        call('mke_mirantis/ucp_https://hub.docker.com',
             ('1.0.0', '2023-10-01T12:00:00Z')),
        call('msr_msr/msr_https://registry.mirantis.com_3.1',
             ('1.0.0', '2023-10-01T12:00:00Z'))
    ]
    mock_cache.set.assert_has_calls(calls_set, any_order=True)


def test_scheduled_update(mock_cache, mock_dt_now):
    """
    Test the scheduled update of the cache and RSS feed.
    
    Args:
        mock_release_cache (MagicMock): Mock of the release_cache object.
        mock_datetime_now (Mock): Mock of the datetime module's now method.
    """
    # Set the initial datetime
    initial_datetime = datetime(2023, 10, 1, 0, 0, 0)
    mock_dt_now.return_value = initial_datetime

    # Mock the get_latest_release function to return a new version
    with patch('app.get_latest_release') as mock_get_latest_release:
        # Example mock data
        mock_get_latest_release.return_value = (
            '1.1.0', '2023-10-02T12:00:00Z')

        # Initial update
        update_cache()

        # Before calling rss_feed, ensure that the release_info in the cache
        # has a real datetime object for pubdate
        with patch.object(mock_cache, 'get',
                          return_value=('1.1.0', initial_datetime)):
            rss_feed()  # Trigger RSS feed generation

    # Define the expected cache keys and associated values
    expected_calls = [
        call('mcr_https://repos.mirantis.com_stable_docker',
             ('1.1.0', '2023-10-02T12:00:00Z')),
        call('mke_mirantis/ucp_https://hub.docker.com',
             ('1.1.0', '2023-10-02T12:00:00Z')),
        call('msr_msr/msr_https://registry.mirantis.com_3.1',
             ('1.1.0', '2023-10-02T12:00:00Z'))
    ]

    # Assert that the cache was updated with the new version for each product
    mock_cache.set.assert_has_calls(expected_calls, any_order=True)


if __name__ == '__main__':
    pytest.main()
