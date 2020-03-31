import json
import os
import pycurl
import random
import re
import subprocess
import sys
import requests
import asyncio
from concurrent.futures import ThreadPoolExecutor
from timeit import default_timer

try:
    from io import BytesIO
except ImportError:
    from StringIO import StringIO as BytesIO

START_TIME = default_timer()

workDir = os.path.dirname(os.path.realpath(__file__))
shodanFile = open(os.path.join(workDir, 'shodan-export-port-8448.json'))


# f = open(os.path.join(workDir, 'html', 'synapses.js'), 'w+')
# f.write('var addressPoints = [\n')

line_index = int(sys.argv[1])
lines = [line for line in shodanFile]
if line_index > 6:
    lines = lines[line_index * 3500 :]
else:
    lines = lines[line_index * 3500 : (line_index + 1) * 3500]
random.shuffle(lines)
random.shuffle(lines)

def curl(line):
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
    f = open(os.path.join(workDir, 'html', 'synapses.js'), 'w+')
    f.write('var addressPoints = [\n')

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

    f.write('];')
    f.close()


def main():
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(get_data_asynchronous())
    loop.run_until_complete(future)

main()