"""
This module contains unit tests for verifying the functionality of the app.
"""
# pytest -v unittests.py
from datetime import datetime
from unittest.mock import patch, Mock, MagicMock, call, ANY
import logging
import os
import pytest

# Set env variables for testing
os.environ['RUN_INITIALIZE'] = 'false'

# pylint: disable=wrong-import-position
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
def mock_get_latest_release_fixture(request):
    """
    Mock the get_latest_release function, simulating its behavior for testing.
    
    Yields:
        MagicMock: A mock object simulating the get_latest_release function.
    """
    mock = MagicMock()
    # Set the return_value or side_effect here based on request.param
    if hasattr(request, "param"):
        # If the test is parameterized, use the parameter for return_value
        mock.return_value = request.param[1]
    else:
        # Otherwise, use a default return value
        mock.return_value = ('1.0.0', '2023-10-01T12:00:00Z')

    with patch('app.get_latest_release', new=mock) as mock_func:
        yield mock_func


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
    Mock the datetime module's now method, controlling the returned current
    time.
    
    Yields:
        Mock: A mock object simulating the now method of the datetime module.
    """
    class MockDateTime(datetime):
        """
        A subclass of datetime, used to override the now() method for testing
        purposes.
        
        This class is intended to be used within testing environments where
        control over the current date and time returned by datetime.now() is
        required. It allows tests to simulate different points in time and
        observe how the code under test behaves.
        
        Methods:
        --------
        now(cls) -> datetime:
            Overrides the datetime.now() method to return a mock datetime
            object. The actual datetime returned is controlled by the mock_now
            function.
            
        Example:
        --------
        >>> with patch('datetime.datetime', new=MockDateTime):
        ...     assert datetime.now() == mock_now()  # mock_now() returns the
                mock datetime object.
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
        mock_get_latest_release (MagicMock): Mock of the get_latest_release
                                             function.
        mock_release_cache (MagicMock): Mock of the release_cache object.
    """
    response = test_client.get('/rss')

    # Assert that the response status code is 200 (OK)
    assert response.status_code == 200


def test_update_cache(mock_get_release, mock_cache):
    """
    Test the update_cache function of the app.
    
    Args:
        mock_get_latest_release (MagicMock): Mock of the get_latest_release
                                             function.
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
            'product': 'mcp',
            'repository': 'https://mirror.mirantis.com',
            'channel': 'update',
            'fetch_function': ANY 
        }),
        call({
            'product': 'mke-3.7',
            'repository': 'mirantis/ucp',
            'registry': 'https://hub.docker.com',
            'branch': '3.7',
            'fetch_function': ANY
        }),
        call({
            'product': 'mke-3.6',
            'repository': 'mirantis/ucp',
            'registry': 'https://hub.docker.com',
            'branch': '3.6',
            'fetch_function': ANY
        }),
        call({
            'product': 'msr-3.1',
            'repository': 'msr/msr',
            'registry': 'https://registry.mirantis.com',
            'branch': '3.1',
            'fetch_function': ANY
        }),
        call({
            'product': 'msr-2.9',
            'repository': 'mirantis/dtr',
            'registry': 'https://registry.hub.docker.com',
            'branch': '2.9',
            'fetch_function': ANY
        }),
        call({
            'product': 'mcc',
            'url': 'https://binary.mirantis.com',
            'prefix': 'releases/kaas/',
            'fetch_function': ANY
        }),
        call({
            'product': 'mosk',
            'url': 'https://binary.mirantis.com',
            'prefix': 'releases/cluster/',
            'fetch_function': ANY
        }),
        call({
            'product': 'k0s',
            'url': 'https://github.com/k0sproject/k0s/releases/latest',
            'fetch_function': ANY
        }),
        call({
            'product': 'lens',
            'url': 'https://api.k8slens.dev/binaries/latest.json',
            'fetch_function': ANY
        }),
    ]
    mock_get_release.assert_has_calls(
        calls_get_latest_release, any_order=True)

    # Assert that the cache was updated with the expected data using set method
    calls_set = [
        call('mcr_https://repos.mirantis.com_stable_docker',
             ('1.0.0', '2023-10-01T12:00:00Z')),
        call('mcp_https://mirror.mirantis.com_update',
             ('1.0.0', '2023-10-01T12:00:00Z')),
        call('mke-3.7_mirantis/ucp_https://hub.docker.com_3.7',
             ('1.0.0', '2023-10-01T12:00:00Z')),
        call('mke-3.6_mirantis/ucp_https://hub.docker.com_3.6',
             ('1.0.0', '2023-10-01T12:00:00Z')),
        call('msr-3.1_msr/msr_https://registry.mirantis.com_3.1',
             ('1.0.0', '2023-10-01T12:00:00Z')),
        call('msr-2.9_mirantis/dtr_https://registry.hub.docker.com_2.9',
             ('1.0.0', '2023-10-01T12:00:00Z')),
        call('mcc_https://binary.mirantis.com_releases/kaas/',
             ('1.0.0', '2023-10-01T12:00:00Z')),
        call('mosk_https://binary.mirantis.com_releases/cluster/',
             ('1.0.0', '2023-10-01T12:00:00Z')),
        call('k0s_https://github.com/k0sproject/k0s/releases/latest',
             ('1.0.0', '2023-10-01T12:00:00Z')),
        call('lens_https://api.k8slens.dev/binaries/latest.json',
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
        call('mcp_https://mirror.mirantis.com_update',
             ('1.1.0', '2023-10-02T12:00:00Z')),
        call('mke-3.7_mirantis/ucp_https://hub.docker.com_3.7',
             ('1.1.0', '2023-10-02T12:00:00Z')),
        call('mke-3.6_mirantis/ucp_https://hub.docker.com_3.6',
             ('1.1.0', '2023-10-02T12:00:00Z')),
        call('msr-3.1_msr/msr_https://registry.mirantis.com_3.1',
             ('1.1.0', '2023-10-02T12:00:00Z')),
        call('msr-2.9_mirantis/dtr_https://registry.hub.docker.com_2.9',
             ('1.1.0', '2023-10-02T12:00:00Z')),
        call('mcc_https://binary.mirantis.com_releases/kaas/',
             ('1.1.0', '2023-10-02T12:00:00Z')),
        call('mosk_https://binary.mirantis.com_releases/cluster/',
             ('1.1.0', '2023-10-02T12:00:00Z')),
        call('k0s_https://github.com/k0sproject/k0s/releases/latest',
             ('1.1.0', '2023-10-02T12:00:00Z')),
        call('lens_https://api.k8slens.dev/binaries/latest.json',
             ('1.1.0', '2023-10-02T12:00:00Z'))
    ]

    # Assert that the cache was updated with the new version for each product
    mock_cache.set.assert_has_calls(expected_calls, any_order=True)

# Define a parameterized fixture that will generate two sets of test data
@pytest.mark.parametrize('mock_get_release', [
    ('mosk', ('23.2.3', '2023-10-05T12:00:00Z')),  # for old format
    ('mosk', ('23.3', '2023-10-05T12:00:00Z')),     # for new format
], indirect=['mock_get_release'])
def test_mosk_version_extraction(mock_get_release, mock_cache):
    """
    Test the MOSK version extraction from the release content for both old and
    new version formats.

    Args:
        mock_get_elease (MagicMock): Mock of the get_latest_release function.
        mock_cache (MagicMock): Mock of the release_cache object.
    """
    logger.debug("mock_get_release called with: %s",
                 mock_get_release.call_args_list)

    # Mock the request to get the release content
    release_content = "some content that would be returned by requests.get"
    expected_version_info = mock_get_release.return_value
    logger.debug("Expected version info: %s", expected_version_info)

    with patch('requests.get') as mock_request:
        mock_response = Mock()
        mock_response.text = release_content
        mock_request.return_value = mock_response

        # Update cache
        update_cache()

        # Log the call arguments for debugging
        logger.debug("Mock get_latest_release called with: %s",
                     mock_get_release.call_args_list)
        logger.debug("Mock cache set called with: %s",
                     mock_cache.set.call_args_list)

        # Use assert_any_call to ensure the expected call was made at some
        # point
        mock_get_release.assert_any_call({
            'product': 'mcr',
            'repository': 'https://repos.mirantis.com',
            'channel': 'stable',
            'component': 'docker',
            'fetch_function': ANY
        })

        # If you want to ensure that the cache was updated with the expected
        # version, iterate over call_args_list
        found_version_call = False
        for call_args in mock_cache.set.call_args_list:
            name, version_tuple = call_args[0]
            if name == 'mosk_https://binary.mirantis.com_releases/cluster/':
                found_version_call = version_tuple == expected_version_info
                break

        assert found_version_call, (
            "The cache was not updated with the expected version "
            "for MOSK."
        )

@pytest.mark.parametrize('mock_get_release', [
    ('mcr', ('23.0.9', '2023-10-05T12:00:00Z')),    # Standard format
    ('mcr', ('23.0.9-1', '2023-10-06T12:00:00Z')),  # Incremented format
], indirect=['mock_get_release'])
def test_mcr_version_format_handling(mock_get_release, mock_cache):
    """
    Test the MCR version extraction and handling for both standard and
    incremented version formats.

    Args:
        mock_get_release (MagicMock): Mock of the get_latest_release function.
        mock_cache (MagicMock): Mock of the release_cache object.
    """
    logger.debug("mock_get_release called with: %s",
                 mock_get_release.call_args_list)

    # Mock the request to get the release content
    release_content = "some content that would be returned by requests.get"
    expected_version_info = mock_get_release.return_value
    logger.debug("Expected version info: %s", expected_version_info)

    with patch('requests.get') as mock_request:
        mock_response = Mock()
        mock_response.text = release_content
        mock_request.return_value = mock_response

        # Update cache
        update_cache()

        # Log the call arguments for debugging
        logger.debug("Mock get_latest_release called with: %s",
                     mock_get_release.call_args_list)
        logger.debug("Mock cache set called with: %s",
                     mock_cache.set.call_args_list)

        # Use assert_any_call to ensure the expected call was made at some
        # point
        mock_get_release.assert_any_call({
            'product': 'mosk',
            'url': 'https://binary.mirantis.com',
            'prefix': 'releases/cluster/',
            'fetch_function': ANY  # The actual fetch function reference
        })

        # If you want to ensure that the cache was updated with the expected
        # version, iterate over call_args_list
        found_version_call = False
        for call_args in mock_cache.set.call_args_list:
            name, version_tuple = call_args[0]
            if name == 'mcr_https://repos.mirantis.com_stable_docker':
                found_version_call = version_tuple == expected_version_info
                break

        assert found_version_call, (
            "The cache was not updated with the expected version "
            "for MCR."
        )


if __name__ == '__main__':
    pytest.main()
