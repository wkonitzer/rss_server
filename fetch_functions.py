"""
This module contains functions to fetch the latest release information for
specified products from different types of repositories and registries.
"""

import re
from datetime import datetime
import importlib

import requests
import yaml
from bs4 import BeautifulSoup


def fetch_mcr(product_config):
    """
    Fetch and return the latest release information for MCR.

    :param product_config: Configuration dictionary containing details about
    the product such as 'repository', 'channel', and 'component'.
    :type product_config: dict
    :return: A list of dictionaries each containing 'name' and 'date' of a
             release.
    :rtype: list of dict
    """
    config = importlib.import_module('config')
    config.logger.debug('fetch_mcr called with configuration: %s',
                        product_config)

    repository = product_config.get('repository')
    channel = product_config.get('channel')
    component = product_config.get('component')
    url = f"{repository}/win/static/{channel}/x86_64/"

    config.logger.debug('Constructed URL: %s', url)

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()

        config.logger.debug('HTTP response status: %s', response.status_code)
        config.logger.debug('HTTP response text: %s', response.text)

        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text()

        pattern = re.compile(
            rf"{component}-([0-9]+\.[0-9]+\.[0-9]+)\.zip\s+"
            rf"([0-9]+-[0-9]+-[0-9]+)\s+([0-9]+:[0-9]+:[0-9]+)"
        )

        releases = []
        for match in pattern.finditer(page_text):
            version = match.group(1)
            datetime_str = f"{match.group(2)} {match.group(3)}"
            datetime_object = datetime.strptime(datetime_str,
                                                '%Y-%m-%d %H:%M:%S')
            releases.append({'name': version, 'date': datetime_object})

        config.logger.debug('Parsed releases: %s', releases)

        return releases

    except requests.RequestException as request_exception:
        config.logger.error('HTTP request failed: %s', request_exception)
        return []
    except ValueError as value_error:
        config.logger.error("An unexpected error occurred: %s", value_error)
        return []


def fetch_mke(product_config):
    """
    Fetches the latest release information for the specified MKE product from
    Docker Hub's registry.

    This function constructs a URL based on the provided configuration and
    sends an HTTP GET request to it. The response is then parsed to extract
    release information, which is returned as a list of dictionaries, each
    containing the name and date of a release.

    Parameters:
        product_config (dict): A dictionary containing the configuration for
            the product, which includes 'repository' and optionally 'registry'.
            Example:
                {
                    'repository': 'mirantis/ucp',
                    'registry': 'https://hub.docker.com'  # optional
                }

    Returns:
        list: A list of dictionaries containing the name and date of each
        release. If an error occurs or no releases are found, returns an empty
        list.
        Example:
            [{'name': '3.4.5',
             'date': datetime.datetime(2023, 10, 1, 12, 0, 0)}]

    Raises:
        ValueError: If required keys are missing in the product_config.
        requests.RequestException: For issues related to the HTTP request.
    """
    config = importlib.import_module('config')
    config.logger.debug('fetch_mke called with configuration: %s',
                        product_config)

    repository = product_config.get('repository')
    registry = product_config.get('registry')
    url = f"{registry}/v2/repositories/{repository}/tags"

    config.logger.debug('Constructed URL: %s', url)

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()

        config.logger.debug('HTTP response status: %s', response.status_code)
        config.logger.debug('HTTP response text: %s', response.text)

        data = response.json()
        releases = []
        for tag in data.get('results', []):
            tag_name = tag.get('name')
            date_str = tag.get('tag_last_pushed', '')

            config.logger.debug('Processing tag: %s, Date: %s',
                                tag_name, date_str)

            if tag_name and date_str and re.match('^[0-9]+\\.[0-9]+\\.[0-9]+$',
                                                  tag_name):
                date_object = datetime.strptime(date_str,
                                                '%Y-%m-%dT%H:%M:%S.%fZ')
                releases.append({'name': tag_name, 'date': date_object})

        config.logger.debug('Parsed releases: %s', releases)

        return releases

    except (requests.RequestException, requests.HTTPError) as request_error:
        config.logger.error("Error fetching %s: %s", url, request_error)
        return []
    except ValueError as value_error:
        config.logger.error("Value error occurred: %s", value_error)
        return []

def fetch_msr(product_config):
    """
    This code block fetches release information for a specified MSR product
    from either the Mirantis registry or a Helm chart repository, based on the
    provided configuration. It constructs the appropriate URL, sends an HTTP
    GET request, and processes the response to extract release details. 

    Configuration settings are imported, and the logger from the config module
    is utilized to log process details and any potential errors. The URL is
    constructed dynamically based on the product configuration and the major
    version of the specified branch.

    The code sends an HTTP GET request to the constructed URL and logs the HTTP
    response status and text. If the branch_major is 3 or above, the response
    text is interpreted as YAML; otherwise, it's interpreted as JSON. The
    parsed data, along with the branch information, is then passed to the
    'parse_msr_releases' function to extract the release details.

    In case of errors during the HTTP request, such as connectivity problems,
    timeout, or unsuccessful HTTP status, appropriate exceptions are caught,
    and error messages are logged. If an error occurs during the response text
    parsing as YAML or JSON, a ValueError is caught and logged.

    Parameters:
        product_config (dict): Contains product configuration details like
            'repository', 'registry', and 'branch'.
            Example:
                {
                    'repository': 'msr/msr',
                    'registry': 'https://registry.mirantis.com',
                    'branch': '3.1'
                }

    Returns:
        list: Returns a list of dictionaries, each containing the 'name' and
        'date' of a release, returned by the 'parse_msr_releases' function.
        Returns an empty list if any error occurs during the process.

    Raises:
        requests.RequestException: For issues related to the HTTP request, such 
        asconnectivity problems or timeout.
        requests.HTTPError: If the HTTP request receives an unsuccessful status
        code.
        yaml.YAMLError: If there is an error in parsing the YAML response from
        the Helm chart repository.
        ValueError: For errors in interpreting the response text as YAML or
        JSON, or in parsing the date string in 'parse_msr_releases'.
    """
    config = importlib.import_module('config')
    config.logger.debug('fetch_msr called with configuration: %s',
                        product_config)
    repository = product_config.get('repository')
    registry = product_config.get('registry')
    branch = product_config.get('branch')
    branch_major = int(branch.split('.')[0]) if branch else None

    base_url = (
        f"{registry}/charts/{repository}"
        if branch_major and branch_major >= 3
        else f"{registry}/v2/repositories/{repository}"
    )
    url = (
        f"{base_url}/index.yaml"
        if branch_major and branch_major >= 3
        else f"{base_url}/tags"
    )
    config.logger.debug('Constructed URL: %s', url)

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        config.logger.debug('HTTP response status: %s', response.status_code)
        config.logger.debug('HTTP response text: %s', response.text)

        data = (yaml.safe_load(response.text) 
                if branch_major and branch_major >= 3 
                else response.json())
        return parse_msr_releases(data, branch)
    except (requests.RequestException, 
            requests.HTTPError, 
            yaml.YAMLError) as request_error:
        config.logger.error("Error fetching %s: %s", url, request_error)
        return []
    except ValueError as value_error:
        config.logger.error("Value error occurred: %s", value_error)
        return []

def parse_msr_releases(data, branch):
    """
    Parses the release information from the provided data and returns a list
    of dictionaries, each representing a release with its name and date.

    This function iterates over the data, extracting the app version and 
    creation date of each release, then filters the releases based on the 
    provided branch and returns a list of the remaining releases.

    Parameters:
        data (dict): A dictionary containing the release data to be parsed.
        branch (str): The branch of the product to filter the releases by. 
                      Releases not belonging to this branch are discarded.

    Returns:
        list: A list of dictionaries, each containing the 'name' and 'date' 
              of a release. For example:
              [
                  {'name': '3.4.5', 'date': datetime.datetime(2023, 10, 1,
                                                              12, 0, 0)}
              ]

    Raises:
        ValueError: If there is an error in parsing the date string.

    Notes:
        If the 'appVersion' contains a '-', it is discarded.
        If the 'created' key is missing or empty, a warning is logged.
        If a branch is specified, releases not belonging to this branch are
        discarded.
    """    
    config = importlib.import_module('config')
    releases = []
    for entry in data.get('entries', {}).get('msr', []):
        app_version = entry.get('appVersion')
        date_str = entry.get('created', '')
        if app_version and '-' not in app_version:
            if date_str:
                try:
                    date_object = datetime.strptime(date_str,
                                                    '%Y-%m-%dT%H:%M:%S.%fZ')
                    releases.append({'name': app_version, 'date': date_object})
                except ValueError:
                    config.logger.error("Error parsing date string: %s",
                                        date_str)
            else:
                config.logger.warning("No date found for version %s",
                                      app_version)

    if branch:
        major, minor = map(int, branch.split('.'))
        releases = [
            release for release in releases 
            if release['name'].split('.')[0] == str(major) 
            and release['name'].split('.')[1] == str(minor)
        ]
    return releases
