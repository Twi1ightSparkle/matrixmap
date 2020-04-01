import json
import os
import random
import re
import subprocess
import sys
import requests
import asyncio
from concurrent.futures import ThreadPoolExecutor

try:
    from io import BytesIO
except ImportError:
    from StringIO import StringIO as BytesIO


# Paths
workDir = os.path.dirname(os.path.realpath(__file__))
shodanFile = open(os.path.join(workDir, 'shodan-export-port-8448.json'))


# Split into workers. Assuming less than or slightly more than 28k entries
line_index = int(sys.argv[1])
lines = [line for line in shodanFile]
if line_index > 6:
    lines = lines[line_index * 3500 :]
else:
    lines = lines[line_index * 3500 : (line_index + 1) * 3500]
random.shuffle(lines) # Randomize the list


def curl(line):
    '''
    Do curl stuff.

    Args:
        line: a text string

    Returns
        json response
    '''
    data = json.loads(line)
    if data['transport'] == 'tcp':
        lon = data['location']['longitude']
        lat = data['location']['latitude']
        ip = data['ip_str']
        ipHttps = 'https://' + str(ip) + ':8448/_matrix/federation/v1/version'

        if lat and lon:
            lat = round(lat, 4)
            lon = round(lon, 4)

            try:
                output = subprocess.check_output(['curl', '-k', '-s', '-m', '3', '--tlsv1.1', ipHttps])
            except subprocess.CalledProcessError:
                pass
            else:
                if 'Synapse' in str(output):
                    return (lat, lon, ip)


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