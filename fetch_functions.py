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
    Fetches and parses the latest release information for a specified MSR
    product from Mirantis registry or a Helm chart repository, based on the
    provided configuration.
    
    The function constructs the request URL from the configuration, sends an
    HTTP GET request to retrieve the release information, and then parses the
    response to extract the relevant details. It returns a list containing
    dictionaries with the name and date of each release found.
    
    Parameters:
        product_config (dict): A configuration dictionary specifying the
            details about the product whose release information is to be
            fetched. It should contain keys such as 'repository', 'registry',
            and 'branch'.
            Example:
                {
                    'repository': 'msr/msr',
                    'registry': 'https://registry.mirantis.com',  # optional, 
                                                         specifies registry URL
                    'branch': '3.1'  # specifies the branch of the product
                }
    
    Returns:
        list: A list of dictionaries, each representing a release with its
            name and date.
            Example:
                [
                    {'name': '3.4.5', 'date': datetime.datetime(2023, 10, 1,
                     12, 0, 0)}
                ]
            Returns an empty list if no releases are found or an error occurs 
            during the fetch operation.
    
    Raises:
        ValueError: If required keys in the product_config are missing.
        requests.RequestException: If there are issues related to the HTTP 
        request, e.g. connectivity problems, timeout, etc.
        yaml.YAMLError: If there is an error in parsing the YAML response from 
        the Helm chart repository.
    
    Notes:
        The function handles fetching from different sources (registry or Helm
        chart repository) based on the branch version specified in the
        product_config. It filters the fetched releases based on the specified
        branch and logs errors and warnings for various failure scenarios.
    """    
    config = importlib.import_module('config')
    config.logger.debug('fetch_msr called with configuration: %s',
                        product_config)

    repository = product_config.get('repository')
    registry = product_config.get('registry')
    branch = product_config.get('branch')

    config.logger.debug('Repository: %s, Registry: %s, Branch: %s',
                        repository, registry, branch)

    releases = []
    branch_major = int(branch.split('.')[0]) if branch else None
    if branch_major and branch_major >= 3:
        url = f"{registry}/charts/{repository}/index.yaml"
        config.logger.debug('Constructed URL: %s', url)

        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()

            config.logger.debug('HTTP response status: %s',
                                response.status_code)
            config.logger.debug('HTTP response text: %s', response.text)

            data = yaml.safe_load(response.text)
            for entry in data.get('entries', {}).get('msr', []):
                app_version = entry.get('appVersion')
                date_str = entry.get('created', '')

                config.logger.debug('Processing app_version: %s, Date: %s',
                                    app_version, date_str)

                if app_version and '-' not in app_version:
                    if date_str:
                        try:
                            date_object = datetime.strptime(date_str,
                                                       '%Y-%m-%dT%H:%M:%S.%fZ')
                            releases.append({'name': app_version,
                                            'date': date_object})
                        except ValueError:
                            config.logger.error(
                                "Error parsing date string: %s", 
                                date_str
                            )
                    else:
                        config.logger.warning(
                            "No date found for version %s", app_version)
        except (requests.RequestException,
                requests.HTTPError, yaml.YAMLError) as e:
            config.logger.error("Error fetching %s: %s", url, e)
    else:
        url = f"{registry}/v2/repositories/{repository}/tags"
        config.logger.debug('Constructed URL: %s', url)

        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()

            config.logger.debug('HTTP response status: %s',
                                response.status_code)
            config.logger.debug('HTTP response text: %s', response.text)

            data = response.json()
            for tag in data.get('results', []):
                tag_name = tag.get('name')
                date_str = tag.get('tag_last_pushed', '')

                config.logger.debug('Processing tag_name: %s, Date: %s',
                                    tag_name, date_str)

                if tag_name != 'latest' and '-' not in tag_name and date_str:
                    date_object = datetime.strptime(date_str,
                                                    '%Y-%m-%dT%H:%M:%S.%fZ')
                    releases.append({'name': tag_name, 'date': date_object})
        except (requests.RequestException, requests.HTTPError) as e:
            config.logger.error("Error fetching %s: %s", url, e)
        except Exception as e:
            config.logger.error("An unexpected error occurred: %s", e)
            return []

    config.logger.debug('Parsed releases before filtering: %s', releases)

    if branch:
        major, minor = map(int, branch.split('.'))
        releases = [
            release for release in releases
            if release['name'].split('.')[0] == str(major)
            and release['name'].split('.')[1] == str(minor)
        ]

    config.logger.debug('Parsed releases after filtering: %s', releases)

    return releases
