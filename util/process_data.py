## Import modules
import os
import sqlite3

## Import other python files
from . import resolve_hostname


## Functions

def write_matrix_servers(db_file_path, line):
    """Generate matrix_servers.js

    Args:
        db_file_path: Full file path to matrix_servers.js.
        line: A line to add to the file.
    """

    out_file = open(db_file_path, 'w+')

    # Write headers
    if not os.path.isfile(db_file_path):
        out_file.write('var addressPoints = [\n')

    out_file.write(line)
    out_file.close()


def initialize_database(db_file_path):
    """Initialize SQLite database

    Initialize SQLite3 database if needed

    Args:
        db_file_path: Full path to SQLite3 database file.
    """

    try:
        conn = sqlite3.connect(db_file_path)
        cur = conn.cursor()
    except sqlite3.OperationalError as error:
        print('Error initializing database:', error)
        exit(1)
    else:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS delegated_data (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                hostname            TEXT,
                delegated_hostname  TEXT,
                delegated_ip        TEXT,
                delegated_port      INTEGER,
                server_lookup_type  TEXT,
                name                TEXT,
                version             TEXT,
                valid_ssl           TEXT,
                latitude            TEXT,
                longitude           TEXT
            )
        ''')
        cur.execute(''' 
            CREATE TABLE IF NOT EXISTS public_rooms (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                host_id             INTEGER,
                canonical_alias     TEXT,
                name                TEXT,
                num_joined_members  INTEGER,
                room_id             TEXT,
                topic               TEXT,
                world_readable      TEXT,
                guest_can_join      TEXT,
                avatar_url          TEXT,
                m_federate          TEXT,
                FOREIGN KEY(host_id) REFERENCES delegated_data(id)
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS aliases (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id             INTEGER,
                alias               TEXT,
                FOREIGN KEY(room_id) REFERENCES public_rooms(id)
            )
        ''')
    finally:
        # Save and close database
        conn.commit()
        conn.close()




def write_delegated(db_file_path, data):
    """Write delegated info to sqllite

    Write delegated Matrix hostnames to a SQLite3 database

    Args:
        db_file_path: Full path to SQLite3 database file.
        data: Data to add to database
    """

    initialize_database(db_file_path)

    try:
        conn = sqlite3.connect(db_file_path)
        cur = conn.cursor()
    except sqlite3.OperationalError as error:
        print('Error initializing database:', error)
        exit(1)
    
    # Loop over data list
    for hostname in data:
        # host_list
        #   0 hostname
        #   1 delegated_hostname
        #   2 delegated_ip
        #   3 delegated port
        #   4 serer_lookup_type
        #   5 name
        #   6 version
        #   7 valid_ssl
        host_list = hostname.split(';')
        host_list[0] = str(host_list[0]).lower()

        # Check if hostname already exist. If yes; delete old record
        for row in cur.execute(f'''
            SELECT count(hostname)
            FROM delegated_data
            WHERE hostname = "{host_list[0]}"
        '''):
            count = row[0]
        
        if count > 0:
            cur.execute(f'''
                DELETE FROM delegated_data
                WHERE hostname = "{host_list[0]}"
            ''')
        
        # Insert datapoint into database
        cur.execute(f'''
            INSERT INTO delegated_data 
            (hostname, delegated_hostname, delegated_ip, delegated_port, server_lookup_type, name, version, valid_ssl)
            VALUES (
                "{host_list[0]}",
                "{host_list[1]}",
                "{host_list[2]}",
                "{host_list[3]}",
                "{host_list[4]}",
                "{host_list[5]}",
                "{host_list[6]}",
                "{host_list[7]}"
            )
        ''')

    # Save and close database
    conn.commit()
    conn.close()


def purge_db_duplicates(db_file_path):
    """Remove duplicated from database
    
    - Get all IP addresses from database where server_lookup_type = ip
    - If the IP exist again for a host with server_lookup_type not = ip then
        - delete the address with server_lookup_type = ip
    
    Args:
        db_file_path: Full path to SQLite3 database file.
    """

    # Connect to database
    try:
        conn = sqlite3.connect(db_file_path)
        cur = conn.cursor()
    except sqlite3.OperationalError as error:
        print('Error initializing database:', error)
        exit(1)
    
    # Get all where server_lookup_type = ip
    ip_only = []
    for row in cur.execute('''
        SELECT delegated_ip FROM delegated_data
        WHERE server_lookup_type = "ip"
    '''):
        ip_only.append(row[0])

    for ip in ip_only:
        cur.execute(f'''
            DELETE FROM delegated_data
            where server_lookup_type = "ip"
            AND hostname in (
                SELECT delegated_ip FROM delegated_data
                WHERE delegated_ip = "{ip}"
                AND server_lookup_type != "ip"
            )
        ''')
    
    # Save and close database
    conn.commit()
    conn.close()


def get_public_rooms(db_file_path):
    """Get public rooms

    Get public rooms for all hosts in database

    Args:
        db_file_path: Full path to SQLite3 database file.
    """

    # Connect to database
    try:
        conn = sqlite3.connect(db_file_path)
        cur = conn.cursor()
        cur2 = conn.cursor()
    except sqlite3.OperationalError as error:
        print('Error initializing database:', error)
        exit(1)
    
    # Loop over hostnames
    for host in cur.execute('''
        SELECT id, delegated_hostname, delegated_port FROM delegated_data
        /*WHERE id NOT IN (
            SELECT host_id FROM public_rooms
        )
    '''):
        # Get all rooms from server
        rooms = resolve_hostname.https_download(host[1], '/_matrix/client/r0/publicRooms', host[2], True)

        # If rooms is not Null
        if rooms:
            #If chunk exists
            if 'chunk' in rooms:
                # Loop over the rooms and save to db
                for room in rooms['chunk']:
                    # Set all variables to empty
                    canonical_alias = None
                    name = None
                    num_joined_members = None
                    room_id = None
                    topic = None
                    world_readable = None
                    guest_can_join = None
                    avatar_url = None
                    m_federate = None

                    # # Set variables if they exists, otherwise leave as None
                    if 'canonical_alias' in room:
                        canonical_alias = str(room['canonical_alias'])
                    if 'name' in room:
                        name = str(room['name']).replace('"', '')
                    if 'num_joined_members' in room:
                        num_joined_members = int(room['num_joined_members'])
                    if 'room_id' in room:
                        room_id = str(room['room_id'])
                    if 'topic' in room:
                        topic = str(room['topic']).replace('"', '')
                    if 'world_readable' in room:
                        world_readable = str(room['world_readable'])
                    if 'guest_can_join' in room:
                        guest_can_join = str(room['guest_can_join'])
                    if 'avatar_url' in room:
                        avatar_url = str(room['avatar_url'])
                    if 'm.federate' in room:
                        m_federate = str(room['m.federate'])

                    # Insert room into public_rooms table
                    try:
                        cur2.execute(f'''
                            INSERT INTO public_rooms
                            (host_id, canonical_alias, name, num_joined_members, room_id, topic, world_readable, guest_can_join, avatar_url, m_federate)
                            VALUES (
                                "{host[0]}",
                                "{canonical_alias}",
                                "{name}",
                                "{num_joined_members}",
                                "{room_id}",
                                "{topic}",
                                "{world_readable}",
                                "{guest_can_join}",
                                "{avatar_url}",
                                "{m_federate}"
                            )
                        ''')
                    except sqlite3.OperationalError as e:
                        print('a', e)

                    # Get the key id of this room
                    try:
                        for row in cur2.execute(f'''
                            SELECT id from public_rooms
                            WHERE room_id = "{room_id}"
                            ORDER BY id DESC
                            LIMIT 1
                        '''):
                            room_key_id = row[0]
                    except Exception as e:
                        print(e)

                    # If aliases, loop over them and insert into aliases table
                    if 'aliases' in room:
                        for alias in room['aliases']:
                            try:
                                cur2.execute(f'''
                                    INSERT INTO aliases
                                    (room_id, alias)
                                    VALUES (
                                        "{room_key_id}",
                                        "{alias}"
                                    )
                                ''')
                            except Exception as e:
                                print('b', e)

    # Save and close database
    conn.commit()
    conn.close()