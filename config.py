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
import os
import logging

from fetch_functions import (
    fetch_mcr,
    fetch_mke,
    fetch_msr,
    fetch_mcc,
    fetch_mosk,
    fetch_k0s,
    fetch_mcp,
    fetch_lens
)


# Get logging level from environment variable. If not set, default to INFO
LOGGING_LEVEL = os.environ.get('LOGGING_LEVEL', 'INFO')
LOGGING_LEVEL = getattr(logging, LOGGING_LEVEL.upper(), logging.INFO)

logger = logging.getLogger(__name__)
logger.setLevel(LOGGING_LEVEL)

console_handler = logging.StreamHandler()
console_handler.setLevel(LOGGING_LEVEL)
formatter = logging.Formatter(
    '%(threadName)s - %(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
console_handler.setFormatter(formatter)

# Avoiding duplicate logging, in case a handler is already added by basicConfig
if not logger.hasHandlers():
    logger.addHandler(console_handler)

# List of Mirantis products and their repository information
PRODUCTS = [
    {
        'product': 'mcr',
        'repository': 'https://repos.mirantis.com',
        'channel': 'stable',
        'component': 'docker',
        'fetch_function': fetch_mcr
    },
    {
        'product': 'mcp',
        'repository': 'https://mirror.mirantis.com',
        'channel': 'update',
        'fetch_function': fetch_mcp
    },
    {
        'product': 'mke',
        'repository': 'mirantis/ucp',
        'registry': 'https://hub.docker.com',
        'fetch_function': fetch_mke
    },
    {
        'product': 'msr',
        'repository': 'msr/msr',
        'registry': 'https://registry.mirantis.com',
        'branch': '3.1',
        'fetch_function': fetch_msr
    },
    {
        'product': 'mcc',
        'url': 'https://binary.mirantis.com',
        'prefix': 'releases/kaas/',
        'fetch_function': fetch_mcc
    },
    {
        'product': 'mosk',
        'url': 'https://binary.mirantis.com',
        'prefix': 'releases/cluster/',
        'fetch_function': fetch_mosk
    },
    {
        'product': 'k0s',
        'url': 'https://github.com/k0sproject/k0s/releases/latest',
        'fetch_function': fetch_k0s
    },
    {
        'product': 'lens',
        'url': 'https://api.k8slens.dev/binaries/latest.json',
        'fetch_function': fetch_lens
    },
]

# Cache expiration time in seconds
CACHE_TIMEOUT = int(os.environ.get('CACHE_TIMEOUT', 86400))  # 24 hours

# Port and host settings
PORT = int(os.environ.get('PORT', 4000))
HOST = os.environ.get('HOST', '0.0.0.0')

# Scheduler interval in hours
SCHEDULER_INTERVAL = int(os.environ.get('SCHEDULER_INTERVAL', 12))
