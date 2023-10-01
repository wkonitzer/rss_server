# config.py

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
