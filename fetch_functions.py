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
from urllib.parse import parse_qsl
from typing import Optional, Dict, List, Tuple

SEMVER_BRANCH = re.compile(r"^\d+\.\d+(?:\.\d+)?$")
_BR_RE = re.compile(r"^\d+\.\d+(?:\.\d+)?$")

def construct_url(repository, channel):
    """
    Constructs and returns the URL to be used for fetching release information
    for MCR based on the provided repository, channel, and component.

    :param repository: The repository where the product is located.
    :type repository: str
    :param channel: The channel which the product belongs to.
    :type channel: str
    :return: The constructed URL as a string.
    :rtype: str
    """
    return f"{repository}/ubuntu/dists/jammy/pool/{channel}/amd64/"

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
        rf"{component}-ee_(\d+\.\d+\.\d+)(?:~(\d+))?[\w\-.~]*_amd64\.deb\s+"
        rf"([0-9]+-[0-9]+-[0-9]+)\s+([0-9]+:[0-9]+:[0-9]+)"
    )
    releases = []
    for match in pattern.finditer(page_text):
        base_version = match.group(1)

        # Assuming ~3 is the base revision number and should result in no suffix.
        revision_number = int(match.group(2)) - 3 if match.group(2) else 0
        if revision_number > 0:
            version = f"{base_version}-{revision_number}"
        else:
            version = base_version
        datetime_str = f"{match.group(3)} {match.group(4)}"
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
    branch = product_config.get('branch')
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
                                               tag_name) and branch in tag_name:
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

def _filter_branch(tags, branch):
    """Return only tags that match the given branch prefix (e.g. '3.1' or '3.1.x')."""
    if not branch or not SEMVER_BRANCH.match(branch):
        return list(tags or [])
    pref = f"{branch}."
    return [t for t in (tags or []) if t == branch or t.startswith(pref)]

def _semver_key(v):
    """Convert a version string into a sortable (major, minor, patch) tuple."""
    try:
        parts = v.split(".")
        parts += ["0"] * (3 - len(parts))
        return tuple(int(p) for p in parts[:3])
    except Exception:
        return (-1, -1, -1)

def _build_chartmuseum_index_like(product, versions):
    """Build a minimal ChartMuseum-like index dict for the given chart versions."""

    entries = [{"apiVersion": "v2", "name": product, "version": v, "urls": []}
               for v in versions]
    return {"apiVersion": "v1", "entries": {product: entries}}

def _parse_bearer_challenge(header_val):
    """Parse a WWW-Authenticate Bearer challenge into (realm, service, scope_dict)."""
    # Example: Bearer realm="https://auth.example/token",service="registry.example",scope="repository:harbor/helm/msr:pull"
    parts = header_val[len("Bearer "):].split(",")
    kv = {}
    for p in parts:
        if "=" in p:
            k, v = p.split("=", 1)
            kv[k.strip()] = v.strip().strip('"')
    realm = kv.get("realm")
    service = kv.get("service")
    scope = kv.get("scope")
    return realm, service, dict(parse_qsl(scope)) if scope and "=" in scope else {"scope": scope}

def _get_registry_token(registry, artifact_path, logger, username=None, password=None, session=None):
    """Obtain a Bearer token for Docker Registry v2 using the server's authenticate challenge."""
    s = session or requests.Session()
    probe_url = f"{registry.rstrip('/')}/v2/{artifact_path}/tags/list"
    r = s.get(probe_url, timeout=10)
    if r.status_code != 401 or "WWW-Authenticate" not in r.headers:
        # Some registries allow anonymous pulls; no token needed.
        return None
    realm, service, scope_map = _parse_bearer_challenge(r.headers["WWW-Authenticate"])
    if not realm:
        logger.debug("Bearer challenge missing realm; proceeding without token.")
        return None

    # Compose scope if not present. Standard scope format:
    #   scope=repository:<name>:pull
    scope = scope_map.get("scope")
    if not scope:
        scope = f"repository:{artifact_path}:pull"

    params = {"service": service, "scope": scope}
    auth = (username, password) if (username and password) else None
    tr = s.get(realm, params=params, auth=auth, timeout=10)
    tr.raise_for_status()
    token = (tr.json() or {}).get("token") or (tr.json() or {}).get("access_token")
    return token

import requests

def _fetch_manifest_created(session: requests.Session,
                            registry: str,
                            artifact_path: str,
                            tag: str,
                            headers: dict,
                            timeout: int = 10) -> str | None:
    """Fetch a tag's manifest and return org.opencontainers.image.created (ISO-8601) or None."""
    url = f"{registry.rstrip('/')}/v2/{artifact_path}/manifests/{tag}"
    # Accept both OCI and Docker manifest types
    h = {"Accept": (
            "application/vnd.oci.image.manifest.v1+json, "
            "application/vnd.oci.artifact.manifest.v1+json, "
            "application/vnd.docker.distribution.manifest.v2+json"
        )}
    if headers:
        h.update(headers)
    try:
        r = session.get(url, headers=h, timeout=timeout)
        r.raise_for_status()
        m = r.json() or {}
        ann = m.get("annotations") or {}
        created = ann.get("org.opencontainers.image.created")
        if not created:
            # Some producers stash annotations under config
            cfg = m.get("config") or {}
            cfg_ann = cfg.get("annotations") or {}
            created = cfg_ann.get("org.opencontainers.image.created")
        # Normalize to Z-suffixed ISO 8601 if needed
        if created and not created.endswith("Z"):
            created = created + "Z"
        return created
    except Exception:
        return None

def _build_chartmuseum_index_like(product: str,
                                  versions: list[str],
                                  created_map: dict[str, str] | None = None) -> dict:
    """Build a minimal ChartMuseum-like index dict for given versions; adds 'created' when available."""
    entries = []
    for v in versions:
        e = {"apiVersion": "v2", "name": product, "version": v, "urls": []}
        if created_map and created_map.get(v):
            e["created"] = created_map[v]
        entries.append(e)
    return {"apiVersion": "v1", "entries": {product: entries}}


def fetch_msr(product_config):
    """
    Fetch MSR releases:
      - MSR 3.x (OCI): registry.mirantis.com/msr/helm/msr
      - MSR 4.x (OCI): registry.mirantis.com/harbor/helm/msr
      - < 3.x legacy:  <registry>/v2/repositories/<repository>/tags (JSON)
    Performs Bearer auth, fetches per-tag manifest 'created', and returns data
    in a ChartMuseum-like shape so existing parsers work unchanged.
    """
    config = importlib.import_module('config')
    logger = config.logger

    logger.debug('fetch_msr called with configuration: %s', product_config)

    repository = product_config.get('repository')            # e.g. 'harbor/helm' or 'msr/msr'
    registry   = product_config.get('registry')              # e.g. 'https://registry.mirantis.com'
    branch     = product_config.get('branch')                # e.g. '4.0', '3.1'
    product    = product_config.get('product', 'msr')        # 'msr'
    username   = product_config.get('username')              # optional
    password   = product_config.get('password')              # optional
    branch_major = int(branch.split('.')[0]) if branch else None

    try:
        # OCI-backed charts (Mirantis Harbor) for >= 3.x
        if branch_major and branch_major >= 3 and "registry.mirantis.com" in registry:
            # Preferred path per major, plus a fallback to the other known path.
            preferred = "harbor/helm/msr" if branch_major >= 4 else "msr/helm/msr"
            alternate = "msr/helm/msr" if branch_major >= 4 else "harbor/helm/msr"

            # If caller gave an explicit parent repo, consider that too.
            explicit = None
            if repository and repository.strip("/"):
                # Only use when it would form <repo>/<product> (e.g., 'harbor/helm/msr')
                explicit = f"{repository.strip('/')}/{product}"

            candidate_paths = [preferred, alternate]
            if explicit and explicit not in candidate_paths:
                candidate_paths.insert(0, explicit)

            s = requests.Session()
            headers: Dict[str, str] = {}
            all_tags: List[str] = []
            chosen_path: Optional[str] = None

            # Try each candidate path until one returns tags
            for artifact_path in candidate_paths:
                url = f"{registry.rstrip('/')}/v2/{artifact_path}/tags/list"
                logger.debug('Trying OCI tags URL: %s', url)

                resp = s.get(url, timeout=10)
                if resp.status_code == 401:
                    token = _get_registry_token(s, registry, artifact_path, logger, username, password)
                    if token:
                        headers = {"Authorization": f"Bearer {token}"}
                        resp = s.get(url, headers=headers, timeout=10)

                if 200 <= resp.status_code < 300:
                    payload = resp.json() or {}
                    tags = payload.get("tags") or []
                    logger.debug("Found %d tags on %s", len(tags), artifact_path)
                    if tags:
                        all_tags = tags
                        chosen_path = artifact_path
                        break
                else:
                    logger.debug("Path %s returned %s; body: %s", artifact_path, resp.status_code, resp.text[:300])

            if not all_tags:
                logger.warning("No tags found on any known artifact path for branch %s", branch)
                return []

            # Filter to the requested branch and sort
            branch_tags = _filter_branch(all_tags, branch)
            branch_tags = sorted(branch_tags, key=_semver_key, reverse=True)
            logger.debug("Branch-filtered tags: %s", branch_tags[:10])

            # Fetch 'created' for each tag (reuse the same session + token)
            created_map: Dict[str, str] = {}
            for t in branch_tags:
                created_map[t] = _fetch_manifest_created(
                    session=s,
                    registry=registry,
                    artifact_path=chosen_path,
                    tag=t,
                    headers=headers
                )

            synthetic_index = _build_chartmuseum_index_like(product, branch_tags, created_map)
            return parse_msr_releases(synthetic_index, branch)

        # Legacy (< 3.x) JSON endpoint
        base_url = f"{registry.rstrip('/')}/v2/repositories/{(repository or '').strip('/')}"
        url = f"{base_url}/tags"
        logger.debug('Constructed URL (legacy tags): %s', url)

        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        logger.debug('HTTP response status: %s', resp.status_code)
        logger.debug('HTTP response text: %s', resp.text)

        data = resp.json()
        return parse_msr_releases(data, branch)

    except (requests.RequestException, requests.HTTPError, yaml.YAMLError) as request_error:
        # 'url' may be the last attempted; safe fallback in log if unset
        try:
            logger.error("Error fetching %s: %s", url, request_error)
        except Exception:
            logger.error("Error fetching releases: %s", request_error)
        return []
    except ValueError as value_error:
        logger.error("Value error occurred: %s", value_error)
        return []

def _parse_iso8601(dt: str):
    """Parse ISO-8601 timestamps with/without fractional seconds; return datetime or None."""
    if not dt:
        return None
    # Normalize trailing Z
    s = dt.rstrip("Z")
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None

def _is_prerelease(v: str) -> bool:
    """Return True if version has a hyphen suffix (e.g., '-rc', '-beta')."""
    return "-" in v if v else False

def _in_branch(v: str, branch: str) -> bool:
    """Return True if version matches 'X.Y' branch (v == 'X.Y' or v startswith 'X.Y.')."""
    if not branch or not v:
        return True
    b = branch.lstrip("v")
    return v == b or v.startswith(b + ".")

def parse_msr_releases(data, branch):
    """
    Parse MSR release info from various backends (ChartMuseum index, OCI tags, Docker Hub).
    Returns [{'name': <version>, 'date': <datetime|None>}, ...] filtered to the given branch.
    Discards pre-releases (versions containing '-').
    """
    config = importlib.import_module('config')
    logger = config.logger
    releases = []

    # Normalize branch ('v4.13' -> '4.13')
    branch = (branch or "").lstrip("v")

    # Case A: ChartMuseum-like shape (real or synthesized)
    entries = data.get("entries") if isinstance(data, dict) else None
    if isinstance(entries, dict):
        # Iterate all charts; keep entries whose appVersion/version match branch and are GA
        for chart_name, chart_entries in entries.items():
            for e in chart_entries or []:
                # Prefer appVersion, else fallback to version
                ver = (e.get("appVersion") or e.get("version") or "").lstrip("v")
                if not ver or _is_prerelease(ver) or not _in_branch(ver, branch):
                    continue
                created = e.get("created") or ""
                dt = _parse_iso8601(created)
                if not dt and created:
                    logger.warning("Unparsable created timestamp for %s: %s", ver, created)
                if not created:
                    logger.warning("No date found for version %s", ver)
                releases.append({"name": ver, "date": dt})
        return releases

    # Case B: Raw OCI tags list
    if isinstance(data, dict) and isinstance(data.get("tags"), list):
        for tag in data["tags"]:
            ver = str(tag).lstrip("v")
            if not ver or _is_prerelease(ver) or not _in_branch(ver, branch):
                continue
            # Tags endpoint has no date; keep it with date=None
            logger.warning("No date available from tags endpoint for version %s", ver)
            releases.append({"name": ver, "date": None})
        return releases

    # Case C: Docker Hub listing (results[] with last_updated)
    if isinstance(data, dict) and isinstance(data.get("results"), list):
        for r in data["results"]:
            ver = str(r.get("name", "")).lstrip("v")
            if not ver or _is_prerelease(ver) or not _in_branch(ver, branch):
                continue
            dt = _parse_iso8601((r.get("last_updated") or "").replace("Z", ""))
            if not dt and r.get("last_updated"):
                logger.warning("Unparsable last_updated for %s: %s", ver, r.get("last_updated"))
            releases.append({"name": ver, "date": dt})
        return releases

    # Fallback: unknown shape — try best-effort keys
    logger.warning("Unknown data shape in parse_msr_releases; data keys: %s", list(data.keys()) if isinstance(data, dict) else type(data))
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
    config.logger.debug("Release url: %s", latest_release_url)
    release_content = requests.get(latest_release_url, timeout=5).text

    # Parsing the version from the release content
    match = re.search(
        (r'version:\s*'
         r'(\d+\.\d+\.\d+|\d+\.\d+)\+'
         r'(\d+\.\d+\.\d+|\d+\.\d+)'),
        release_content
    )
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


def fetch_lens(product_config):
    """
    Fetches the latest release information for the Lens product from a given
    URL.

    The function retrieves release information, including the version and
    release date, from a specified JSON endpoint. It then processes the
    received data, removing the '-latest' suffix from the version and
    converting the release date into a datetime object in the system's local
    timezone.

    Args:
        product_config (dict): A dictionary containing configuration details 
                               for the product, specifically the 'url' key to 
                               denote where to fetch the release information
                               from.

    Returns:
        list[dict]: A list containing a single dictionary with keys:
                    - 'name': The version of the product release.
                    - 'date': The release date as a datetime object.
                    If no valid release information is found or there's an
                    error in processing the response, an empty list is
                    returned.

    Logs:
        Various debug, warning, and error messages to give insights about the 
        status of the operation and any potential issues encountered.
    """
    config = importlib.import_module('config')
    url = product_config.get('url')
    config.logger.debug("Fetching release information from: %s", url)

    # Fetch the content of the URL
    response = requests.get(url, timeout=5)
    if response.status_code != 200:
        config.logger.warning("Received a non-200 status code: %d",
                              response.status_code)
        return []

    try:
        data = response.json()
    except ValueError:
        config.logger.error("Invalid JSON response received.")
        return []

    try:
        version_str = data.get('version')

        # Strip "-latest" from the end of the version string
        version_str = version_str.replace("-latest", "")

        release_date_str = data.get('releaseDate')

        # Convert the date string to a datetime object
        release_date = datetime.fromisoformat(
                                release_date_str.replace("Z", "+00:00"))

        naive_datetime = release_date.astimezone()
        config.logger.debug("Converted to system timezone: %s",
                            naive_datetime)

        naive_datetime = naive_datetime.replace(tzinfo=None)
        config.logger.debug("Removed timezone info: %s",
                            naive_datetime)

        # Construct the result dictionary
        result = {
            'name': version_str,
            'date': naive_datetime
        }

        config.logger.debug("Extracted version: %s and date: %s",
                            result['name'], result['date'])
        return [result]

    except (TypeError, ValueError):
        config.logger.error("Error extracting or converting"
                            " version or release date.")
        return []
