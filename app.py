"""
This module serves an RSS feed via a Flask web application, displaying the
latest releases of several products. It uses a caching mechanism to store the
releases and updates them at regular intervals using a background scheduler.

Dependencies:
    - Flask
    - feedgenerator
    - apscheduler
    - etc.

To run:
    python app.py
"""

import os
import time
import logging
import concurrent.futures
from datetime import datetime as dt

from flask import Flask, Response
from prometheus_flask_exporter import PrometheusMetrics
from apscheduler.schedulers.background import BackgroundScheduler
import feedgenerator

from get_latest_release import get_latest_release
import config
from product_utils import generate_product_link

# Configure logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# Set up metrics
metrics = PrometheusMetrics(app)

# Expose some default metrics
metrics.info('app_info', 'Application info', version='1.0.4')


class SimpleCache:
    """
    A simple caching mechanism to store and retrieve data with a timeout
    mechanism. The timeout is the maximum age of the cached data before it is
    considered stale.
    """

    def __init__(self, timeout=86400):  # Default timeout is 24 hours
        self.cache = {}
        self.timeout = timeout

    def get(self, key):
        """
        Retrieves the value from the cache associated with the given key.
        
        Parameters:
        key (str): The key for which the value needs to be retrieved.
        
        Returns:
        value (Any): The value associated with the given key if the key exists
        in the cache and the value is not timed out, else None.
        """
        data = self.cache.get(key)
        if data:
            timestamp, value = data
            if time.time() - timestamp < self.timeout:
                return value
        return None

    def set(self, key, value):
        """
        Stores the key-value pair in the cache with the current timestamp.
        
        Parameters:
        key (str): The key for which the value needs to be stored.
        value (Any): The value that needs to be stored for the given key.
        """
        self.cache[key] = (time.time(), value)


release_cache = SimpleCache(timeout=config.CACHE_TIMEOUT)

products = config.PRODUCTS


def update_cache():
    """
    Updates the cache with the latest release info for each product.
    This function is intended to be run as a scheduled job.
    """
    logging.info('Starting cache update...')

    def fetch_and_cache(product):
        """
        Fetches the latest release information for a given product and updates
        the cache.
        
        This function constructs a key from the available fields in the product
        dictionary, fetches the latest release information for the constructed
        key, and updates the cache with the fetched information.
        
        Parameters:
        product (dict): A dictionary containing the details of the product for
                        which the latest release information needs to be
                        fetched and cached. The dictionary may contain fields
                        like 'product', 'repository', 'channel', 'component',
                        'registry', and 'branch'.
        
        Note:
        This function is intended to be used as a worker function with
        concurrent.futures.ThreadPoolExecutor for parallel execution.
        """
        # Determine the available keys in the product dictionary
        available_keys = [key for key in ['product', 'repository',
                                          'channel', 'component', 'registry',
                                          'branch', 'url',
                                          'prefix'] if key in product]

        # Construct the cache key based on the available keys
        key_parts = [product[key] for key in available_keys]
        key = '_'.join(key_parts)

        # Fetch the latest release info and update the cache
        release_info = get_latest_release(product)
        release_cache.set(key, release_info)
        logging.info('Cache updated for product: %s', product["product"])

    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(fetch_and_cache, products)

    logging.info('Cache update complete.')


@app.route('/rss')
def rss_feed():
    """
    Generates and serves an RSS feed containing the latest releases of the
    products.

    Returns:
        A Flask Response object containing the generated RSS feed in XML
        format.
    """

    logging.info('Generating RSS feed...')
    feed = feedgenerator.Rss201rev2Feed(
        title="Mirantis Software Releases",
        link="https://mirantis.com",
        description="Latest Mirantis software releases",
        language="en",
    )

    def process_product(product):
        """
        Processes the given product and updates the RSS feed with the latest
        release information.
        
        This function constructs a cache key based on the available keys in the
        given product and  attempts to retrieve the release_info from the
        cache. If the cache does not contain valid release_info, the function
        fetches the latest release information, updates the cache, and logs an
        error if the fetched release_info is invalid. After processing the
        release_info, it updates the RSS feed with a new item containing the
        latest release details, including the version, release date, link, and
        description.
        
        Parameters:
        product (dict): A dictionary containing the details of the product to
                        be processed, including keys like 'product',
                        'repository', 'channel', 'component', 'registry', and
                        'branch'.
        
        Returns:
        None: This function does not return a value; it updates the global RSS
        feed directly.
        
        Side Effects:
        - Updates the global RSS feed with a new item, if valid release_info is
          found or fetched.
        - Logs an error message if invalid release_info is encountered.
        - Updates the global release_cache with fetched release_info.
        
        Example:
        --------
        >>> product = {
        ...    'product': 'mcr',
        ...    'repository': 'https://repos.mirantis.com',
        ...    'channel': 'stable',
        ...    'component': 'docker',
        ... }
        >>> process_product(product)  # Updates the RSS feed with the latest
        release of the 'mcr' product.

        Note:
        This function is intended to be used as a worker function with
        concurrent.futures.ThreadPoolExecutor for parallel execution.
        """
        # Determine the available keys in the product dictionary
        available_keys = [key for key in ['product', 'repository',
                                          'channel', 'component', 'registry',
                                          'branch', 'url',
                                          'prefix'] if key in product]

        # Construct the cache key based on the available keys
        key_parts = [product[key] for key in available_keys]
        key = '_'.join(key_parts)

        # Check if release info is in the cache
        release_info = release_cache.get(key)

        if release_info is None or len(release_info) < 2:
            # If not in the cache, fetch the latest release info and update the
            # cache
            release_info = get_latest_release(product)
            if release_info is None or len(release_info) < 2:
                # Log an error message and continue to the next product if
                # fetched data is still invalid
                app.logger.error('Invalid release_info for key %s: %s',
                                 key, release_info)
                return

            # Update the cache with the valid fetched data
            release_cache.set(key, release_info)

        # Use the release_info for the product
        version, release_date = release_info

        # Check and convert release_date to datetime object if it's a string
        if isinstance(release_date, str):
            release_date = dt.fromisoformat(release_date.rstrip('Z'))

        link = generate_product_link(product, version)
        description = (
            f'<a href="{link}">Release notes for '
            f'{product["product"].upper()} {version}</a>'
        )

        feed.add_item(
            title=f"Mirantis {product['product'].upper()} {version}",
            link=link,
            description=description,
            pubdate=release_date or dt.now(),
        )

    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(process_product, products)

    # Before calling writeString, ensure all items have real datetime objects
    # for pubdate
    for item in feed.items:
        if not isinstance(item['pubdate'], dt):
            item['pubdate'] = dt.now()  # Or another suitable datetime value

    response = Response(feed.writeString('utf-8'),
                        content_type='application/rss+xml; charset=utf-8')
    logging.info('RSS feed generated successfully.')
    return response


@app.route('/health')
def health_check():
    """
    A simple health check endpoint returning 'OK' with a 200 status code.
    Can be used as a liveness and readiness probe in Kubernetes.
    """
    return 'OK', 200


# Initialize the cache and the scheduler
update_cache()
scheduler = BackgroundScheduler()
scheduler.add_job(update_cache, 'interval', hours=config.SCHEDULER_INTERVAL)
logging.info(
    'Scheduler started with job to update cache every %s hours.',
    config.SCHEDULER_INTERVAL
)
scheduler.start()

if __name__ == '__main__':
    logging.info('Starting application...')
    is_debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host=config.HOST, port=config.PORT, debug=is_debug_mode)
    logging.info('Application stopped.')
