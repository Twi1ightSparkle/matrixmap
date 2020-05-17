## Import modules
import asyncio
import configparser
import os
import random
from concurrent.futures import ThreadPoolExecutor

## Import other python files
from util import import_hostnames
from util import resolve_hostname

## Functions

async def get_data_asynchronous(workers):
    with ThreadPoolExecutor(max_workers=workers) as executor:
        # Set any session parameters here before calling check_matrix_server
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(
                executor,
                resolve_hostname.check_matrix_server,
                hostname # Allows us to pass in multiple arguments
            )
            for hostname in hostnames
        ]
        for response in await asyncio.gather(*tasks):
            if response:
                print(response)


if __name__ == "__main__":
    # Load config
    work_dir = os.path.dirname(os.path.realpath(__file__)) # Get the path for the directory this python file is stored in
    config = configparser.ConfigParser()
    config.read(os.path.join(work_dir, 'config.ini'))

    # Global
    conf_global_data_directory = config.get('Global', 'data_directory')
    
    # PostgreSQL
    conf_psql_enabled = config.get('PostgreSQL', 'enabled')
    if conf_psql_enabled == 'Yes':
        try_sql = True
    elif conf_psql_enabled == 'No':
        try_sql = False
    else:
        print('Config error. PostgreSQL: enabled must be either Yes or No')
        exit(1)
    conf_psql_server = config.get('PostgreSQL', 'server')
    try:
        conf_psql_port = int(config.get('PostgreSQL', 'port'))
    except ValueError:
        print('Config error. PostgreSQL: port must be an integer')
        exit(1)
    conf_psql_database = config.get('PostgreSQL', 'database')
    conf_psql_username = config.get('PostgreSQL', 'username')
    conf_psql_password = config.get('PostgreSQL', 'password')
    try:
        conf_psql_limit = int(config.get('PostgreSQL', 'limit'))
    except ValueError:
        print('Config error. PostgreSQL: limit must be an integer')
        exit(1)

    # HomeserverFile
    conf_hs_file_filename = config.get('HomeserverFile', 'filename')

    try:
        conf_processhomeservers_workers = int(config.get('ProcessHomeservers', 'workers'))
    except ValueError:
        print('Config error. ProcessHomeservers: workers must be an integer')
        exit(1)
    conf_processhomeservers_debug = config.get('ProcessHomeservers', 'debug')
    if conf_processhomeservers_debug == 'Yes':
        debug = True
    elif conf_processhomeservers_debug == 'No':
        debug = False
    else:
        print('Config error. ProcessHomeservers: debug must be either Yes or No')
        exit(1)

    # Output
    conf_output_homeservers = config.get('Output', 'homeservers')


    # Set paths
    hostnames_file_path = os.path.join(work_dir, conf_global_data_directory, conf_hs_file_filename)
    out_file_path = os.path.join(work_dir, conf_global_data_directory, conf_output_homeservers)
    
    # Load hostnames
    hostnames = []
    hostnames_from_file = import_hostnames.load_file(hostnames_file_path)
    hostnames_from_postgres = False
    if try_sql:
        hostnames_from_postgres = import_hostnames.get_hostnames_from_postgres(conf_psql_server,
                                                                                conf_psql_port,
                                                                                conf_psql_database,
                                                                                conf_psql_username,
                                                                                conf_psql_password,
                                                                                conf_psql_limit)
    if hostnames_from_file:
        hostnames.extend(hostnames_from_file)
    if hostnames_from_postgres:
        hostnames.extend(hostnames_from_postgres)
    
    # Quit if no hostnames found
    if len(hostnames) < 1:
        print('No hostnames found, quitting')
        exit(1)

    # Split into workers
    # line_index = int(sys.argv[1])
    # processes = int(sys.argv[2])
    # line_count = file_len(hostnames_file))
    # index = int(line_count / processes)

    # Split the list of hostnames into multiple sets
    # if line_index > processes - 2:
    #     hostnames = hostnames[line_index * index :]
    # else:
    #     hostnames = hostnames[line_index * index : (line_index + 1) * index]

    # Randomize the order of the hostname list 
    random.shuffle(hostnames)

    # Print headers for debug
    if debug:
        print('Hostname;Delegated hostname;Delegated IP;Delegated port;Server lookup type;Name;Matrix server version;Valid SSL')

    # Run async stuff
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(get_data_asynchronous(conf_processhomeservers_workers))
    loop.run_until_complete(future)
