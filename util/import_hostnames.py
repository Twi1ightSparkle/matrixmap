## Import modules
import json
import os
import psycopg2


## Functions

def get_hostnames_from_postgres(server, port, database, username, password, limit=None, ):
    """Get hostnames from PostgreSQL

    Try and connect to PostgreSQL database, then get hostnames from table destinations.
    List stripped of shitespace before returning.

    Args:
        server: IP or fqdn for PostgreSQL server
        port: Port to talk to server on
        database: Which database to look in
        username: Username to authenticate with
        password: Password to authenticate with
        limit: Limit number of results for testing or debugging purposes. Default None

    Returns:
        List of hostnames. None if any error occurred or destinations table is empty
    """

    temp = []

    # Try and get stuff from the datbase
    try:
        connection = psycopg2.connect(user=username, password=password, host=server, port=port, database=database, connect_timeout=3)
        cursor = connection.cursor()

        if limit:
            postgre_select_query = f'SELECT destination FROM destinations LIMIT {limit}'
        else:
            postgre_select_query = 'SELECT destination FROM destinations'

        cursor.execute(postgre_select_query)
        mobile_records = cursor.fetchall() 
        
        for row in mobile_records:
            temp.append(row[0])

    # If any error, print the error and return None
    except (Exception, psycopg2.Error) as error :
        print ('Error while fetching data from PostgreSQL', error)
        cont = input('\nType yes if you would like to continue, or no to exit: ')
        if cont.lower() == 'yes':
            return(None)
        exit(0)
    
    # If no errors, return stuff
    else:
        if len(temp) < 1:
            print("Destinations table is empty")
            return(None)
        else:
            hostnames = []
            for x in temp:
                hostnames.append(x.strip())
            return(hostnames)

    # Close database connection
    finally:
        try:
            if(connection):
                cursor.close()
                connection.close()
        except UnboundLocalError:
            pass



def load_hostnames_file(file_path):
    """Load file to list

    If supplied file exist, load it to a list. LF style new line separated. List stripped of whitespace before returning.

    Args:
        file_path: Full path to a text file.
    
    Returns:
        List of all lines in the file. Or None if the file does not exist.
    
    """

    # Check if the file exist
    if not os.path.isfile(file_path):
        return(None)

    # Else load the file
    f = open(file_path, 'r')
    temp = [line for line in f]
    f.close()

    lines = []
    for x in temp:
        lines.append(x.strip())
    return(lines)


def load_shodan_file(file_path):
    """Load Shodan export file

    If supplied Shodan export file file exist, load IP addresses from it to a list.

    Args:
        file_path: Full path to a Shodan data export json file.
    
    Returns:
        All IP addresses from said file. Or None if file does not exist.
    """

    # Check if the file exist
    if not os.path.isfile(file_path):
        return(None)
    
    # Else load the file
    f = open(file_path, 'r')
    temp = [line for line in f]
    f.close()

    # Extract IPs
    lines = []
    for line in temp:
        data = json.loads(line)
        if data['transport'] == 'tcp':
            lines.append(str(data['ip_str']).strip())
    
    return(lines)


def file_len(f_name):
    """Count lines in a file

    Args:
        f_name: Full path to a text file
    
    Returns:
        An integer
    """

    with open(f_name) as f:
        for i, l in enumerate(f):
            l = l
            pass
    return i + 1


def unique_list(l):
    """Remove duplicated from a list

    Args:
        l: A list
    
    Returns:
        The input list minus any duplicates
    """

    return(list(dict.fromkeys(l)))
