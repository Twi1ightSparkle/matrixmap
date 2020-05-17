## Import modules
import dns
import json
import logging
import re
import requests
import ssl
import socket
import srvlookup
import urllib3
from fake_useragent import UserAgent


## Functions

def resolve_well_known(hostname):
    """Get delegated hostname and port from hostname

    Try and look up the well-know server file for a hostname, then if this file exists return
    the delegated hostname and port, or return an empty string if no well known server file exists.

    Args:
        hostname: A hostname as found in the Matrix ID
    
    Returns:
        Delegated hostname and port in the format sub.domain.tld:port:wellknown
        Or an empty string
    """

    # Set a random valid user-agent
    ua = UserAgent()
    headers = {'User-Agent': ua.random}

    # Set well-known URL
    well_known_url = f'https://{hostname}/.well-known/matrix/server'

    # Try to downlad well-known server file
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    try:
        well_known_request = requests.get(well_known_url, headers=headers, allow_redirects=True, verify=False, timeout=3)
    except (
        dns.name.LabelTooLong,
        NameError,
        requests.exceptions.ConnectionError,
        requests.exceptions.InvalidURL,
        requests.exceptions.ReadTimeout,
        requests.exceptions.SSLError,
        requests.exceptions.TooManyRedirects,
        socket.timeout,
        ssl.SSLCertVerificationError,
        ssl.SSLError,
        UnicodeError,
        urllib3.exceptions.MaxRetryError,
        urllib3.exceptions.NewConnectionError

    ):
        return(None)

    # If not 200
    if not well_known_request.status_code == 200:
        return(None)

    # Try and decode json, then split domain.tld:port
    try:
        delegated_hostname, delegated_port = str(well_known_request.json()['m.server']).split(':')

    # If converting to json fails it's probably a bitstream or something
    except json.decoder.JSONDecodeError:
        return(None)
    
    except (ValueError, KeyError):
        delegated_port = 443
    
    else: 
        return(f'{delegated_hostname}:{delegated_port}:wellknown')


def resolve_srv(hostname):
    """Get delegated hostname and port from DNS SRV record

    Try and look up the DNS SRV record for a hostname, then if this exists return
    the delegated hostname, port and srv, or return an empty string if no well known server file exists.

    Args:
        hostname: A hostname as found in the Matrix ID
    
    Returns:
        Delegated hostname and port in the format sub.domain.tld:port:srv
        Or an empty string
    """

    # Turn off annoying logging to terminal from srv lookup
    logger = logging.getLogger('srvlookup').setLevel(logging.CRITICAL)
    logger = logger
    
    # Try and look up SRV record
    try:
        srv = srvlookup.lookup('matrix', 'TCP', hostname)

    # SRV lookup fail (except no record found)
    except (srvlookup.SRVQueryFailure, UnicodeError, dns.name.LabelTooLong):
        return(None)
    
    # SRV lookup returns something
    else:
        # Successful SRV lookup
        if 'Error querying SRV' not in srv[0]:
            delegated_hostname = srv[0].hostname
            delegated_port = srv[0].port
            return(f'{delegated_hostname}:{delegated_port}:srv')
        
        # Error quering
        else:
            return(None)


def resolve_delegated_homeserver(hostname):
    """Return delegated hostname and port from a hostname

    Tries to looks up well-known server file, then SRV DNS record.
    If both fail, return the arg hostname with assumed port 8448

    Args:
        hostname: hostname (the domain part of a MAtrix ID)

    Returns:
        A string containing delegated hostname and port for the hostname in this format:
        sub.domain.tld:port:server-resolve-type
    """

    # If hostname is an ip
    pattern = re.compile(r'\d+\.\d+\.\d+\.\d')
    if pattern.match(hostname):
        return(f'{hostname}:8448:ip')

    # If a well-known
    temp = resolve_well_known(hostname)
    if temp:
        return temp
    
    # If a srv
    temp = resolve_srv(hostname)
    if temp:
        return temp
    
    # Else, assume A or AAAA and assume port 8448
    return(f'{hostname}:8448:a')


def https_download(hostname, path, port=443):
    """Try and download something over https

    Try and download something from https. Decode and return whatever it downloaded or return empty of download failed

    Args:
        hostname: A hostname or an IP address
        path: What do download. For example /_matrix/static
        port: A port, default 443
    
    Returns:
        Some decoded content if there is some or not 404. If 404 or otherwise fail, return empty string
    """

    # Set a random valid user-agent
    ua = UserAgent()
    headers = {'User-Agent': ua.random}

    # Set  URL
    url = f'https://{hostname}:{port}{path}'

    # Try and download
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    try:
        http_request = requests.get(url, headers=headers, allow_redirects=True, verify=False, timeout=3)
    except (
        dns.name.LabelTooLong,
        NameError,
        requests.exceptions.ConnectionError,
        requests.exceptions.InvalidURL,
        requests.exceptions.ReadTimeout,
        requests.exceptions.SSLError,
        requests.exceptions.TooManyRedirects,
        socket.timeout,
        ssl.SSLCertVerificationError,
        ssl.SSLError,
        UnicodeError,
        urllib3.exceptions.MaxRetryError,
        urllib3.exceptions.NewConnectionError

    ):
        return(None)

    # If not 200
    if not http_request.status_code == 200:
        return(None)

    # Try and decode json, then split domain.tld:port
    try:
        delegated_hostname, delegated_port = str(http_request.json()['m.server']).split(':')

    # If converting to json fails it's probably a bitstream or something
    except json.decoder.JSONDecodeError:
        return(None)

    # Split on : fail due to no : being present, assume port 443
    except ValueError:
        return(f'{delegated_hostname}:443')
    
    else: 
        return(f'{delegated_hostname}:{delegated_port}')


def check_matrix_server(hostname):
    """Check if and save there is a Synapse or Dendrite server on a url

    Check if there is a Synapse or Dendrite server on a url:port. If there is a Synapse/Dendrite there,
    look up IP and version, then store information to database

    Args:
        hostname: Some URL from Matrix IDs in format sub.domain.com
    
    Return:
        A string with delegated hostname, IP, port and resolve type if the hostname is active.
        Return None if not a Matrix server or server is dead.
    """
    
    # Clean up hostname to exclude errors
    hostname = hostname.strip()
    hostname = hostname.replace('http://', '')
    hostname = hostname.replace('https://', '')
    if '!' in hostname:
        hostname = hostname.replace('!', '')
        _, hostname = hostname.split(':', 1)
    if '?' in hostname:
        hostname, _ = hostname.split('?', 1)
    if '#' in hostname:
        hostname = hostname.replace('#', '')

    # If port is already known
    port = None
    if ':' in hostname:
        hostname, port = hostname.split(':')

    # Get delegated stuff
    delegated_hostname, delegated_port, server_lookup_type = str(resolve_delegated_homeserver(hostname)).split(':')

    if port:
        delegated_port = port

    # Set a random valid user-agent
    ua = UserAgent()
    headers = {'User-Agent': ua.random}

    # Set version URL
    version_url = f'https://{delegated_hostname}:{delegated_port}/_matrix/federation/v1/version'
    
    # Try to downlad version
    valid_ssl = True
    try:
        version_request = requests.get(version_url, headers=headers, allow_redirects=True, timeout=3)
    
    # If ssl error
    except (requests.exceptions.SSLError, ssl.SSLCertVerificationError, ssl.SSLError):
        try:
            version_request = requests.get(version_url, headers=headers, allow_redirects=True, verify=False, timeout=3)
        except (
            dns.name.LabelTooLong,
            NameError,
            requests.exceptions.ConnectionError,
            requests.exceptions.InvalidURL,
            requests.exceptions.ReadTimeout,
            requests.exceptions.SSLError,
            requests.exceptions.TooManyRedirects,
            socket.timeout,
            ssl.SSLCertVerificationError,
            ssl.SSLError,
            UnicodeError,
            urllib3.exceptions.MaxRetryError,
            urllib3.exceptions.NewConnectionError
        ):
            pass
        valid_ssl = False
    
    # If connection error
    except (
        dns.name.LabelTooLong,
        NameError,
        requests.exceptions.ConnectionError,
        requests.exceptions.InvalidURL,
        requests.exceptions.ReadTimeout,
        requests.exceptions.TooManyRedirects,
        socket.timeout,
        UnicodeError,
        urllib3.exceptions.MaxRetryError,
        urllib3.exceptions.NewConnectionError

    ):
        return(None)

    # If not response code 200
    try:
        if not version_request.status_code == 200:
            return(None)
    except:
        return(None)

    
    # Try and decode json
    try:
        version_json = version_request.json()

    # If converting to json fails it's probably a bitstream or something
    except json.decoder.JSONDecodeError:
        return(None)
    
    # Get version data
    else:
        name = version_json['server']['name']
        version = version_json['server']['version']
    
    # Get the IP for the Matrix server
    delegated_ip = socket.gethostbyname(delegated_hostname)
    
    # Create ; separated string and return it
    out_string = f'{hostname};{delegated_hostname};{delegated_ip};{delegated_port};{server_lookup_type};{name};{version};'
    if valid_ssl:
        out_string += 'yes'
    else:
        out_string += 'no'
    return(out_string)
