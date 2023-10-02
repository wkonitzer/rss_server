import re
from datetime import datetime

import requests
import yaml
from bs4 import BeautifulSoup
import importlib


def fetch_mcr(product_config):
    config = importlib.import_module('config')
    config.logger.debug('fetch_mcr called with configuration: %s',
                        product_config)
    
    repository = product_config.get('repository')
    channel = product_config.get('channel', 'stable')
    component = product_config.get('component', 'docker')
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
        
    except requests.RequestException as e:
        config.logger.error('HTTP request failed: %s', e)
        return []
    except Exception as e:
        config.logger.error("An unexpected error occurred: %s", e)
        return []           


def fetch_mke(product_config):
    config = importlib.import_module('config')
    config.logger.debug('fetch_mke called with configuration: %s',
                        product_config)
    
    repository = product_config.get('repository')
    registry = product_config.get('registry', 'https://hub.docker.com')
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

    except (requests.RequestException, requests.HTTPError) as e:
        config.logger.error("Error fetching %s: %s", url, e)
        return []
    except Exception as e:
        config.logger.error("An unexpected error occurred: %s", e)
        return []

def fetch_msr(product_config):
    config = importlib.import_module('config')
    config.logger.debug('fetch_msr called with configuration: %s',
                        product_config)
    
    repository = product_config.get('repository')
    registry = product_config.get('registry', 'https://registry.mirantis.com')
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