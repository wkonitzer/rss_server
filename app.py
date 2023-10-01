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

from flask import Flask, Response
import feedgenerator
from apscheduler.schedulers.background import BackgroundScheduler
from get_latest_release import get_latest_release
from datetime import datetime as dt
import time
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)


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
        data = self.cache.get(key)
        if data:
            timestamp, value = data
            if time.time() - timestamp < self.timeout:
                return value
        return None

    def set(self, key, value):
        self.cache[key] = (time.time(), value)


release_cache = SimpleCache(timeout=86400)  # 24-hour timeout

products = [
    {'product': 'mcr', 'repository': 'https://repos.mirantis.com',
        'channel': 'stable', 'component': 'docker'},
    {'product': 'mke', 'repository': 'mirantis/ucp',
        'registry': 'https://hub.docker.com'},
    {'product': 'msr', 'repository': 'msr/msr',
        'registry': 'https://registry.mirantis.com', 'branch': '3.1'},
]


def update_cache():
    """
    Updates the cache with the latest release info for each product.
    This function is intended to be run as a scheduled job.
    """

    logging.info('Starting cache update...')
    for product in products:
        # Determine the available keys in the product dictionary
        available_keys = [key for key in ['product', 'repository',
                                          'channel', 'component', 'registry',
                                          'branch'] if key in product]

        # Construct the cache key based on the available keys
        key_parts = [product[key] for key in available_keys]
        key = '_'.join(key_parts)

        # Fetch the latest release info and update the cache
        release_info = get_latest_release(**product)
        release_cache.set(key, release_info)
        logging.info(f'Cache updated for product: {product["product"]}')
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
        link="http://localhost:5000/",
        description="Latest Mirantis software releases",
        language="en",
    )

    for product in products:
        # Determine the available keys in the product dictionary
        available_keys = [key for key in ['product', 'repository',
                                          'channel', 'component', 'registry',
                                          'branch'] if key in product]

        # Construct the cache key based on the available keys
        key_parts = [product[key] for key in available_keys]
        key = '_'.join(key_parts)

        # Check if release info is in the cache
        release_info = release_cache.get(key)

        if release_info is None or len(release_info) < 2:
            # If not in the cache, fetch the latest release info and update the
            # cache
            release_info = get_latest_release(**product)
            if release_info is None or len(release_info) < 2:
                # Log an error message and continue to the next product if
                # fetched data is still invalid
                app.logger.error(
                    f'Invalid release_info for key {key}: {release_info}')
                # Skip to the next iteration of the loop, ignoring the current
                # product
                continue

            # Update the cache with the valid fetched data
            release_cache.set(key, release_info)

        # Use the release_info for the product
        version, release_date = release_info

        # Check and convert release_date to datetime object if it's a string
        if isinstance(release_date, str):
            release_date = dt.fromisoformat(release_date.rstrip('Z'))

        major_minor = '.'.join(version.split('.')[:2])
        link = (
            f"https://docs.mirantis.com/{product['product']}/"
            f"{major_minor}/release-notes/{version.replace('.', '-')}.html"
        )
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

    # Before calling writeString, ensure all items have real datetime objects
    # for pubdate
    for item in feed.items:
        if not isinstance(item['pubdate'], dt):
            item['pubdate'] = dt.now()  # Or another suitable datetime value

    response = Response(feed.writeString('utf-8'),
                        content_type='application/rss+xml; charset=utf-8')
    logging.info('RSS feed generated successfully.')
    return response


# Initialize the cache and the scheduler
update_cache()
scheduler = BackgroundScheduler()
scheduler.add_job(update_cache, 'interval', hours=12)
logging.info('Scheduler started with job to update cache every 12 hours.')
scheduler.start()

if __name__ == '__main__':
    logging.info('Starting application...')
    is_debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host="0.0.0.0", port=4000, debug=is_debug_mode)
    logging.info('Application stopped.')
