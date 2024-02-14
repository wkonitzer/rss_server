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
from prometheus_client import Counter, Gauge, Histogram
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
metrics.info('app_info', 'Application info', version='1.0.9')

# Cache metrics
cache_hits = Counter('cache_hits', 'Number of cache hits')
cache_misses = Counter('cache_misses', 'Number of cache misses')
cache_size = Gauge('cache_size', 'Number of items in the cache')

# Update scheduler metrics
update_duration = Histogram('update_duration_seconds',
                            'Time spent updating cache')
update_failures = Counter('update_failures', 'Number of update failures')

# Feed generation metrics
feed_requests = Counter('feed_requests', 'Number of RSS feed requests')
feed_generation_duration = Histogram('feed_generation_duration_seconds',
                                     'Time spent generating RSS feed')


class SimpleCache:
    """
    A simple caching mechanism to store and retrieve data with a timeout
    mechanism. The timeout is the maximum age of the cached data before it is
    considered stale.
    """

    def __init__(self, timeout=86400):  # Default timeout is 24 hours
        self.cache = {}
        self.timeout = timeout
        cache_size.set(0)  # Initialize cache size

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
                cache_hits.inc()  # Increment cache hit counter
                return value
        cache_misses.inc()  # Increment cache miss counter
        return None

    def set(self, key, value):
        """
        Stores the key-value pair in the cache with the current timestamp.
        
        Parameters:
        key (str): The key for which the value needs to be stored.
        value (Any): The value that needs to be stored for the given key.
        """
        self.cache[key] = (time.time(), value)
        cache_size.set(len(self.cache))  # Update cache size gauge

    def get_link(self, product, version):
        """
        Retrieves the cached link for a given product and its version.

        This method constructs a unique key based on the product's name 
        and its version to fetch the link from the cache.

        Parameters:
            product (dict): A dictionary containing product details.
                            The 'product' key holds the name of the product.
            version (str): The version of the product for which the link is to
                           be retrieved.

        Returns:
            str or None: The cached link if it exists, otherwise None.
        """
        key = f"link_{product['product']}_{version}"
        return self.get(key)

    def set_link(self, product, version, link):
        """
        Stores the provided link in the cache for a given product and its
        version.

        This method constructs a unique key based on the product's name
        and its version to store the link in the cache.

        Parameters:
            product (dict): A dictionary containing product details.
                            The 'product' key holds the name of the product.
            version (str): The version of the product for which the link is to
                           be stored.
            link (str): The link to be stored in the cache.
        """
        key = f"link_{product['product']}_{version}"
        self.set(key, link)


release_cache = SimpleCache(timeout=config.CACHE_TIMEOUT)

products = config.PRODUCTS


def update_cache():
    """
    Updates the cache with the latest release info and associated links for
    each product.
    
    This function fetches the latest release information for each product,
    caches this data, and also caches the link to the product's release notes
    or webpage. This is intended to optimize retrieval times and minimize
    redundant operations when serving the RSS feed. This function is meant to
    be run as a scheduled job to keep the cache up-to-date.
    
    Note:
    This function is parallelized for efficiency using a thread pool.
    """
    logging.info('Starting cache update...')

    def fetch_and_cache(product):
        """
        Fetches the latest release information for a given product, updates
        the cache with the release information, and caches the link to the 
        product's release notes or webpage.
        
        Parameters:
        product (dict): A dictionary containing the details of the product for
                        which the latest release information needs to be
                        fetched.
        """
        try:
            # Determine cache key for release info
            available_keys = [key for key in ['product', 'repository',
                                              'channel', 'component',
                                              'registry', 'branch', 'url',
                                              'prefix'] 
                              if key in product]
            key_parts = [product[key] for key in available_keys]
            key = '_'.join(key_parts)

            # Fetch the latest release info and update the cache
            release_info = get_latest_release(product)
            release_cache.set(key, release_info)
            logging.info('Cache updated for product: %s', product["product"])

            # If the release info is valid, cache the product link
            if release_info and len(release_info) > 1:
                version, _ = release_info
                link = generate_product_link(product, version)
                release_cache.set_link(product, version, link)

        except ValueError as value_error:
            update_failures.inc()  # Increment on failure
            logging.error(
                "Failed to update cache for product %s due to value error: %s",
                product.get("product", "unknown"), str(value_error)
            )

    with update_duration.time():  # Start measuring time
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

        link = release_cache.get_link(product, version)
        if not link:
            link = generate_product_link(product, version)
            release_cache.set_link(product, version, link)

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

    feed_requests.inc()  # Increment feed request counter
    with feed_generation_duration.time():  # Measure feed generation time
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


def initialize_app():
    """
    Start the Flask application along with a background scheduler.

    This function initializes the application cache, sets up a background
    scheduler to update the cache at regular intervals, and starts the Flask
    application. The interval at which the cache is updated is determined by
    the `SCHEDULER_INTERVAL` configuration.

    The Flask application is started with the host and port specified in the
    configuration. If the `FLASK_DEBUG` environment variable is set to 'true',
    the application will run in debug mode.

    Side Effects:
        - Calls `update_cache()` to initialize the cache with the latest data.
        - Starts a background scheduler to call `update_cache()` at regular
          intervals.
        - Logs the initiation of cache updating and the Flask application
          start.

    Environment Variables:
        FLASK_DEBUG: If set to 'true', runs the application in debug mode.
                     Default is 'false'.

    Configuration Variables:
        - SCHEDULER_INTERVAL: The interval in hours for the scheduler to update
                              the cache.
    """
    update_cache()
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_cache, 'interval',
                      hours=config.SCHEDULER_INTERVAL)
    logging.info(
        'Scheduler started with job to update cache every %s hours.',
        config.SCHEDULER_INTERVAL
    )
    scheduler.start()


def run_app():
    """
    Launch the Flask application with the configuration specified in the
    `config` module.

    This function starts the Flask web server with the host and port as defined
    in the application's configuration. It checks the `FLASK_DEBUG` environment
    variable to determine if the application should be started in debug mode.

    Debug mode allows for automatic reloading of the application upon detecting
    changes in the code and provides a debugger if an exception is raised.
    However, it should not be used in a production environment due to the
    performance overhead and potential security risks.

    The function logs the start and stop of the application to provide feedback
    in the console regarding the state of the application server.

    Environment Variables:
        FLASK_DEBUG: If set to 'true', runs the application in debug mode which
                     enables a debugger and auto-reloading. Default is 'false'.

    Side Effects:
        - Starts the Flask application server.
        - Logs the start and stop of the application server to the console.

    Returns:
        None
    """
    logging.info('Starting application...')
    is_debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host=config.HOST, port=config.PORT, debug=is_debug_mode)
    logging.info('Application stopped.')


# Set the RUN_INITIALIZE environment variable to "false" when running tests
if os.environ.get('RUN_INITIALIZE', 'true').lower() == 'true':
    initialize_app()


if __name__ == '__main__':
    initialize_app()
    run_app()
