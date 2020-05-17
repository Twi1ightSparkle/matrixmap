## Import modules
import os
import psycopg2


## Functions

def get_hostnames_from_postgres(server, port, database, username, password, limit=None, ):
    """Get hostnames from PostgreSQL

    Try and connect to PostgreSQL database, then get hostnames from table destinations

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

    hostnames = []

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
            hostnames.append(row[0])

    # If any error, print the error and return None
    except (Exception, psycopg2.Error) as error :
        print ('Error while fetching data from PostgreSQL', error)
        return(None)
    
    # If no errors, return stuff
    else:
        if len(hostnames) < 1:
            print("Destinations table is empty")
            return(None)
        else:
            return(hostnames)

    # Close database connection
    finally:
        try:
            if(connection):
                cursor.close()
                connection.close()
        except UnboundLocalError:
            pass


def load_file(file_path):
    """Load file to list

    If supplied file exist, load it to a list. LF style new line separated

    Args:
        file_path: A fill path to a text file.
    
    Returns:
        List of all lines in the file. Or None if the file does not exist
    
    """

    # Check if the file exist
    if not os.path.isfile(file_path):
        return(None)

    # Else load the file
    f = open(file_path, 'r')
    lines = [line for line in f]
    f.close()
    return(lines)
