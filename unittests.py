# pytest -v unittests.py
import pytest
from datetime import datetime
from unittest.mock import patch, Mock, MagicMock, call
from app import app, update_cache, rss_feed
import logging

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@pytest.fixture
# Create a test client for the Flask app
def client():
    with app.test_client() as client:
        yield client


@pytest.fixture
# Mock the get_latest_release function
def mock_get_latest_release():
    with patch('app.get_latest_release') as mock:
        # Example mock data
        mock.return_value = ('1.0.0', '2023-10-01T12:00:00Z')
        yield mock


@pytest.fixture
# Mock the release_cache
def mock_release_cache():
    with patch('app.release_cache', MagicMock()) as mock:
        yield mock


@pytest.fixture
# Mock the datetime module to control the current time
def mock_datetime_now():
    class MockDateTime(datetime):
        @classmethod
        def now(cls):
            return mock_now()

    mock_now = Mock(return_value=datetime(2023, 10, 1, 0, 0, 0))

    with patch('datetime.datetime', new=MockDateTime):
        yield mock_now


# Test the /rss route
def test_rss_feed(client, mock_get_latest_release, mock_release_cache):
    # Simulate a request to the /rss route
    response = client.get('/rss')

    # Assert that the response status code is 200 (OK)
    assert response.status_code == 200


def test_update_cache(mock_get_latest_release, mock_release_cache):
    # Call the update_cache function
    update_cache()

    # Log interactions with mocks
    logger.debug(
        f'Mock get_latest_release called with: '
        f'{mock_get_latest_release.call_args_list}'
    )
    logger.debug(
        f'Mock release_cache.set called with: '
        f'{mock_release_cache.set.call_args_list}'
    )

    # Assert that the get_latest_release was called with the expected arguments
    # for each product
    calls_get_latest_release = [
        call(product='mcr', repository='https://repos.mirantis.com',
             channel='stable', component='docker'),
        call(product='mke', repository='mirantis/ucp',
             registry='https://hub.docker.com'),
        call(product='msr', repository='msr/msr',
             registry='https://registry.mirantis.com', branch='3.1')
    ]
    mock_get_latest_release.assert_has_calls(
        calls_get_latest_release, any_order=True)

    # Assert that the cache was updated with the expected data using set method
    calls_set = [
        call('mcr_https://repos.mirantis.com_stable_docker',
             ('1.0.0', '2023-10-01T12:00:00Z')),
        # Adjusted to match the pattern and the expected return value from
        # get_latest_release
        call('mke_mirantis/ucp_https://hub.docker.com',
             ('1.0.0', '2023-10-01T12:00:00Z')),
        # Adjusted to match the pattern and the expected return value from
        # get_latest_release
        call('msr_msr/msr_https://registry.mirantis.com_3.1',
             ('1.0.0', '2023-10-01T12:00:00Z'))
    ]
    mock_release_cache.set.assert_has_calls(calls_set, any_order=True)


# Test the scheduled update of the cache and RSS feed
def test_scheduled_update(mock_release_cache, mock_datetime_now):
    # Set the initial datetime
    initial_datetime = datetime(2023, 10, 1, 0, 0, 0)
    mock_datetime_now.now.return_value = initial_datetime

    # Mock the get_latest_release function to return a new version
    with patch('app.get_latest_release') as mock_get_latest_release:
        # Example mock data
        mock_get_latest_release.return_value = (
            '1.1.0', '2023-10-02T12:00:00Z')

        # Initial update
        update_cache()

        # Before calling rss_feed, ensure that the release_info in the cache
        # has a real datetime object for pubdate
        with patch.object(mock_release_cache, 'get',
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
    mock_release_cache.set.assert_has_calls(expected_calls, any_order=True)


if __name__ == '__main__':
    pytest.main()
