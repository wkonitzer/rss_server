"""
config.py

Configuration module for setting up the list of Mirantis products and their
repository information, cache timeout, port, host, and scheduler interval
settings.

This module contains the following configurations:
- PRODUCTS: A list of dictionaries containing product information such as name,
            repository URL, channel, component, etc.
- CACHE_TIMEOUT: The expiration time for cache in seconds.
- PORT: The port number on which the application will run.
- HOST: The host on which the application will run.
- SCHEDULER_INTERVAL: The interval in hours at which the scheduler runs.

Example:
PRODUCTS = [
    {
        'product': 'mcr',
        'repository': 'https://repos.mirantis.com',
        'channel': 'stable',
        'component': 'docker'
    },
    ...
]

"""

# List of Mirantis products and their repository information
PRODUCTS = [
    {
        'product': 'mcr',
        'repository': 'https://repos.mirantis.com',
        'channel': 'stable',
        'component': 'docker'
    },
    {
        'product': 'mke',
        'repository': 'mirantis/ucp',
        'registry': 'https://hub.docker.com'
    },
    {
        'product': 'msr',
        'repository': 'msr/msr',
        'registry': 'https://registry.mirantis.com',
        'branch': '3.1'
    },
]

# Cache expiration time in seconds
CACHE_TIMEOUT = 86400  # 24 hours

# Port and host settings
PORT = 4000
HOST = "0.0.0.0"

# Scheduler interval in hours
SCHEDULER_INTERVAL = 12
