import asyncio
import json
import logging
import os
import random
import re
import socket
import srvlookup
import subprocess
import sys
import requests
from concurrent.futures import ThreadPoolExecutor
from fake_useragent import UserAgent

try:
    from io import BytesIO
except ImportError:
    from StringIO import StringIO as BytesIO


# Paths
workDir = os.path.dirname(os.path.realpath(__file__))
homeservers = open(os.path.join(workDir, 'homeservers.txt'))

# Turn off annoying logging to terminal from srvlookup
logger = logging.getLogger('srvlookup').setLevel(logging.CRITICAL)

def file_len(f_name):
    '''
    Count lines in a file
    Args:
        f_name: Full path to a file
    Returns:
        An int
    '''
    with open(f_name) as f:
        for i, l in enumerate(f):
            l = l
            pass
    return i + 1


# Split into workers. Assuming less than or slightly more than 28k entries
# line_index = int(sys.argv[1])
# processes = int(sys.argv[2])
line_count = file_len(os.path.join(workDir, 'homeservers.txt'))
# index = int(line_count / processes)


lines = [line for line in homeservers]
# if line_index > processes - 2:
#     lines = lines[line_index * index :]
# else:
#     lines = lines[line_index * index : (line_index + 1) * index]

random.shuffle(lines) # Randomize the list


def curl(line):
    '''
    Do curl stuff.

    Args:
        line: a text string

    Returns
        json response
    '''
    homeserver = str(line).strip()

    # Set a rnadom valid user-agent
    ua = UserAgent()
    headers = {'User-Agent': ua.random}

    url = 'https://' + homeserver + '/.well-known/matrix/server'

    try: # Download the server file
        r = requests.get(url, headers=headers, allow_redirects=True)
    except requests.exceptions.SSLError: # Not a valid SSL certificate, return nothing
        return('')

    try: # Try and decode json, then split domain.tld:port
        homeserver_url, homeserver_port = str(r.json()['m.server']).split(':')
    except json.decoder.JSONDecodeError: # Converting to json fails it's probably a bitstream or something
        if 404 in r or '404' in r.content.decode('ISO-8859-1'):
            try: # Try and look up SRV record
                srv = srvlookup.lookup('matrix', 'TCP', homeserver)
            except srvlookup.SRVQueryFailure: # SRV lookup fail (except no record found)
                return('')
            else: # SRV lookup returns something
                if 'Error querying SRV' not in srv[0]: # Successful SRV lookup
                    homeserver_url = srv[0].hostname
                    homeserver_port = srv[0].port
                else: # Error quering
                    return('')
        else:
            return(url, r.content.decode('ISO-8859-1'))
    except ValueError: # Split on : fail due to no : being present, assume port 443
        homeserver_url = str(r.json()['m.server'])
        homeserver_port = '443'

    # Return the homeserver domain and port
    return (homeserver_url, homeserver_port)


async def get_data_asynchronous():
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Set any session parameters here before calling `fetch`
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(
                executor,
                curl,
                line, # Allows us to pass in multiple arguments to `fetch`
            )
            for line in lines
        ]
        for response in await asyncio.gather(*tasks):
            if response:
                print(response)


def main():
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(get_data_asynchronous())
    loop.run_until_complete(future)

main()