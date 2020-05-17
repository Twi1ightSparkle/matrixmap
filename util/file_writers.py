## Import modules
import os


## Functions

def write_matrix_servers(out_file_path, line):
    """Generate matrix_servers.js

    Args:
        out_file_path: Full file path to matrix_servers.js
        line: A line to add to the file
    """

    out_file = open(out_file_path, 'w+')

    # Write headers
    if not os.path.isfile(out_file_path):
        out_file.write('var addressPoints = [\n')

    out_file.write(line)

    out_file.close()
