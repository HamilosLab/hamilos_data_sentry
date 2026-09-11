"""
- Only use user list from the server
- Cache manual selections for user convenience

- Recording log will contain:
    1) Date
    2) Time
    3) User
    4) Project name
    5) User email
    6) Recording name
    7) Recording path
"""

import easygui
import os
import argparse
import shutil
import sys
import time
from glob import glob
import pandas as pd
from tqdm import tqdm
import numpy as np
from archive.src import dataset_handler


# Load path to the blech server
script_path = os.path.realpath(__file__)
dir_path = os.path.dirname(script_path)
# dir_path = '/media/bigdata/projects/blech_data_transfer'

##############################
##############################

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Transfer data from the blech server to the local machine.')
    parser.add_argument('data_folder', type=str, help='Path to local data folder.',
                        default=None)
    return parser.parse_args()

# Get path to the data folder
args = parse_arguments()

def get_data_folder(args):
    """Get the data folder path from arguments or GUI selection."""
    if args.data_folder is None:
        data_folder = easygui.diropenbox(title='Select data folder', 
                                         default=os.path.expanduser('~/Desktop'))
    else:
        data_folder = args.data_folder

    if data_folder and data_folder[-1] == '/':
        data_folder = data_folder[:-1]
    
    return data_folder

data_folder = get_data_folder(args)

# data_folder = '/media/bigdata/Abuzar_Data/ORX15_spont_230529_095725'

# from importlib import reload
# reload(dataset_handler)
def initialize_dataset_handler(dir_path):
    """Initialize the dataset handler and check the dataset frame."""
    handler = dataset_handler.DatasetFrameHandler(dir_path)
    handler.check_dataset_frame()
    handler.sync_logs()
    return handler

def check_experiment_existence(handler, data_folder):
    """Check if the experiment already exists on the server."""
    exp_exists = handler.check_experiment_exists(data_folder)
    if exp_exists: 
        print(f"Experiment already exists on the server: {data_folder}")
        continue_bool = input("Would you like to continue (y/n)? ")
        while continue_bool not in ['y', 'n']:
            print(f"Invalid selection: {continue_bool}")
            continue_bool = input("Would you like to continue (y/n)? ")
        if continue_bool == 'n':
            print("Exiting...")
            sys.exit()

# Check that experiment is not already on the server
this_dataset_handler = initialize_dataset_handler(dir_path)
check_experiment_existence(this_dataset_handler, data_folder)

def validate_data_folder(data_folder):
    """Validate that the data folder exists."""
    if not os.path.exists(data_folder):
        print(f"Data folder not found: {data_folder}")
        print("Exiting...")
        sys.exit()
    else:
        print(f"Processing data folder: {data_folder}")
        print("")

validate_data_folder(data_folder)


##############################
##############################

def check_info_file(data_folder):
    """Check if an .info file exists in the data folder."""
    info_file = glob(os.path.join(data_folder, '*.info'))
    while len(info_file) == 0:
        info_file = glob(os.path.join(data_folder, '*.info'))
        print("""
    No ".info" file found in the data folder.
    Run blech_exp_info.py to create an ".info" file.
          """)
        exit_code = input("Should I wait (w) or exit (e)? ")
        while exit_code not in ['w', 'e']:
            print(f"Invalid selection: {exit_code}")
            exit_code = input("Should I wait (w) or exit (e)? ")
        if exit_code == 'w':
            input("Press Enter to continue...")
        else:
            print("Exiting...")
            sys.exit()
    else:
        info_file = info_file[0]
        print(f"Found .info file: {info_file}")
        print("Continuing...")
        print("")
    return info_file

info_file = check_info_file(data_folder)

##############################
##############################

server_path = this_dataset_handler.server_path

# server_path_file = os.path.join(dir_path, 'blech_server_path.txt')
# 
# # Get server path
# if not os.path.exists(server_path_file):
#     print(f"Server path file not found: {server_path_file}")
#     print("I don't know how to figure out the server path.")
#     print("Exiting...")
#     sys.exit()
# else:
#     with open(server_path_file, 'r') as f:
#         server_path = f.readline().strip()
#     if not os.path.exists(server_path):
#         print(f"Server path not found: {server_path}")
#         print("Exiting...")
#         sys.exit()
#     else:
#         print(f"Server path found: {server_path}")
#         print("Continuing...")
#         print("")

##############################
##############################
# Check if users list exists on the server
# If it does, copy it locally 

# Get list of users on the blech server or from dir_path
server_home_dir = this_dataset_handler.server_home_dir
users_list_path = os.path.join(server_home_dir, 'users_list.txt')
if not os.path.exists(users_list_path):
    print(f"Users list not found: {users_list_path}")
    print("Exiting...")
    sys.exit()
else:
    users_list = pd.read_csv(users_list_path, header=0)
    print(f"Users list found: {users_list_path}")
    print("Continuing...")
    print("")

def select_user(users_list, server_path):
    """Select a user from the list and get their path."""
    user_inds = list(np.arange(len(users_list))+1)
    user_select_str = "\n".join(f"{i}: {users_list.iloc[i-1]['Username']}" for i in user_inds)
    msg = f"Select a user from the list:\n{user_select_str}\n:::"
    # Don't exit if user doesn't select a user
    user_ind = input(msg)

    while not user_ind.isdigit() or int(user_ind) not in user_inds:
        print(f"Invalid selection: {user_ind}")
        user_ind = input(msg)

    # Get subfolders for the selected user
    user = users_list.iloc[int(user_ind)-1]['Username']
    print(f"Selected user: {user}")
    user_path = users_list.loc[
            users_list['Username'] == user, 'Directory'].values[0]
    user_path = os.path.join(server_path, user_path)
    
    return user, user_path

user, user_path = select_user(users_list, server_path)

def select_subfolder(user_path):
    """Select a subfolder or create a new one."""
    subdirs = sorted([d for d in os.listdir(user_path) if os.path.isdir(os.path.join(user_path, d))])
    subdir_inds = list(np.arange(len(subdirs))+1)
    subdir_select_str = "\n".join(f"{i}: {subdirs[i-1]}" for i in subdir_inds)
    # Add -1 : Create new subfolder option
    subdir_select_str = f"\n-1: Create new subfolder" + '\n\n' + subdir_select_str
    msg = f"Select a subfolder from the list:\n{subdir_select_str}\n:::"
    copy_dir = input(msg)

    while not copy_dir.isdigit() or (int(copy_dir) not in subdir_inds and int(copy_dir) != -1):
        print(f"Invalid selection: {copy_dir}")
        copy_dir = input(msg)

    if int(copy_dir) == -1:
        print("Creating new subfolder...")
        new_subdir = input("Enter new subfolder name: ")
        copy_dir = os.path.join(user_path, new_subdir)
        if not os.path.exists(copy_dir):
            os.makedirs(copy_dir)
            print(f"Creating new subfolder: {os.path.join(copy_dir)}")
        else:
            print(f"Subfolder already exists: {copy_dir}")
            print("Continuing...")
            print("")
    else:
        print(f"Selected subfolder: {subdirs[int(copy_dir)-1]}")
        copy_dir = os.path.join(user_path, subdirs[int(copy_dir)-1])
    
    return copy_dir

copy_dir = select_subfolder(user_path)



##############################
##############################


# Begin transfer process
print("Beginning data transfer...")
print("")

def prepare_file_transfer(data_folder, copy_dir):
    """Prepare file lists and create server data folder."""
    # Get list of files to transfer
    file_list = glob(os.path.join(data_folder, '**', '*'), recursive=True)
    file_list = sorted(file_list)
    dir_list = [f for f in file_list if os.path.isdir(f)]
    file_list = [f for f in file_list if os.path.isfile(f)]
    rel_file_list = [os.path.relpath(f, data_folder) for f in file_list]

    # Create data folder on the server
    server_data_folder = os.path.join(copy_dir, os.path.basename(data_folder))
    if not os.path.exists(server_data_folder):
        os.makedirs(server_data_folder)
        print(f"Created server data folder: {server_data_folder}")
        print("Continuing...")
        print("")
    else:
        print(f"Server data folder already exists: {server_data_folder}")
        print("Continuing...")
        print("")
    
    return dir_list, file_list, rel_file_list, server_data_folder

dir_list, file_list, rel_file_list, server_data_folder = prepare_file_transfer(data_folder, copy_dir)

def transfer_data(data_folder, server_data_folder, dir_list, rel_file_list):
    """Transfer data from local folder to server."""
    # Create directories on the server
    pbar = tqdm(dir_list)
    for d in pbar:
        rel_dir = os.path.relpath(d, data_folder)
        pbar.set_description(f"Creating {rel_dir}")
        server_dir = os.path.join(server_data_folder, rel_dir)
        if not os.path.exists(server_dir):
            os.makedirs(server_dir)
        else:
            print(f"Directory already exists on the server: {server_dir}")
            print("")

    # Copy files to the server
    pbar = tqdm(rel_file_list)
    for file in pbar:
        pbar.set_description(f"Copying {file}")
        src_path = os.path.join(data_folder, file)
        dst_path = os.path.join(server_data_folder, file)
        if not os.path.exists(dst_path): 
            shutil.copy2(src_path, dst_path)
        else:
            print(f"File already exists on the server: {file}")
            print("")
    print("Data transfer complete.")
    print("")

transfer_data(data_folder, server_data_folder, dir_list, rel_file_list)

##############################
##############################

def add_log_entry(dataset_handler, users_list, user, data_folder, server_data_folder):
    """Add an entry to the recording log."""
    email = users_list.loc[
            users_list['Username'] == user, 'Email'].values[0]
    entry_keys = [
            'date', 
            'time', 
            'user', 
            'email', 
            'recording', 
            'recording_path', 
            'info_file_exists'
            ]
    entry_dict = dict(
            zip(
                entry_keys,
                [time.strftime('%Y-%m-%d'),
                 time.strftime('%H:%M:%S'),
                 user,
                 email,
                 os.path.basename(data_folder),
                 server_data_folder,
                 True
                 ]
                )
            )

    dataset_handler.add_entry(entry_dict)

add_log_entry(this_dataset_handler, users_list, user, data_folder, server_data_folder)

# Copy recording log back to server
# shutil.copy2('recording_log.csv', server_home_dir)
# print("Recording log updated.")
# print("")

##############################
##############################

print("Exiting...")
sys.exit()
