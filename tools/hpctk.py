from io import StringIO
from pathlib import Path
import os
import pandas as pd
import re
import shutil
import subprocess
import yaml

###############################################################################
# states

STATE_WORK="🚧"
STATE_DONE="✅"
STATE_FAIL="🤢"
STATE_WARN="🚨"
STATE_INFO="✋"

###############################################################################
# runner

def run(cmd, stdout=True):
    """
    Run a command locally.

    Args:
    - cmd: Command as a [] list with all separated args
    - stdout: Print stdout by default (True)
    """
    result = subprocess.run(cmd, capture_output=True, text=True, cwd="../")
    if (result.returncode != 0):
        raise subprocess.CalledProcessError(result.returncode, cmd, output=result.stdout, stderr=result.stderr)
    else:
        print(result.stdout) if stdout == True else None
        
    return result

def run_remote(cmd, host, ssh, stdout=True):
    """
    Run a command remotely.

    Args:
    - cmd: Command as a [] list with all separated args
    - host: IP or hostname
    - ssh: SSH creds dict
    - stdout: Print stdout by default (True)
    """
    new_cmd = ["ssh", f"{ssh['user']}@{host}", "-p", f"{ssh['port']}", "-i", f"{ssh['ssh_path']}/{ssh['ssh_key_name']}"] + cmd
    result = subprocess.run(new_cmd, capture_output=True, text=True)
    if (result.returncode != 0):
        raise subprocess.CalledProcessError(result.returncode, cmd, output=result.stdout, stderr=result.stderr)
    else:
        print(result.stdout) if stdout == True else None
        
    return result

def get_ssh_server_pubkey(host, ssh, stdout=True):
    """
    Get a SSH public key from a server.

    Args:
    - host: IP or Hostname
    - ssh: SSH creds dict
    - stdout: Print stdout by default (True)
    """
    cmd = ["ssh-keyscan", "-p", f"{ssh['port']}", "-t", "ecdsa", host]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if (result.returncode != 0):
        raise subprocess.CalledProcessError(result.returncode, cmd, output=result.stdout, stderr=result.stderr)
    else:
        print(result.stdout) if stdout == True else None
        
    return result.stdout

def is_ip_address(hostname):
    """
    Check if the given hostname is an IP address.
    
    Args:
    - hostname: The hostname or IP address to check.
    
    Returns:
    - True if the hostname is an IP address, False otherwise.
    """
    return hostname.startswith("[") and ":" in hostname

def extract_ip_or_hostname(hostname):
    """
    Extract the IP address or hostname without brackets and port number.
    
    Args:
    - hostname: The hostname or IP address to extract from.
    
    Returns:
    - The extracted IP address or hostname.
    """
    # Get the first part of the server pubkey line
    hostname = hostname.split(' ')[0]

    # Remove brackets and port number from the hostname if it's in the format [192.168.2.1]:22
    if hostname.startswith("["):
        return hostname.split(':')[0][1:-1]  # Remove port number if exists
    else:
        return hostname.split(':')[0]  # Remove port number if exists

def add_host_key_to_known_hosts(pubkey, ssh):
    """
    Add the host verification key to the known_hosts file if it doesn't already exist.
    
    Args:
    - public_key_line: A line containing the server public key (e.g., obtained from ssh-keyscan).
    - ssh: SSH creds dict
    """
    try:
        # Extract hostname from the public key line
        parts = pubkey.split()
        hostname = parts[0]

        # Extract IP address or hostname without brackets and port number
        hostname = extract_ip_or_hostname(hostname)

        print(f"{STATE_WORK} Check server public key {hostname}")

        # Run ssh-keygen to check if the host key already exists in known_hosts
        check_key_command = ["ssh-keygen", "-F", hostname]
        key_check_output = subprocess.check_output(check_key_command, stderr=subprocess.DEVNULL)

        # If the key doesn't exist, add it
        if not key_check_output.strip():
            # Decode output to string
            ssh_keyscan_output = ssh_keyscan_output.decode(pubkey)

            # Add the public key to the known_hosts file
            with open(f"{ssh['ssh_path']}/known_hosts", "a") as known_hosts_file:
                known_hosts_file.write(ssh_keyscan_output)
            
            print(f"{STATE_DONE} Host key added to known_hosts successfully.")
        else:
            print(f"{STATE_DONE} Host key already exists.")
    except subprocess.CalledProcessError as e:
        print(f"{STATE_FAIL} Error: Failed to add host key to known_hosts.")
        print(e)

###############################################################################
# printer

def print_hpc_setup_yaml(lab, user, container_name, container_tag, docker_file, registry_host, hpc_mn, ssh_creds, workspace_dir, hpc_mn_project_base):
    # Creating a DataFrame
    data = {
        "Fact": ["lab", "user", "container_name", "container_tag", "docker_file", "registry_host", "hpc_mn", "ssh_creds", "workspace_dir", "hpc_mn_project_base"],
        "Value": [lab, user, container_name, container_tag, docker_file, registry_host, hpc_mn, ssh_creds, workspace_dir, hpc_mn_project_base]
    }

    df = pd.DataFrame(data)

    # Styling the DataFrame
    styled_df = df.style.set_properties(**{
        'background-color': '#f4f4f4',
        'color': 'black',
        'border-color': 'black',
        'border-style': 'solid',
        'border-width': '1px',
        'text-align': 'left'
        ''
    }).set_table_styles([{
        'selector': 'th',
        'props': [('background-color', '#404040'), ('color', 'white'), ('border-color', 'black'), ('border-style', 'solid'), ('border-width', '1px')]
    }]).hide()

    # Display the DataFrame in a Jupyter Notebook
    from IPython.display import display
    display(styled_df)

def print_ssh_public_key(ssh_file_path):
    # Construct the path to the public key file
    public_key_path = ssh_file_path + ".pub"

    try:
        # Open the public key file for reading
        with open(public_key_path, "r") as public_key_file:
            # Read the content of the public key file
            public_key_content = public_key_file.read()
            # Print the content of the public key
            print(f"{STATE_INFO} This is your SSH public key:\n")
            print(public_key_content)
    except FileNotFoundError:
        print(f"{STATE_FAIL} Public key file '{public_key_path}' not found.")

###############################################################################
# conversion

def time_to_minutes(time_str):
    parts = list(map(int, time_str.split(':')))
    if len(parts) == 2:  # HH:MM
        hh, mm = parts
        return hh * 60 + mm
    elif len(parts) == 3:  # HH:MM:SS
        hh, mm, ss = parts
        return hh * 60 + mm + ss / 60
    return 0

def minutes_to_time(minutes):
    hh = int(minutes // 60)
    mm = int(minutes % 60)
    return f'{hh:02d}:{mm:02d}'

###############################################################################
# tabular highlighter

def highlight_tags(s):
    color = 'color: white; background-color: green' if s == 'latest' else 'color: black; background-color: yellow'
    return color

def highlight_state(s):
    color = 'color: white; '
    color += 'background-color: green' if s == 'idle' else 'background-color: red'
    return color

def highlight_job_state(s):
    color = 'color: white; background-color: green' if s == 'R' else 'color: black; background-color: yellow'
    return color

def show_tab_styled(output, skip_lines, highlighter, columns=['STATE']):
    # Extract the relevant part of the output
    data = output.split('\n')[skip_lines:] # skip lines

    # Create a DataFrame from the string
    df = pd.read_csv(StringIO('\n'.join(data)), sep='\s+')
    styled_df = df.style.map(highlighter, subset=columns)

    # Display the DataFrame in a Jupyter Notebook
    from IPython.display import display
    display(styled_df)

def show_tab_styled_bar(output, skip_lines, highlighter, columns=['STATE']):
    # Extract the relevant part of the output
    data = output.split('\n')[skip_lines:] # skip lines

    # Create a DataFrame from the string
    df = pd.read_csv(StringIO('\n'.join(data)), sep='\s+')

    # Apply the conversion to the TIME column
    df['TIME'] = df['TIME'].apply(time_to_minutes)

    styled_df = df.style.map(highlighter, subset=columns)

    # Apply bar styling to the 'TIME' column
    styled_df = styled_df.bar(subset=['TIME'], color='#d65f5f')

    # Display the DataFrame in a Jupyter Notebook
    from IPython.display import display
    display(styled_df)

# def show_tab_styled_bar_horizontal(output, skip_lines, highlighter, columns=['STATE']):
#     # Extract the relevant part of the output
#     data = output.split('\n')[skip_lines:] # skip lines

#     # Create a DataFrame from the string
#     df = pd.read_csv(StringIO('\n'.join(data)), sep='\s+')

#     # Apply the conversion to the TIME column
#     df['TIME'] = df['TIME'].apply(time_to_minutes)

#     # Transpose the DataFrame
#     df_transposed = df.T

#     # Apply the style to the transposed 'ST' rows
#     styled_df_transposed = df_transposed.style.map(highlighter, subset=pd.IndexSlice['ST', :])

#     # Apply bar styling to the transposed 'TIME' rows
#     styled_df_transposed = styled_df_transposed.bar(subset=pd.IndexSlice['TIME', :], color='#d65f5f')

#     # Display the styled transposed DataFrame in a Jupyter Notebook
#     from IPython.display import display
#     display(styled_df_transposed)

###############################################################################
# Input helper

class YAML_configurator:
    def __init__(self, file):
        self.file = file

    def check_file_existence(self):
        if os.path.exists(self.file):
            filename, extension = os.path.splitext(self.file)
            new_file = filename + ".org" + extension
            print(f"{STATE_WARN} Warning: File '{self.file}'  overwritten")
            return new_file, True
        else:
            return self.file, False

    def save_to_yaml(self, data):
        with open(self.file, 'w') as yaml_file:
            yaml.dump(data, yaml_file, default_flow_style=False)

    def read_yaml(self):
        with open(self.file, 'r') as yaml_file:
            data = yaml.safe_load(yaml_file)
        return data

    def get_yaml_input(self, default_data=None):
        raise NotImplementedError("Subclass must implement abstract method")


class YAML_hpc_creds_configurator(YAML_configurator):
    def get_yaml_input(self, default_data=None):
        data = default_data if default_data else {
            "container_tag": "latest",
            "docker_file": "Dockerfile",
            "registry_host": "127.0.0.5000",
            "hpc_mn": "127.0.0.1",
            "ssh_creds": {
                "ssh_path": "~/.ssh",
                "ssh_key_name": "hpc",
                "ssh_port": "22"
            }
        }

        data['lab']                 = input(f"Your laboratory (default: {data.get('lab')}): ") or data.get('lab')
        data['user']                = input(f"Your HPC user name (default: {data.get('user')}): ") or data.get('user')
        data['container_name']      = input(f"Docker container name (default: {data.get('container_name')}): ") or data.get('container_name')
        data['container_tag']       = input(f"Docker container tag (default: {data.get('container_tag')}): ") or data.get('container_tag')
        data['workspace_dir']       = input(f"Workspace dir (default: {data.get('workspace_dir')}): ") or data.get('workspace_dir')
        data['hpc_mn_project_base'] = input(f"Project directory on HPC management host (default: {data.get('hpc_mn_project_base')}): ") or data.get('hpc_mn_project_base')
        data['docker_file']         = input(f"Dockerfile to use for builds (default: {data.get('docker_file')}): ") or data.get('docker_file')
        data['registry_host']       = input(f"Docker registry host:port (default: {data.get('registry_host')}): ") or data.get('registry_host')
        data['hpc_mn']              = input(f"HPC management host (default: {data.get('hpc_mn')}): ") or data.get('hpc_mn')
        ssh_user                    = input(f"SSH user name (default: {data.get('ssh_creds').get('user')}): ") or data.get('ssh_creds').get('user')
        ssh_path                    = input(f"SSH keys directory (default: {data.get('ssh_creds').get('ssh_path')}): ") or data.get('ssh_creds').get('ssh_path')
        ssh_key_name                = input(f"SSH key file name (default: {data.get('ssh_creds').get('ssh_key_name')}): ") or data.get('ssh_creds').get('ssh_key_name')
        ssh_port                    = input(f"SSH port (default: {data.get('ssh_creds').get('port')}): ") or data.get('ssh_creds').get('port')

        data['ssh_creds'] = {'user': ssh_user, 'ssh_path': ssh_path, 'ssh_key_name': ssh_key_name, 'port': ssh_port}

        return data

class YAML_hpc_sbatch_configurator(YAML_configurator):
    def get_yaml_input(self, default_data=None):
        data = default_data if default_data else {
            "hpc_partition": "",                # name of the HPC partition
            "hpc_nodes": 1,                     # number of HPC nodes to use
            'job': {
                'name': 'repropy',              # name of your HPC job
                'stdout': 'job.out',            # where stdout is written
                'stderr': 'job.err',            # where stderr is written
                'memory': '6G',                 # how much memory to use for each process
                'threads_per_core': 2,          # 1 - no hyperthreading, 2 - hyperthreading
                'array': {
                            'start': 0,         # start of the job array
                            'end': 285,         # end of the job array
                            'limit': 16         # limit of concurrent running jobs
                        },         
                'time': {
                            'activate': True,   # use time limit
                            'limit': '01:00:00' # time limit in HH:MM:ss
                        },
            }
        }
    
        data['hpc_partition'] = input(f"Name of the HPC partition (default: {data.get('hpc_partition')}): ") or data.get('hpc_partition')
        data['hpc_nodes']     = input(f"Number of HPC nodes to use (default: {data.get('hpc_nodes')}): ") or data.get('hpc_nodes')

        job = data.get('job')

        job_name              = input(f"Name of your HPC job (default: {job.get('name')}): ") or data.get('job').get('name')
        job_stdout            = input(f"Where stdout is written (default: {job.get('stdout')}): ") or job.get('stdout')
        job_stderr            = input(f"Where stderr is written (default: {job.get('stderr')}): ") or job.get('stderr')
        job_memory            = input(f"How much memory to use for each process (default: {job.get('memory')}): ") or job.get('memory')
        job_threads_per_core  = input(f"1 - no hyperthreading, 2 - hyperthreading (default: {job.get('threads_per_core')}): ") or job.get('threads_per_core')

        array  = job.get['array']

        array['start']           = input(f"Start of the job array (default: {array.get('start')}): ") or array.get('start')
        array['end']             = input(f"End of the job array (default: {array.get('end')}): ") or array.get('end')
        array['limit']           = input(f"Limit of concurrent running jobs (default: {array.get('limit')}): ") or array.get('limit')

        time = job.get['time']

        time['activate']         = input(f"Use time limit (default: {time.get('activate')}): ") or time.get('activate')
        time['limit']            = input(f"Time limit in HH:MM:ss (default: {time.get('limit')}): ") or time.get('limit')

        # time        = {'activate': time_limit_activate, 'limit': time_limit}
        # array       = {'start': array_start, 'end': array_end, 'limit': array_limit}  
        # data['job'] = {'name': job_name, 'stdout': job_stdout, 'stderr': job_stderr, 'memory': job_memory, 'threads_pe_core': job_threads_per_core, 'array': array, 'time': time}

        return data

class SSHConfigurator:
    def get_ssh_input(self):
        data = {}
        data['ssh_path'] = input("Where do you store your SSH keys (default: ~/.ssh): ") or "~/.ssh"
        data['ssh_key_file'] = input("Your SSH key file name (default: hpc): ") or "~/hpc"
        data["ssh_user"] = input("Your HPC user name: ")
        return data

###############################################################################
# Generators

def get_last_directory_name(path):
    path_obj = Path(path)
    # Get the name of the last directory
    last_dir = path_obj.name if path_obj.is_dir() else path_obj.parent.name
    return last_dir

def gen_ssh_key(ssh_creds):
    ssh_file_path = os.path.expanduser(ssh_creds["ssh_path"] + "/" + ssh_creds["ssh_key_name"])
    ssh_user_name = ssh_creds["user"]

    if os.path.exists(ssh_file_path):
        shutil.move(ssh_file_path, ssh_file_path + ".org")
        shutil.move(ssh_file_path + ".pub", ssh_file_path + ".pub.org")
        print(f"{STATE_WARN} Warning: SSH key '{ssh_file_path}' already exists. Saving as .org backup.\n")

    run(["ssh-keygen", "-t", "ecdsa", "-b", "521", "-N", "", "-C", f"{ssh_user_name}", "-f", ssh_file_path])

    print_ssh_public_key(ssh_file_path)

