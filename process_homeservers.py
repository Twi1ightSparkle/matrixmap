## Import modules
import asyncio
import configparser
import os
import random
from concurrent.futures import ThreadPoolExecutor

## Import other python files
from util import import_hostnames
from util import process_data
from util import resolve_hostname

## Functions

async def get_data_asynchronous(workers, delegated_details):
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
                delegated_details.append(response)


if __name__ == "__main__":
    print('Setting up')
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
    conf_psql_limit = config.get('PostgreSQL', 'limit')
    if conf_psql_limit == 'None':
        conf_psql_limit = None
    else:
        try:
            conf_psql_limit = int(config.get('PostgreSQL', 'limit'))
        except ValueError:
            print('Config error. PostgreSQL: limit must be an integer or None')
            exit(1)

    # Files
    conf_files_hs_filename = config.get('Files', 'hs_filename')
    conf_files_shodan_filename = config.get('Files', 'shodan_filename')
    conf_files_del_hs_data = config.get('Files', 'delegated_hs_data')

    try:
        conf_settings_workers = int(config.get('Settings', 'hs_workers'))
    except ValueError:
        print('Config error. Settings: hs_workers must be an integer')
        exit(1)
    conf_settings_debug = config.get('Settings', 'debug')
    if conf_settings_debug == 'Yes':
        debug = True
    elif conf_settings_debug == 'No':
        debug = False
    else:
        print('Config error. Settings: debug must be either Yes or No')
        exit(1)
    


    # Set paths
    hostnames_file_path = os.path.join(work_dir, conf_global_data_directory, conf_files_hs_filename)
    shodan_file_path = os.path.join(work_dir, conf_global_data_directory, conf_files_shodan_filename)
    db_file_path = os.path.join(work_dir, conf_global_data_directory, conf_files_del_hs_data)
    
    # Load hostnames
    print('Loading hostnames')
    hostnames = []
    hostnames_from_file = import_hostnames.load_hostnames_file(hostnames_file_path)
    hostnames_from_shodan = import_hostnames.load_shodan_file(shodan_file_path)
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
    if hostnames_from_shodan:
        hostnames.extend(hostnames_from_shodan)
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

    # Uniq and randomize the order of the hostname list
    hostnames = import_hostnames.unique_list(hostnames)
    random.shuffle(hostnames)

    # for x in hostnames:
    #     print(x)
    # print(len(hostnames))
    # exit(0)

    # Print headers for debug
    if debug:
        print('Hostname;Delegated hostname;Delegated IP;Delegated port;Server lookup type;Name;Matrix server version;Valid SSL')

    # Run async stuff
    print(f'Found {len(hostnames)} unique hostnames. Validating hostnames. This may take a long time')
    delegated_details = []
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(get_data_asynchronous(conf_settings_workers, delegated_details))
    loop.run_until_complete(future)

    # Check again for and remove duplicates
    delegated_details = import_hostnames.unique_list(delegated_details)

    # Save to database
    print('Inserting data into SQLite3 database')
    process_data.write_delegated(db_file_path, delegated_details)

    # Clean up duplicates
    print('Cleaning up duplicates')
    process_data.purge_db_duplicates(db_file_path)
