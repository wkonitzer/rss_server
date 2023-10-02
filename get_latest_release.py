"""
This module provides a function to fetch the latest release information for
specified products. It supports fetching release information from different
types of repositories and registries, handling each product type uniquely based
on its source of release information.

Dependencies:
    - packaging.version
"""
from packaging.version import Version

from config import PRODUCTS
from config import logger


def get_latest_release(product_config):
    """
    Fetch and return the latest release information for a specified product.

    This function extracts product information from the provided configuration,
    calls the appropriate fetch function to retrieve release data, sorts the 
    releases by version, and returns the latest release's name and date.

    Parameters:
        product_config (dict): Configuration dictionary containing details
            about the product. Expected keys include 'product' (product name),
            'fetch_function' (function to fetch release data), and others as
            required by the fetch function.

    Returns:
        tuple: A tuple containing the latest release's name and date. If no
            release data is found, returns (None, None).

    Example:
        config = {
            'product': 'mcr',
            'fetch_function': fetch_mcr_function,
            ...  # other product-specific configurations
        }
        version, date = get_latest_release(config)
    """
    # Extract product name from the configuration, raise an error if not
    # present
    if 'product' not in product_config:
        raise ValueError("Product configuration must contain a 'product' key.")

    product = product_config['product']
    logger.info('Fetching latest release for product: %s...', product)

    # Find the appropriate fetch function from the mapping, or use a lambda
    # that returns an empty list as default
    fetch_function = product_config.get('fetch_function', lambda config: [])

    # Call the fetch function with the product configuration
    logger.debug('Calling %s with config: %s', fetch_function, product_config)
    releases = fetch_function(product_config)

    # If there are any releases, sort them by version and return the latest one
    if releases:
        releases.sort(key=lambda x: Version(x['name']), reverse=True)
        latest_release = releases[0]
        logger.info(
            'Latest release for %s: Version - %s, Date - %s',
            product, latest_release["name"], latest_release["date"]
        )
        return latest_release['name'], latest_release['date']

    logger.warning('No matching GA releases found for product: %s', product)
    return None, None


if __name__ == "__main__":
    for config in PRODUCTS:
        version, date = get_latest_release(config)
        print(
            f"Product: {config.get('product')}, "
            f"Version: {version}, Date: {date}"
        )
