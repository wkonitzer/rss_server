from flask import Flask, Response
import feedgenerator
from apscheduler.schedulers.background import BackgroundScheduler
from get_latest_release import get_latest_release
import datetime
import time

app = Flask(__name__)

class SimpleCache:
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
    {'product': 'mcr', 'repository': 'https://repos.mirantis.com', 'channel': 'stable', 'component': 'docker'},
    {'product': 'mke', 'repository': 'mirantis/ucp', 'registry': 'https://hub.docker.com'},
    {'product': 'msr', 'repository': 'msr/msr', 'registry': 'https://registry.mirantis.com', 'branch': '3.1'},
]


def update_cache():
    for product in products:
        # Determine the available keys in the product dictionary
        available_keys = [key for key in ['product', 'repository', 'channel', 'component', 'registry', 'branch'] if key in product]
    
        # Construct the cache key based on the available keys
        key_parts = [product[key] for key in available_keys]
        key = '_'.join(key_parts)
        
        # Fetch the latest release info and update the cache
        release_info = get_latest_release(**product)
        release_cache.set(key, release_info)


@app.route('/rss')
def rss_feed():
    feed = feedgenerator.Rss201rev2Feed(
        title="Mirantis Software Releases",
        link="http://localhost:5000/",
        description="Latest Mirantis software releases",
        language="en",
    )

    for product in products:
        # Determine the available keys in the product dictionary
        available_keys = [key for key in ['product', 'repository', 'channel', 'component', 'registry', 'branch'] if key in product]
        
        # Construct the cache key based on the available keys
        key_parts = [product[key] for key in available_keys]
        key = '_'.join(key_parts)
        
        # Check if release info is in the cache
        release_info = release_cache.get(key)
        
        if release_info is None:
            # If not in the cache, fetch the latest release info and update the cache
            release_info = get_latest_release(**product)
            release_cache[key] = release_info
        
        # Use the release_info for the product
        version, release_date = release_info
        major_minor = '.'.join(version.split('.')[:2])
        link = f"https://docs.mirantis.com/{product['product']}/{major_minor}/release-notes/{version.replace('.', '-')}.html"
        description = f'<a href="{link}">Release notes for {product["product"].upper()} {version}</a>'
        
        feed.add_item(
            title=f"Mirantis {product['product'].upper()} {version}",
            link=link,
            description=description,
            pubdate=release_date or datetime.datetime.now(),
        )

    response = Response(feed.writeString('utf-8'), content_type='application/rss+xml; charset=utf-8')
    return response


# Initialize the cache and the scheduler
update_cache()
scheduler = BackgroundScheduler()
scheduler.add_job(update_cache, 'interval', hours=12)
scheduler.start()

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
