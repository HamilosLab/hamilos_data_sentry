"""
Checks for logs both locally and on server.
If both present, merge.
Regardless, confirm that logs are up to date (that is, all files are present).
Ask user if they would like to validate logs, or just sync from server.
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
from datetime import datetime
from pprint import pformat 


# Load path to the blech server
# script_path = os.path.realpath(__file__)
# dir_path = os.path.dirname(script_path)

# dir_path = '/media/bigdata/projects/blech_data_transfer'
# 
# this_dataset_handler = DatasetFrameHandler(dir_path)
# this_dataset_handler.get_dataset_frame()
# this_dataset_handler.sync_logs()

def get_time_pretty():
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))

class DatasetFrameLogger:
    """
    Log changes to the dataset frame
    """
    def __init__(self, server_home_dir):
        self.write_dir = server_home_dir 
        self.log_path = os.path.join(self.write_dir, 'dataset_frame_log.txt')
        print(f"Logging to: {self.log_path}")
        self.current_user = os.getlogin()
        self.current_computer = os.uname().nodename
        print(f"Current user: {self.current_user}")
        print(f"Current computer: {self.current_computer}")

    def log(self, msg):
        with open(self.log_path, 'a') as self.log_cxn:
            write_str = f"{get_time_pretty()} - {self.current_user}@{self.current_computer}: {msg}\n\n"
            self.log_cxn.write(write_str)
            print(write_str)

class DatasetFrameHandler:

    def __init__(self, dir_path): 
        self.dir_path = dir_path
        self.server_path_file = os.path.join(dir_path, 'local_only_files','blech_server_path.txt')
        self.get_server_path()
        self.check_server_write_access(self.server_home_dir)
        self.logger = DatasetFrameLogger(self.server_home_dir)

    def get_server_path(self):
        # Get server path
        if not os.path.exists(self.server_path_file):
            print(f"Server path file not found: {server_path_file}")
            print("I don't know how to figure out the server path.")
            print("Exiting...")
            sys.exit()
        else:
            with open(self.server_path_file, 'r') as f:
                self.server_path = f.readline().strip()
            if not os.path.exists(self.server_path):
                print(f"Server path not found: {self.server_path}")
                print("Exiting...")
                sys.exit()
            else:
                print(f"Server path found: {self.server_path}")
                print("Continuing...")
                print("")

            self.server_home_dir = os.path.join(self.server_path, 'data_management')
            if not os.path.exists(self.server_home_dir):
                os.mkdir(self.server_home_dir)

    def check_server_write_access(self, copy_dir):
        # Check that selected subfolder is writable
        write_bool = os.access(copy_dir, os.W_OK)
        if not write_bool:
            print(f"Server path is not writable: {copy_dir}")
            self.write_bool = False
        else:
            print(f"Server path is writable: {copy_dir}")
            print("Continuing...")
            print("")
            self.write_bool = True

    def check_dataset_frame(self):
        dataset_frame_path_list = [
                os.path.join(self.server_home_dir, 'dataset_frame.csv'),
                os.path.join(self.dir_path, 'dataset_frame.csv')
                ]

        dataset_frame_path_exists = [os.path.exists(f) for f in dataset_frame_path_list]
        if any(dataset_frame_path_exists):
            self.sync_logs()
            self.dataset_frame_path = dataset_frame_path_list[1]
        # if all(dataset_frame_path_exists):
        #     # # Check which dataset frame is more recent
        #     # log_times = [os.path.getmtime(f) for f in dataset_frame_path]
        #     # # Convert to datetime
        #     # log_times = [time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(t)) for t in log_times]
        #     # # Ask user which log to use
        #     # print(f"Found multiple dataset frames:")
        #     # for i, f in enumerate(dataset_frame_path):
        #     #     print(f"{i}: {f} ({log_times[i]})")
        #     # log_choice = input("Which log should I use (0/1)? ")
        #     # while not log_choice.isdigit() or int(log_choice) not in [0, 1]:
        #     #     print(f"Invalid selection: {log_choice}")
        #     #     log_choice = input("Which log should I use (0/1)? ")
        #     # self.dataset_frame_path = dataset_frame_path[int(log_choice)]
        # elif any(dataset_frame_path_exists):
        #     self.dataset_frame_path = dataset_frame_path[dataset_frame_path_exists.index(True)]

        # If doesn't exist, ask user if they want to create a new dataset frame
        while not any(dataset_frame_path_exists):
            dataset_frame_path_str = "\n=OR=\n".join(dataset_frame_path_list)
            print(f"dataset frame not found: \n{dataset_frame_path_str}")
            # Ask user if this is expected, if it is, create a new dataset frame
            # If it's not, exit
            create_log = input("Should I create a new dataset frame (y/n)? ")
            while create_log not in ['y', 'n']:
                print(f"Invalid selection: {create_log}")
                create_log = input("Should I create a new dataset frame (y/n)? ")
            if create_log == 'y':
                # Make log on server
                self.dataset_frame_path = dataset_frame_path_list[0]
                self.dataset_frame = pd.DataFrame(
                        columns=[
                            'date', 
                            'time', 
                            'user', 
                            # 'project', 
                            'email', 
                            'recording', 
                            'recording_path'
                            ]
                        )
                self.dataset_frame.to_csv(self.dataset_frame_path, index=False)
                print(f"Created new dataset frame: {self.dataset_frame_path}")
                print("Continuing...")
                print("")

                self.logger.log(f"Created new dataset frame: {self.dataset_frame_path}")
            else:
                wait = input("Should I wait (w) or exit (e)? ")
                while wait not in ['w', 'e']:
                    print(f"Invalid selection: {wait}")
                    wait = input("Should I wait (w) or exit (e)? ")
                if wait == 'w':
                    input("Press Enter to continue...")
                else:
                    print("Exiting...")
                    sys.exit()

    def sync_logs(self):
        """
        If logs are not present on both local and server, copy the one that is present.
        If present on both, merge and update both
        """
        subset_cols = ['user', 'recording', 'recording_path', 'info_file_exists']
        dataset_frame_path_list = [
                os.path.join(self.server_home_dir, 'dataset_frame.csv'),
                os.path.join(self.dir_path, 'dataset_frame.csv')
                ]
        path_exists = [os.path.exists(f) for f in dataset_frame_path_list]
        if not all(path_exists) and any(path_exists):
            dataset_frame_path = dataset_frame_path_list[path_exists.index(True)]
            dataset_frame = pd.read_csv(dataset_frame_path)
            dataset_frame = dataset_frame.drop_duplicates(
                    subset=subset_cols,
                    keep='last')
            if path_exists[0]:
                dataset_frame.to_csv(dataset_frame_path_list[1], index=False)
                self.logger.log(f"Synced dataset frame from server to local: {dataset_frame_path_list[1]}")
            else:
                dataset_frame.to_csv(dataset_frame_path_list[0], index=False)
                self.logger.log(f"Synced dataset frame from local to server: {dataset_frame_path_list[1]}")
        elif all(path_exists):
            dataset_frames = [pd.read_csv(f) for f in dataset_frame_path_list]
            subset_frames = [df[subset_cols] for df in dataset_frames]
            if not subset_frames[0].equals(subset_frames[1]):
                self.logger.log(f"Found different dataset frames on server and local")
                dataset_frame = pd.concat(dataset_frames)
                dataset_frame = dataset_frame.drop_duplicates(
                        subset=subset_cols,
                        keep='last')
                dataset_frame = dataset_frame.reset_index(drop=True)
                list_str = "\n".join(dataset_frame_path_list)
                self.logger.log(f"Merged dataset frames: \n{list_str}")
                for f in dataset_frame_path_list:
                    dataset_frame.to_csv(f, index=False)
                self.logger.log(f"Synced dataset frames: \n{list_str}") 
            else:
                # Just drop duplicates and save
                dataset_frame = dataset_frames[0]
                dataset_frame = dataset_frame.drop_duplicates(
                        subset=subset_cols,
                        keep='last')
                for f in dataset_frame_path_list:
                    dataset_frame.to_csv(f, index=False)

    def add_entry(self, entry_dict):
        """
        Add entry to dataset frame
        """
        entry_keys = ['date', 'time', 'user', 'email', 'recording', 'recording_path']
        # Check that dict has all required keys
        if not all([k in entry_dict.keys() for k in entry_keys]):
            print(f"Missing keys in entry_dict: {entry_dict.keys()}")
            print(f"Required keys: {entry_keys}")
            raise ValueError("Missing keys in entry_dict")
        else:
            dataset_frame = pd.read_csv(self.dataset_frame_path)
            dataset_frame = dataset_frame._append(entry_dict, ignore_index=True)
            dataset_frame.to_csv(self.dataset_frame_path, index=False)
            pformat_dict = pformat(entry_dict, indent=4)
            self.logger.log(f"Added entry to dataset frame: \n {pformat_dict}")
            self.sync_logs()

    def check_experiment_exists(self, data_folder):
        """
        Check if experiment has already been transferred
        """
        dataset_frame = pd.read_csv(self.dataset_frame_path)
        recording = os.path.basename(data_folder)
        if recording in dataset_frame['recording'].values:
            print("Recording already exists") 
            row = dataset_frame.loc[dataset_frame['recording'] == recording]
            print(row.T)
            return True
        else:
            return False


# ##############################
# ##############################
# # Check if dataset frame exists on server 
# 
# # Look for dataset frame in both dir_path and server_home_dir
#         
# # Copy dataset frame locally
# shutil.copy2(dataset_frame_path, dir_path)
# 
# dataset_frame = pd.read_csv(os.path.join(dir_path, 'dataset_frame.csv'))
# # Check whether the recording has already been transferred
# recording = os.path.basename(data_folder)
# if recording in dataset_frame['recording'].values:
#     print(f"Recording already transferred: {recording}")
#     print("Exiting...")
#     sys.exit()
