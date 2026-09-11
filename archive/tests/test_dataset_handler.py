import pytest
import os
import pandas as pd
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from archive.src.dataset_handler import DatasetFrameLogger, DatasetFrameHandler, get_time_pretty

class TestDatasetFrameLogger:
    def setup_method(self):
        # Create a temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        # Clean up the temporary directory
        shutil.rmtree(self.temp_dir)
        
    def test_logger_initialization(self):
        logger = DatasetFrameLogger(self.temp_dir)
        assert logger.write_dir == self.temp_dir
        assert logger.log_path == os.path.join(self.temp_dir, 'dataset_frame_log.txt')
        assert logger.current_user == os.getlogin()
        assert logger.current_computer == os.uname().nodename
        
    @patch('dataset_handler.get_time_pretty')
    def test_logger_log_method(self, mock_time):
        mock_time.return_value = "2025-04-28 12:00:00"
        logger = DatasetFrameLogger(self.temp_dir)
        logger.log("Test message")
        
        # Check if log file exists and contains the message
        assert os.path.exists(logger.log_path)
        with open(logger.log_path, 'r') as f:
            log_content = f.read()
        
        expected_content = f"2025-04-28 12:00:00 - {logger.current_user}@{logger.current_computer}: Test message\n\n"
        assert expected_content in log_content

class TestDatasetFrameHandler:
    def setup_method(self):
        # Create temporary directories for testing
        self.temp_dir = tempfile.mkdtemp()
        self.server_dir = tempfile.mkdtemp()
        self.server_home_dir = os.path.join(self.server_dir, 'data_management')
        os.makedirs(self.server_home_dir, exist_ok=True)
        
        # Create local_only_files directory and server path file
        self.local_only_dir = os.path.join(self.temp_dir, 'local_only_files')
        os.makedirs(self.local_only_dir, exist_ok=True)
        self.server_path_file = os.path.join(self.local_only_dir, 'blech_server_path.txt')
        
        # Write server path to file
        with open(self.server_path_file, 'w') as f:
            f.write(self.server_dir)
            
    def teardown_method(self):
        # Clean up temporary directories
        shutil.rmtree(self.temp_dir)
        shutil.rmtree(self.server_dir)
        
    @patch('dataset_handler.DatasetFrameLogger')
    def test_handler_initialization(self, mock_logger):
        handler = DatasetFrameHandler(self.temp_dir)
        assert handler.dir_path == self.temp_dir
        assert handler.server_path_file == self.server_path_file
        assert handler.server_path == self.server_dir
        assert handler.server_home_dir == self.server_home_dir
        
    @patch('dataset_handler.DatasetFrameLogger')
    def test_get_server_path(self, mock_logger):
        handler = DatasetFrameHandler(self.temp_dir)
        handler.get_server_path()
        assert handler.server_path == self.server_dir
        assert handler.server_home_dir == self.server_home_dir
        
    @patch('dataset_handler.DatasetFrameLogger')
    def test_check_server_write_access_writable(self, mock_logger):
        handler = DatasetFrameHandler(self.temp_dir)
        handler.check_server_write_access(self.server_home_dir)
        assert handler.write_bool is True
        
    @patch('dataset_handler.DatasetFrameLogger')
    def test_check_server_write_access_not_writable(self, mock_logger):
        # Create a directory with no write permissions
        read_only_dir = os.path.join(self.temp_dir, 'read_only')
        os.makedirs(read_only_dir, exist_ok=True)
        os.chmod(read_only_dir, 0o555)  # Read and execute only
        
        handler = DatasetFrameHandler(self.temp_dir)
        handler.check_server_write_access(read_only_dir)
        assert handler.write_bool is False
        
        # Restore permissions for cleanup
        os.chmod(read_only_dir, 0o755)
        
    @patch('dataset_handler.DatasetFrameLogger')
    @patch('builtins.input', return_value='y')
    def test_check_dataset_frame_create_new(self, mock_input, mock_logger):
        handler = DatasetFrameHandler(self.temp_dir)
        
        # Patch the sync_logs method to avoid actual syncing
        with patch.object(handler, 'sync_logs'):
            handler.check_dataset_frame()
            
        # Check if dataset frame was created
        server_df_path = os.path.join(self.server_home_dir, 'dataset_frame.csv')
        assert os.path.exists(server_df_path)
        
        # Verify the structure of the created dataset frame
        df = pd.read_csv(server_df_path)
        expected_columns = ['date', 'time', 'user', 'email', 'recording', 'recording_path']
        assert all(col in df.columns for col in expected_columns)
        
    @patch('dataset_handler.DatasetFrameLogger')
    def test_sync_logs_server_to_local(self, mock_logger):
        handler = DatasetFrameHandler(self.temp_dir)
        
        # Create a dataset frame on the server
        server_df_path = os.path.join(self.server_home_dir, 'dataset_frame.csv')
        test_data = {
            'date': ['2025-04-28'],
            'time': ['12:00:00'],
            'user': ['test_user'],
            'email': ['test@example.com'],
            'recording': ['test_recording'],
            'recording_path': ['/path/to/recording'],
            'info_file_exists': [True]
        }
        server_df = pd.DataFrame(test_data)
        server_df.to_csv(server_df_path, index=False)
        
        # Sync logs
        handler.sync_logs()
        
        # Check if local dataset frame was created
        local_df_path = os.path.join(self.temp_dir, 'dataset_frame.csv')
        assert os.path.exists(local_df_path)
        
        # Verify the content of the local dataset frame
        local_df = pd.read_csv(local_df_path)
        assert local_df.equals(server_df)
        
    @patch('dataset_handler.DatasetFrameLogger')
    def test_sync_logs_local_to_server(self, mock_logger):
        handler = DatasetFrameHandler(self.temp_dir)
        
        # Create a dataset frame locally
        local_df_path = os.path.join(self.temp_dir, 'dataset_frame.csv')
        test_data = {
            'date': ['2025-04-28'],
            'time': ['12:00:00'],
            'user': ['test_user'],
            'email': ['test@example.com'],
            'recording': ['test_recording'],
            'recording_path': ['/path/to/recording'],
            'info_file_exists': [True]
        }
        local_df = pd.DataFrame(test_data)
        local_df.to_csv(local_df_path, index=False)
        
        # Sync logs
        handler.sync_logs()
        
        # Check if server dataset frame was created
        server_df_path = os.path.join(self.server_home_dir, 'dataset_frame.csv')
        assert os.path.exists(server_df_path)
        
        # Verify the content of the server dataset frame
        server_df = pd.read_csv(server_df_path)
        assert server_df.equals(local_df)
        
    @patch('dataset_handler.DatasetFrameLogger')
    def test_sync_logs_merge(self, mock_logger):
        handler = DatasetFrameHandler(self.temp_dir)
        
        # Create different dataset frames on server and locally
        server_df_path = os.path.join(self.server_home_dir, 'dataset_frame.csv')
        server_data = {
            'date': ['2025-04-28'],
            'time': ['12:00:00'],
            'user': ['server_user'],
            'email': ['server@example.com'],
            'recording': ['server_recording'],
            'recording_path': ['/path/to/server_recording'],
            'info_file_exists': [True]
        }
        server_df = pd.DataFrame(server_data)
        server_df.to_csv(server_df_path, index=False)
        
        local_df_path = os.path.join(self.temp_dir, 'dataset_frame.csv')
        local_data = {
            'date': ['2025-04-28'],
            'time': ['13:00:00'],
            'user': ['local_user'],
            'email': ['local@example.com'],
            'recording': ['local_recording'],
            'recording_path': ['/path/to/local_recording'],
            'info_file_exists': [True]
        }
        local_df = pd.DataFrame(local_data)
        local_df.to_csv(local_df_path, index=False)
        
        # Sync logs
        handler.sync_logs()
        
        # Verify the merged content
        merged_df = pd.read_csv(server_df_path)
        assert len(merged_df) == 2
        assert 'server_recording' in merged_df['recording'].values
        assert 'local_recording' in merged_df['recording'].values
        
    @patch('dataset_handler.DatasetFrameLogger')
    def test_add_entry(self, mock_logger):
        handler = DatasetFrameHandler(self.temp_dir)
        
        # Create a dataset frame
        df_path = os.path.join(self.temp_dir, 'dataset_frame.csv')
        test_data = {
            'date': [],
            'time': [],
            'user': [],
            'email': [],
            'recording': [],
            'recording_path': []
        }
        df = pd.DataFrame(test_data)
        df.to_csv(df_path, index=False)
        
        # Set the dataset frame path
        handler.dataset_frame_path = df_path
        
        # Add an entry
        entry = {
            'date': '2025-04-28',
            'time': '12:00:00',
            'user': 'test_user',
            'email': 'test@example.com',
            'recording': 'test_recording',
            'recording_path': '/path/to/recording'
        }
        
        # Patch sync_logs to avoid actual syncing
        with patch.object(handler, 'sync_logs'):
            handler.add_entry(entry)
        
        # Verify the entry was added
        updated_df = pd.read_csv(df_path)
        assert len(updated_df) == 1
        assert updated_df.iloc[0]['recording'] == 'test_recording'
        assert updated_df.iloc[0]['user'] == 'test_user'
        
    @patch('dataset_handler.DatasetFrameLogger')
    def test_check_experiment_exists_true(self, mock_logger):
        handler = DatasetFrameHandler(self.temp_dir)
        
        # Create a dataset frame with an existing recording
        df_path = os.path.join(self.temp_dir, 'dataset_frame.csv')
        test_data = {
            'date': ['2025-04-28'],
            'time': ['12:00:00'],
            'user': ['test_user'],
            'email': ['test@example.com'],
            'recording': ['existing_recording'],
            'recording_path': ['/path/to/recording']
        }
        df = pd.DataFrame(test_data)
        df.to_csv(df_path, index=False)
        
        # Set the dataset frame path
        handler.dataset_frame_path = df_path
        
        # Check if experiment exists
        result = handler.check_experiment_exists('/path/to/existing_recording')
        assert result is True
        
    @patch('dataset_handler.DatasetFrameLogger')
    def test_check_experiment_exists_false(self, mock_logger):
        handler = DatasetFrameHandler(self.temp_dir)
        
        # Create a dataset frame without the recording we're looking for
        df_path = os.path.join(self.temp_dir, 'dataset_frame.csv')
        test_data = {
            'date': ['2025-04-28'],
            'time': ['12:00:00'],
            'user': ['test_user'],
            'email': ['test@example.com'],
            'recording': ['existing_recording'],
            'recording_path': ['/path/to/recording']
        }
        df = pd.DataFrame(test_data)
        df.to_csv(df_path, index=False)
        
        # Set the dataset frame path
        handler.dataset_frame_path = df_path
        
        # Check if experiment exists
        result = handler.check_experiment_exists('/path/to/non_existing_recording')
        assert result is False

def test_get_time_pretty():
    # This is a simple test to ensure the function returns a string in the expected format
    time_str = get_time_pretty()
    # Check if it matches the format YYYY-MM-DD HH:MM:SS
    assert len(time_str) == 19
    assert time_str[4] == '-' and time_str[7] == '-'
    assert time_str[10] == ' '
    assert time_str[13] == ':' and time_str[16] == ':'
