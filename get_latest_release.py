"""
This module provides a function to fetch the latest release information for
specified products. It supports fetching release information from different
types of repositories and registries, handling each product type uniquely based
on its source of release information.

Dependencies:
    - requests
    - re
    - json
    - yaml
    - BeautifulSoup
    - datetime
    - packaging.version
    - logging
"""

import re
import logging
from datetime import datetime

import requests
import yaml
from bs4 import BeautifulSoup
from packaging.version import Version

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_latest_release(product='mcr',
                       repository=None,
                       registry=None,
                       channel='stable',
                       component='docker',
                       branch=None):
    """
    Fetches the latest release information for a specified product from its
    repository or registry.

    Parameters:
        product (str): The name of the product, default is 'mcr'.
        repository (str): The URL of the product's repository, if applicable.
        registry (str): The URL of the product's registry, if applicable.
        channel (str): The release channel to use, default is 'stable'.
        component (str): The component to look for in the repository, default
                         is 'docker'.
        branch (str): The branch of the product to look for, if applicable.

    Returns:
        tuple: A tuple containing the latest release version as a string and
               its release date as a datetime object.
        Returns (None, None) if no release information is found or in case of
                an error.

    Example:
        >>> get_latest_release(product='mcr',
        repository='https://repos.mirantis.com', channel='stable',
        component='docker')
        ('1.6.17', datetime.datetime(2023, 2, 23, 20, 47, 7))
    """

    logger.info(f'Fetching latest release for product: {product} ...')

    if product == 'mcr':
        url = f"{repository}/win/static/{channel}/x86_64/"
        response = requests.get(url)
        if response.status_code != 200:
            logger.error('Failed to fetch data from %s. Status code: %s',
                         url, response.status_code)
            return "Unexpected response", None

        soup = BeautifulSoup(response.text, 'html.parser')
        # Extracting the text content of the page
        page_text = soup.get_text()

        # Regular expression pattern to match lines like
        # 'containerd-1.6.17.zip   2023-02-23 20:47:07    19577249'
        pattern = re.compile(
            rf"{component}-([0-9]+\.[0-9]+\.[0-9]+)\.zip\s+"
            rf"([0-9]+-[0-9]+-[0-9]+)\s+([0-9]+:[0-9]+:[0-9]+)"
        )

        releases = []
        for match in pattern.finditer(page_text):
            version = match.group(1)
            date_str = match.group(2)
            time_str = match.group(3)

            # Combine date and time strings and convert to datetime object
            datetime_str = f"{date_str} {time_str}"
            datetime_object = datetime.strptime(
                datetime_str, '%Y-%m-%d %H:%M:%S')

            releases.append({'name': version, 'date': datetime_object})

    elif product == 'mke':
        releases = []
        url = f"{registry}/v2/repositories/{repository}/tags"
        response = requests.get(url)
        if response.status_code != 200:
            return "API request to {url} failed."

        data = response.json()
        for tag in data.get('results', []):
            tag_name = tag.get('name')
            # Extract the creation date
            date_str = tag.get('tag_last_pushed', '')
            if tag_name and date_str and re.match('^[0-9]+\\.[0-9]+\\.[0-9]+$',
                                                  tag_name):
                date_object = datetime.strptime(
                    date_str, '%Y-%m-%dT%H:%M:%S.%fZ')
                releases.append({'name': tag_name, 'date': date_object})

    elif product == 'msr':
        releases = []
        branch_major = int(branch.split('.')[0]) if branch else None
        if branch_major and branch_major >= 3:
            url = f"{registry}/charts/{repository}/index.yaml"
            response = requests.get(url)
            if response.status_code != 200:
                return f"Failed to retrieve version info from [{url}]", None

            data = yaml.safe_load(response.text)

            for entry in data.get('entries', {}).get('msr', []):
                app_version = entry.get('appVersion')
                # Use 'created' key to get the creation date
                date_str = entry.get('created', '')

                # Check if app_version is stable
                if app_version and '-' not in app_version:
                    if date_str:
                        try:
                            # Adjust the format string to match the date
                            # string format
                            date_object = datetime.strptime(
                                date_str, '%Y-%m-%dT%H:%M:%S.%fZ')
                        except ValueError:
                            print(f"Error parsing date string: {date_str}")
                            date_object = None
                    else:
                        date_object = None

                    releases.append({'name': app_version, 'date': date_object})

        else:
            registry = "https://hub.docker.com"
            repository = "mirantis/dtr"
            url = f"{registry}/v2/repositories/{repository}/tags"
            response = requests.get(url)
            if response.status_code != 200:
                return (
                    f"Failed to retrieve tags for repository [{repository}]",
                    None
                )

            data = response.json()

            for tag in data.get('results', []):
                tag_name = tag.get('name')
                # Extract the creation date
                date_str = tag.get('tag_last_pushed', '')
                if tag_name != 'latest' and '-' not in tag_name and date_str:
                    date_object = datetime.strptime(
                        date_str, '%Y-%m-%dT%H:%M:%S.%fZ')
                    releases.append({'name': tag_name, 'date': date_object})

        if branch:
            major, minor = map(int, branch.split('.'))
            releases = [
                release for release in releases
                if release['name'].split('.')[0] == str(major)
                and release['name'].split('.')[1] == str(minor)
            ]
    else:
        return "Invalid product"

    if releases:
        # Sort by version and return the latest release and its creation date
        releases.sort(key=lambda x: Version(x['name']), reverse=True)
        latest_release = releases[0]

        date_object = latest_release.get('date')
        logger.info('Latest release for %s: Version - %s, Date - %s',
                    product, latest_release["name"], date_object)
        return latest_release['name'], date_object

    logger.warning('No matching GA releases found for product: %s', product)
    return "No matching GA releases found.", None


if __name__ == "__main__":
    # Test for 'mcr'
    mcr_version, mcr_date = get_latest_release(
        product='mcr', repository='https://repos.mirantis.com',
        channel='stable', component='docker')
    print(f"mcr: Version - {mcr_version}, Date - {mcr_date}")

    # Test for 'mke'
    mke_version, mke_date = get_latest_release(
        product='mke', repository='mirantis/ucp',
        registry='https://hub.docker.com')
    print(f"mke: Version - {mke_version}, Date - {mke_date}")

    # Test for 'msr' with branch '3.1'
    msr_version_31, msr_date_31 = get_latest_release(
        product='msr', repository='msr/msr',
        registry='https://registry.mirantis.com', branch='3.1')
    print(
        f"msr (3.x branch): Version - {msr_version_31}, Date - {msr_date_31}")

    # Test for 'msr' with branch '2.9'
    msr_version_21, msr_date_21 = get_latest_release(
        product='msr', repository='msr/msr',
        registry='https://registry.mirantis.com', branch='2.9')
    print(
        f"msr (2.x branch): Version - {msr_version_21}, Date - {msr_date_21}")
