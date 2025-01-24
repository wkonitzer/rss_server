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
    def generate_mcc_link(version):
        return (f"https://docs.mirantis.com/container-cloud/latest/"
                f"release-notes/releases/{version.replace('.', '-')}.html")

    def generate_mcp_link(version):
        last_part = version.split('.')[-1]
        return (f"https://docs.mirantis.com/mcp/q4-18/mcp-release-notes/mu/"
                f"mu-{last_part}.html")

    def generate_mosk_link(version):
        version_parts = version.split('.')
        series_format = '.'.join(version_parts[:2])
        version_format = '.'.join(version_parts)
        return (f"https://docs.mirantis.com/mosk/latest/"
                f"release-notes/{series_format}-series/"
                f"{version_format}.html")

    def generate_k0s_link(version):
        return f"https://github.com/k0sproject/k0s/releases/tag/v{version}+k0s.0"

    def generate_lagoon_link(version):
        return f"https://github.com/uselagoon/lagoon/releases/tag/v{version}"

    def generate_mke_link(version):
        major_minor = '.'.join(version.split('.')[:2])
        version_parts = version.split('.')
        if int(version_parts[0]) < 4:
            return (f"https://docs.mirantis.com/mke/{major_minor}/release-notes/"
                    f"{version.replace('.', '-')}.html")
        return f"https://docs.mirantis.com/mke-docs/docs/release-notes/{version}/"

    def generate_lens_link(version):
        version_format = '-'.join(version.split('.'))
        base_url = "https://forums.k8slens.dev/t/lens-"
        first_url = base_url + version_format + "-latest-release"
        second_url = base_url + version_format + "-latest-patch-release"

        try:
            response = requests.get(first_url, timeout=5)
            if response.status_code == 200:
                logger.debug("Using the first URL: %s", first_url)
                return first_url
        except requests.RequestException:
            logger.warning("Failed to fetch the first URL.")

        logger.debug("Using the second URL: %s", second_url)
        return second_url

    def default_link(version):
        major_minor = '.'.join(version.split('.')[:2])
        return (f"https://docs.mirantis.com/{product['product']}/"
                f"{major_minor}/release-notes/"
                f"{version.replace('.', '-')}.html")

    # Dispatch table
    link_generators = {
        'mcc': generate_mcc_link,
        'mcp': generate_mcp_link,
        'mosk': generate_mosk_link,
        'k0s': generate_k0s_link,
        'lagoon': generate_lagoon_link,
        'mke': generate_mke_link,
        'lens': generate_lens_link,
    }

    # Generate link based on the product
    return link_generators.get(product['product'], default_link)(version)
