## Import modules
import configparser
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


## Import other python files
from util import import_hostnames


## Functions

def detect_matrix(line):
    """Determing if Matrix server

    Try and determine if a Matrix server is running on this IP.

    Args:
        line: A text string.

    Returns:
        json response
    """

    data = json.loads(line)
    if data['transport'] == 'tcp':
        longitude = data['location']['longitude']
        latitude = data['location']['latitude']
        ip = data['ip_str']
        ip_https = 'https://' + str(ip) + ':8448/_matrix/federation/v1/version'

        if latitude and longitude:
            latitude = round(latitude, 4)
            longitude = round(longitude, 4)

            try:
                # curl
                # -k, --insecure
                #       (TLS) By default, every SSL connection curl makes is verified to be secure. This option allows curl to proceed
                #       and operate even for server connections otherwise considered insecure.
                # -s, --silent
                #       Silent  or  quiet mode. Don't show progress meter or error messages.  Makes Curl mute. It will still output the
                #       data you ask for, potentially even to the terminal/stdout unless you redirect it.
                # -m, --max-time 3
                #       Maximum  time  in  seconds that you allow the whole operation to take.  This is useful for preventing your
                #       batch jobs from hanging for hours due to slow networks or links going down.
                # --tlsv1.1
                #       (TLS) Forces curl to use TLS version 1.1 or later when connecting to a remote TLS server.
                output = subprocess.check_output(['curl', '-k', '-s', '-m', '3', '--tlsv1.1', ip_https])
            except subprocess.CalledProcessError:
                pass
            else:
                if 'Synapse' in str(output) or 'Dendrite' in str(output):
                    return (latitude, longitude, ip)


async def get_data_asynchronous(workers):
    with ThreadPoolExecutor(max_workers=workers) as executor:
        # Set any session parameters here before calling detect_matrix
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(
                executor,
                detect_matrix,
                line, # Allows us to pass in multiple arguments
            )
            for line in lines
        ]
        for response in await asyncio.gather(*tasks):
            if response:
                print(response)


if __name__ == "__main__":
    # Load config
    work_dir = os.path.dirname(os.path.realpath(__file__)) # Get the path for the directory this python file is stored in
    config = configparser.ConfigParser()
    config.read(os.path.join(work_dir, 'config.ini'))
    
    conf_global_data_directory = config.get('Global', 'data_directory')
    conf_files_shodan_filename = config.get('Files', 'shodan_filename')
    try:
        conf_settings_workers = int(config.get('Settings', 'shodan_workers'))
    except ValueError:
        print('Config error. Shodan: workers must be an integer')
        exit(1)

    # Paths
    shodan_export_file_path = os.path.join(work_dir, conf_global_data_directory, conf_files_shodan_filename)

    # Split into workers
    try:
        line_index = int(sys.argv[1])
    except IndexError:  
        print(f'A worker index must be supplied when running this script. For example "python3 {os.path.basename(__file__)} 1"')
        exit(1)

    # Load Shodan export json
    lines = import_hostnames.load_shodan_file(shodan_export_file_path)

    # Quit if the file set in shodan_export_file_path could not be found
    if not lines:
        print('Shodan file does not exist')
        exit(1)

    if line_index > 6:
        lines = lines[line_index * 3500 :]
    else:
        lines = lines[line_index * 3500 : (line_index + 1) * 3500]

    random.shuffle(lines) # Randomize the list

    # Process
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(get_data_asynchronous(conf_settings_workers))
    loop.run_until_complete(future)
