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
from packaging.version import Version

def construct_url(repository, channel):
    """
    Constructs and returns the URL to be used for fetching release information
    for MCR based on the provided repository, channel, and component.

    :param repository: The repository where the product is located.
    :type repository: str
    :param channel: The channel which the product belongs to.
    :type channel: str
    :param component: The component of the product.
    :type component: str
    :return: The constructed URL as a string.
    :rtype: str
    """
    return f"{repository}/win/static/{channel}/x86_64/"

def parse_page_text(page_text, component):
    """
    Parses the provided page_text to extract release information based on the
    specified component, and returns a list of dictionaries containing release
    names and dates.

    :param page_text: The text of the page to be parsed for release
    information.
    :type page_text: str
    :param component: The component of the product to extract release 
                      information for.
    :type component: str
    :return: A list of dictionaries, each containing the 'name' and 'date' of a
             release.
    :rtype: list of dict
    """
    pattern = re.compile(
        rf"{component}-([0-9]+\.[0-9]+\.[0-9]+)\.zip\s+"
        rf"([0-9]+-[0-9]+-[0-9]+)\s+([0-9]+:[0-9]+:[0-9]+)"
    )
    releases = []
    for match in pattern.finditer(page_text):
        version = match.group(1)
        datetime_str = f"{match.group(2)} {match.group(3)}"
        datetime_object = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
        releases.append({'name': version, 'date': datetime_object})
    return releases

def fetch_mcr(product_config):
    """
    Fetch and return the latest release information for MCR. 

    This function, utilizing helper functions 'construct_url' and
    'parse_page_text', fetches the latest release information based on the
    given product configuration. It constructs the URL dynamically, sends an
    HTTP GET request, and parses the received HTML page to extract release
    details.

    It utilizes the logger from the 'config' module to log the process details
    and any potential errors.

    Parameters:
        product_config (dict): A dictionary containing product configuration
            details like 'repository', 'channel', and 'component'.
            Example:
                {
                    'repository': '<REPOSITORY_URL>',
                    'channel': '<CHANNEL>',
                    'component': '<COMPONENT>'
                }

    Returns:
        list: A list of dictionaries, each containing the 'name' and 'date' of
              a release.
              Example:
                  [{'name': '3.4.5', 'date': datetime.datetime(2023, 10, 1,
                                                               12, 0, 0)}]

    Raises:
        requests.RequestException: For issues related to the HTTP request, such
                                   as connectivity problems or timeout.
        ValueError: For any unexpected errors during the execution of this
        function.

    Notes:
        This function is part of a module that contains functions to fetch the
        latest release information for specified products from different types
        of repositories and registries.
    """
    config = importlib.import_module('config')
    config.logger.debug('fetch_mcr called with configuration: %s',
                        product_config)

    repository = product_config.get('repository')
    channel = product_config.get('channel')
    component = product_config.get('component')

    url = construct_url(repository, channel)
    config.logger.debug('Constructed URL: %s', url)

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()

        config.logger.debug('HTTP response status: %s', response.status_code)
        config.logger.debug('HTTP response text: %s', response.text)

        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text()

        releases = parse_page_text(page_text, component)

        config.logger.debug('Parsed releases: %s', releases)
        return releases

    except requests.RequestException as request_exception:
        config.logger.error('HTTP request failed: %s', request_exception)
        return []
    except ValueError as value_error:
        config.logger.error("An unexpected error occurred: %s", value_error)
        return []


def fetch_mcp_product_releases(response_content):
    """
    Fetch the product releases from a directory listing.

    Args:
        response_content (str): The directory listing in string format.

    Returns:
        list[dict]: A list containing dictionaries with the keys:
                    - 'name': The version number of the release (
                              e.g., '1.28.2').
                    - 'date': The release date as a datetime object.
                    If no release information is found, the list will be empty.
    """
    
    # Regular expression to match the provided format
    regex_pattern = r"(\d+\.\d+\.\d+)/\s+(\d+-\w+-\d+)\s+(\d+:\d+)"
    
    matches = re.findall(regex_pattern, response_content)

    releases = []
    for version, date, time in matches:
        # Ignore specific version
        if version == "2019.99.99":
            continue

        # Parsing the date and time into a datetime object
        release_date_str = f"{date} {time}"
        release_datetime = datetime.strptime(release_date_str,
                                             "%d-%b-%Y %H:%M")
        
        releases.append({'name': version, 'date': release_datetime})
        
    return releases


def fetch_mcp(product_config):
    """
    Fetch and return the latest release information for MCR. 

    This function, utilizing helper function 'fetch_mcp_product_releases'
    etches the latest release information based on the
    given product configuration. It constructs the URL dynamically, sends an
    HTTP GET request, and parses the received HTML page to extract release
    details.

    It utilizes the logger from the 'config' module to log the process details
    and any potential errors.

    Parameters:
        product_config (dict): A dictionary containing product configuration
            details like 'repository', and 'channel',
            Example:
                {
                    'repository': '<REPOSITORY_URL>',
                    'channel': '<CHANNEL>',
                }

    Returns:
        list: A list of dictionaries, each containing the 'name' and 'date' of
              a release.
              Example:
                  [{'name': '2019.2.24', 'date': datetime.datetime(2023, 10, 1,
                                                               12, 0, 0)}]

    Raises:
        requests.RequestException: For issues related to the HTTP request, such
                                   as connectivity problems or timeout.
        ValueError: For any unexpected errors during the execution of this
        function.

    Notes:
        This function is part of a module that contains functions to fetch the
        latest release information for specified products from different types
        of repositories and registries.
    """
    config = importlib.import_module('config')
    config.logger.debug('fetch_mcp called with configuration: %s',
                        product_config)

    repository = product_config.get('repository')
    channel = product_config.get('channel')

    url = f"{repository}/{channel}"
    config.logger.debug('Constructed URL: %s', url)

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()

        config.logger.debug('HTTP response status: %s', response.status_code)
        config.logger.debug('HTTP response text: %s', response.text)

        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text()

        releases = fetch_mcp_product_releases(page_text)

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

def date_from_human_string(date_str):
    """
    Convert a human-readable date string into a datetime object.

    The input date string should be in the format "Month Day Year", e.g.,
    "Jan 1 2020".
    
    Parameters:
    - date_str (str): A date string in the format "Month Day Year".
    
    Returns:
    - datetime.datetime: A datetime object representing the given date.
    
    Raises:
    - ValueError: If the month in date_str is not recognized.
    """
    month_to_number = {
        'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
        'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
    }

    month_str, day_str, year_str = date_str.split()
    return datetime(int(year_str), month_to_number[month_str], int(day_str))

def fetch_bucket_url_from_response(response):
    """
    Extract the bucket URL from a given HTTP response.

    The function parses the provided response to search for a BUCKET_URL
    pattern. It looks for the BUCKET_URL within a script tag in the HTML
    content of the response. If the bucket URL does not start with 'http', it
    prepends 'https:' to it.

    Parameters:
    - response (requests.Response): The HTTP response object to extract the
    bucket URL from.

    Returns:
    - str or None: Returns the extracted bucket URL as a string if found;
    otherwise, returns None.
    """
    soup = BeautifulSoup(response.text, 'html.parser')
    bucket_url_element = soup.find("script",
                        string=re.compile(r'BUCKET_URL\s*=\s*["\'](.*?)["\']'))

    if not bucket_url_element:
        return None

    match = re.search(r'BUCKET_URL\s*=\s*["\'](.*?)["\']',
                      bucket_url_element.string)
    if not match:
        return None

    bucket_url = match.group(1)
    if not bucket_url.startswith("http"):
        bucket_url = "https:" + bucket_url

    return bucket_url

def fetch_releases_from_bucket(bucket_url_with_prefix):
    """
    Fetch the release versions and their dates from a specified bucket URL
    with prefix.

    The function sends a GET request to the provided bucket URL to retrieve
    the XML content. It then parses this content to extract information about
    the releases present, specifically their names (versions) and the last
    modified dates.

    Parameters:
    - bucket_url_with_prefix (str): The bucket URL appended with the desired
      prefix which defines the path to the releases.

    Returns:
    - list: A list of dictionaries where each dictionary represents a release
      with its name (version) and last modified date. An example element of the
      list:
      {'name': '1.2.3', 'date': datetime.datetime(2022, 1, 1, 12, 0, 0)}

    Raises:
    - requests.HTTPError: If there's an issue with the request to the bucket
      URL.
    """
    config = importlib.import_module('config')
    response = requests.get(bucket_url_with_prefix, timeout=5)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'xml')
    contents = soup.find_all("Contents")

    releases = []
    for content in contents:
        key_tag = content.find("Key")
        date_tag = content.find("LastModified")

        if key_tag and date_tag:
            key_parts = key_tag.text.split('/')
            if len(key_parts) == 3:
                version = key_parts[2].replace('.yaml', '')
                date_str = date_tag.text
                try:
                    date_object = datetime.strptime(date_str,
                                                    '%Y-%m-%dT%H:%M:%S.%fZ')
                    releases.append({'name': version, 'date': date_object})
                except ValueError:
                    config.logger.error("Error parsing date string: %s",
                                        date_str)

    return releases

def fetch_product(product_config, product_name, post_process_func=None):
    """
    Fetch the releases for a specified product from a given URL and optionally
    post-process the results.

    The function retrieves the bucket URL from the product page's response and
    then fetches the releases from the bucket URL with a specific prefix. If a
    post-processing function is provided, it is used to further process or
    filter the fetched releases.

    Parameters:
    - product_config (dict): A configuration dictionary specific to the
      product. It must contain keys 'url' and 'prefix'.
      Example:
        {
            'url': 'https://example.com/product',
            'prefix': 'releases/product/'
        }
    
    - product_name (str): The name of the product being fetched. Used for
      logging purposes.

    - post_process_func (callable, optional): A function to post-process the
      fetched releases. If provided, it should take three arguments: the list
      of fetched releases, the bucket URL, and the prefix. It should return a
      list of post-processed releases.

    Returns:
    - list: A list of dictionaries where each dictionary represents a release
      with its name (version) and last modified date. Example element of the list:
      {'name': '1.2.3', 'date': datetime.datetime(2022, 1, 1, 12, 0, 0)}

    Raises:
    - requests.HTTPError: If there's an issue with the request to the product
      URL.

    Notes:
    - Uses two helper functions: fetch_bucket_url_from_response and
      fetch_releases_from_bucket.
    """
    config = importlib.import_module('config')
    url = product_config.get('url')
    prefix = product_config.get('prefix')

    config.logger.debug('fetch_%s called. Target URL: %s', product_name, url)

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        config.logger.debug("First 500 characters of response:\n%s",
                            response.text[:500])

        bucket_url = fetch_bucket_url_from_response(response)
        if not bucket_url:
            config.logger.error("Unable to extract BUCKET_URL.")
            return []

        bucket_url_with_prefix = bucket_url + "/?prefix=" + prefix
        releases = fetch_releases_from_bucket(bucket_url_with_prefix)

        if post_process_func:
            releases = post_process_func(releases, bucket_url, prefix)

        return releases

    except requests.RequestException as error:
        config.logger.error(
            f"Error fetching {product_name} releases: %s", error
        )
        return []

def fetch_mcc(product_config):
    """
    Fetch the releases for the 'mcc' product using the given product
    configuration.

    This is a wrapper function that delegates the fetching process to the
    fetch_product function for the 'mcc' product.

    Parameters:
    - product_config (dict): A configuration dictionary specific to the 'mcc'
      product. It should contain keys 'url' and 'prefix'.
      Example:
        {
            'url': 'https://example.com/mcc',
            'prefix': 'releases/mcc/'
        }

    Returns:
    - list: A list of dictionaries where each dictionary represents a release
      with its name (version) and last modified date. Example element of the
      list:
      {'name': '1.2.3', 'date': datetime.datetime(2022, 1, 1, 12, 0, 0)}
    """
    return fetch_product(product_config, 'mcc')

def fetch_mosk(product_config):
    """
    Fetch the releases for the 'mosk' product using the given product
    configuration.

    This function additionally uses the post_process_mosk function to
    post-process the fetched releases for the 'mosk' product. It's a
    specialized wrapper for the fetch_product function.

    Parameters:
    - product_config (dict): A configuration dictionary specific to the 'mosk'
      product. It should contain keys 'url' and 'prefix'.
      Example:
        {
            'url': 'https://example.com/mosk',
            'prefix': 'releases/mosk/'
        }

    Returns:
    - list: A list of dictionaries where each dictionary represents a release
      with its name (version) and last modified date. Example element of the
      list:
      {'name': '1.2.3', 'date': datetime.datetime(2022, 1, 1, 12, 0, 0)}
    """
    return fetch_product(product_config, 'mosk', post_process_mosk)

def post_process_mosk(releases, bucket_url, prefix):
    """
    Post-process the fetched MOSK releases to find and extract the latest
    release containing 'openstack'.

    This function filters out versions with hyphens, sorts the remaining
    releases by date and version, and then scans each release's content for the
    presence of "openstack". If found, it extracts and returns the version
    details of the latest such release.

    Parameters:
    - releases (list): A list of dictionaries where each dictionary represents
      a release with its name (version) and last modified date. Example:
      [{'name': '1.2.3', 'date': datetime.datetime(2022, 1, 1, 12, 0, 0)}]

    - bucket_url (str): The base URL of the bucket from which releases are
      fetched.

    - prefix (str): The prefix to append to the bucket URL to construct the
      complete URL to fetch releases.

    Returns:
    - list: A list containing a single dictionary for the latest release with
      its name (version) and date that 
      contains "openstack" in its content. If no such release is found, an
      empty list is returned. 
      Example return value:
      [{'name': '4.5.6', 'date': datetime.datetime(2022, 1, 1, 12, 0, 0)}]

    Notes:
    - Logging is performed throughout the function for debugging purposes
      using a logger from the imported 'config' module.
    """
    config = importlib.import_module('config')

    # Filter out versions with hyphens
    releases = [release for release in releases if '-' not in release['name']]

    # Sort the releases based on the date and if dates are the same, then based
    # on the version.
    sorted_releases = sorted(releases, key=lambda x: (x['date'],
                             Version(x['name'])), reverse=True)

    for release in sorted_releases:
        latest_release_url = f"{bucket_url}/{prefix}{release['name']}.yaml"
        release_content = requests.get(latest_release_url, timeout=5).text

        snippet_start = max(release_content.lower().find("openstack") - 20, 0)
        snippet_end = min(release_content.lower().find("openstack") + 28,
                          len(release_content))
        config.logger.debug("Content Snippet around 'openstack': %s",
                            release_content[snippet_start:snippet_end])

        # Check for the presence of "openstack"
        if re.search(r'\bopenstack\b', release_content, re.IGNORECASE):
            # Now you have the latest_release with "openstack" in its content
            latest_release = release
            break
    else:
        # If the loop completed without breaking (i.e., "openstack" not found
        # in any release)
        config.logger.error("No release containing 'openstack' was found.")
        return []

    # Now, we need to get the content of this latest release and parse it
    latest_release_url = (f"{bucket_url}/releases/cluster/"
                          f"{latest_release['name']}.yaml")
    release_content = requests.get(latest_release_url, timeout=5).text

    # Parsing the version from the release content
    match = re.search(r'version:\s*(\d+\.\d+\.\d+)\+(\d+\.\d+\.\d+)',
                      release_content)
    if match:
        version_prefix = match.group(1)
        version_suffix = match.group(2)
        config.logger.debug("Extracted version prefix: %s", version_prefix)
        config.logger.debug("Extracted version suffix: %s", version_suffix)
        return [{'name': version_suffix, 'date': latest_release['date']}]

    config.logger.error("Version not found in the release content.")
    return []

def fetch_k0s(product_config):
    """
    Fetch the latest release information for the k0s product from GitHub.

    This function retrieves the latest release information for the k0s product
    from its GitHub releases page. It extracts the version number from the URL
    and the release datetime from the page's HTML content.

    Args:
        product_config (dict): Configuration dictionary for the product. 
                               It should contain a 'url' key pointing to 
                               the GitHub releases page for the product.

    Returns:
        list[dict]: A list containing a dictionary with the keys:
                    - 'name': The version number of the release
                              (e.g., '1.28.2').
                    - 'date': The release date as a datetime object.
                    If no release information is found, the list will be empty.

    Raises:
        Requests exceptions for network-related issues.
    """
    releases = []

    try:
        config = importlib.import_module('config')
        url = product_config.get('url')
        config.logger.debug("Fetching release information from: %s", url)

        response = requests.get(url, timeout=5, allow_redirects=True)
        if response.status_code != 200:
            config.logger.warning("Request to %s returned status code: %s",
                                  url, response.status_code)
            return []

        # Extract version from the URL
        version_match = re.search(r'/releases/tag/v([\d.]+)', response.url)
        if version_match:
            version = version_match.group(1)
            config.logger.debug("Found version: %s", version)

            # Extract datetime value from the HTML content
            soup = BeautifulSoup(response.content, 'html.parser')
            datetime_element = soup.find('relative-time',
                                         attrs={"datetime": True})

            if datetime_element:
                datetime_str = datetime_element['datetime']
                config.logger.debug("Found datetime string: %s", datetime_str)

                try:
                    # Replace 'Z' with '+00:00' for UTC timezone representation
                    datetime_str = datetime_str.replace('Z', '+00:00')

                    release_datetime = datetime.fromisoformat(datetime_str)
                    config.logger.debug(
                        "Parsed datetime string to datetime object: %s",
                         release_datetime
                    )

                    naive_datetime = release_datetime.astimezone()
                    config.logger.debug("Converted to system timezone: %s",
                                        naive_datetime)

                    naive_datetime = naive_datetime.replace(tzinfo=None)
                    config.logger.debug("Removed timezone info: %s",
                                        naive_datetime)

                    releases.append({'name': version, 'date': naive_datetime})
                except ValueError as error:
                    config.logger.error("Error while processing datetime: %s",
                                        error)
        else:
            config.logger.error("Couldn't extract version from the URL")

    except requests.RequestException as error:
        config.logger.error("Error fetching data from GitHub: %s", error)

    return releases
