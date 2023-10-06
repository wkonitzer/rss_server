"""
product_utils.py
----------------

This module provides utility functions to aid in generating product-specific
links based on the type and version of the products for the RSS feed generation
service.
"""
import requests

from config import logger

def generate_product_link(product, version):
    """
    Generates a product-specific link based on its type and version.
    
    Parameters:
        product (dict): Product details.
        version (str): The version of the product.
    
    Returns:
        str: The URL link specific to the product and version.
    """
    major_minor = '.'.join(version.split('.')[:2])

    if product['product'] == 'mcc':
        return (
            f"https://docs.mirantis.com/container-cloud/latest/"
            f"release-notes/releases/{version.replace('.', '-')}.html"
        )

    if product['product'] == 'mcp':
        # Extract the final part of the version
        last_part = version.split('.')[-1]

        return (
            f"https://docs.mirantis.com/mcp/q4-18/mcp-release-notes/mu/"
            f"mu-{last_part}.html"
        )

    if product['product'] == 'mosk':
        version_parts = version.split('.')
        # Always take the first two parts for the series
        series_format = '.'.join(version_parts[:2])
        version_format = '.'.join(version_parts)  # Convert the entire version

        return (
            f"https://docs.mirantis.com/mosk/latest/"
            f"release-notes/{series_format}-series/"
            f"{version_format}.html"
        )

    if product['product'] == 'k0s':
        return (f"https://github.com/k0sproject/k0s/releases/tag/"
                f"v{version}+k0s.0") 

    if product['product'] == 'lens':
        # Construct the potential URLs
        version_parts = version.split('.')
        version_format = '-'.join(version_parts)
        base_url = "https://forums.k8slens.dev/t/lens-"
        first_url = base_url + version_format + "-latest-release"
        second_url = base_url + version_format + "-latest-patch-release"

        # Check validity of the first URL
        try:
            response = requests.get(first_url, timeout=5)
            if response.status_code == 200:
                logger.debug("Using the first URL: %s", first_url)
                return first_url
        except requests.RequestException:
            logger.warning("Failed to fetch the first URL.")

        # If the first URL is not valid or if there's an exception,
        # return the second URL
        logger.debug("Using the second URL: %s", second_url)
        return second_url

    # Default link format
    return (f"https://docs.mirantis.com/{product['product']}/"
            f"{major_minor}/release-notes/"
            f"{version.replace('.', '-')}.html")
