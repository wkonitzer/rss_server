"""
product_utils.py
----------------

This module provides utility functions to aid in generating product-specific
links based on the type and version of the products for the RSS feed generation
service.
"""
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
        # Define link format for 'mcc'
        return (
            f"https://docs.mirantis.com/container-cloud/latest/"
            f"release-notes/releases/{version.replace('.', '-')}.html"
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

    # Default link format (which was already there for other products)
    return (f"https://docs.mirantis.com/{product['product']}/"
            f"{major_minor}/release-notes/"
            f"{version.replace('.', '-')}.html")
