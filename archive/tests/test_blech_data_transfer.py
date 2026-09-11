import pytest
import os
import pandas as pd
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from io import StringIO
import sys

# Import the dataset_handler module
from archive.src.dataset_handler import DatasetFrameHandler, DatasetFrameLogger

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def mock_server_path(temp_dir):
    """Create a mock server path structure"""
    # Create local_only_files directory with server path file
    local_only_dir = os.path.join(temp_dir, 'local_only_files')
    os.makedirs(local_only_dir, exist_ok=True)
    
    # Create server path file
    server_path = os.path.join(temp_dir, 'server')
    os.makedirs(server_path, exist_ok=True)
    
    with open(os.path.join(local_only_dir, 'blech_server_path.txt'), 'w') as f:
        f.write(server_path)
    
    # Create data_management directory
    data_mgmt_dir = os.path.join(server_path, 'data_management')
    os.makedirs(data_mgmt_dir, exist_ok=True)
    
    # Create users_list.txt in data_management
    users_list_content = """Username,Directory,Email
user1,user1_dir,user1@example.com
user2,user2_dir,user2@example.com
user3,user3_dir,user3@example.com"""
    
    with open(os.path.join(data_mgmt_dir, 'users_list.txt'), 'w') as f:
        f.write(users_list_content)
    
    # Create user directories
    for user_dir in ['user1_dir', 'user2_dir', 'user3_dir']:
        user_path = os.path.join(server_path, user_dir)
        os.makedirs(user_path, exist_ok=True)
        # Create some subfolders for user1
        if user_dir == 'user1_dir':
            os.makedirs(os.path.join(user_path, 'subfolder1'), exist_ok=True)
            os.makedirs(os.path.join(user_path, 'subfolder2'), exist_ok=True)
    
    return temp_dir, server_path, data_mgmt_dir

@pytest.fixture
def mock_data_folder(temp_dir):
    """Create a mock data folder with necessary structure"""
    # Create data folder structure
    data_folder = os.path.join(temp_dir, 'test_data')
    session_dir = os.path.join(data_folder, 'session1')
    os.makedirs(session_dir, exist_ok=True)
    
    # Create info file
    with open(os.path.join(data_folder, 'test.info'), 'w') as f:
        f.write('test info content')
    
    # Create some test files
    with open(os.path.join(session_dir, 'test_file.txt'), 'w') as f:
        f.write('test file content')
    
    return data_folder

@pytest.fixture
def mock_dataset_handler(mock_server_path):
    """Create a mock dataset handler"""
    dir_path, server_path, _ = mock_server_path
    
    # Create a real DatasetFrameHandler instance
    handler = DatasetFrameHandler(dir_path)
    
    # Override server_path and server_home_dir
    handler.server_path = server_path
    handler.server_home_dir = os.path.join(server_path, 'data_management')
    
    # Create empty dataset_frame.csv
    dataset_frame = pd.DataFrame(columns=['date', 'time', 'user', 'email', 'recording', 'recording_path', 'info_file_exists'])
    dataset_frame.to_csv(os.path.join(handler.server_home_dir, 'dataset_frame.csv'), index=False)
    
    return handler

def test_parse_arguments():
    """Test argument parsing with data folder specified"""
    with patch('sys.argv', ['blech_data_transfer.py', '/test/path']):
        from archive.src.blech_data_transfer import parse_arguments
        args = parse_arguments()
        assert args.data_folder == '/test/path'

def test_get_data_folder():
    """Test getting data folder from arguments"""
    from archive.src.blech_data_transfer import get_data_folder
    
    # Test with data folder in args
    args = MagicMock()
    args.data_folder = '/test/path'
    
    with patch('easygui.diropenbox', return_value='/gui/path'):
        result = get_data_folder(args)
        assert result == '/test/path'
    
    # Test with no data folder in args, using GUI
    args.data_folder = None
    
    with patch('easygui.diropenbox', return_value='/gui/path'):
        result = get_data_folder(args)
        assert result == '/gui/path'
    
    # Test with trailing slash
    args.data_folder = '/test/path/'
    
    with patch('easygui.diropenbox', return_value='/gui/path'):
        result = get_data_folder(args)
        assert result == '/test/path'

def test_initialize_dataset_handler(mock_server_path):
    """Test initializing dataset handler"""
    from archive.src.blech_data_transfer import initialize_dataset_handler
    
    dir_path, _, _ = mock_server_path
    
    with patch('sys.stdout', new=StringIO()):
        handler = initialize_dataset_handler(dir_path)
    
    assert handler is not None
    assert hasattr(handler, 'check_dataset_frame')
    assert hasattr(handler, 'sync_logs')

def test_check_experiment_existence(mock_dataset_handler, mock_data_folder):
    """Test checking if experiment exists"""
    from archive.src.blech_data_transfer import check_experiment_existence
    
    # Mock check_experiment_exists to return False
    mock_dataset_handler.check_experiment_exists = MagicMock(return_value=False)
    
    with patch('sys.stdout', new=StringIO()):
        # Should not raise any exceptions
        check_experiment_existence(mock_dataset_handler, mock_data_folder)
    
    # Mock check_experiment_exists to return True
    mock_dataset_handler.check_experiment_exists = MagicMock(return_value=True)
    
    # Test with user choosing to continue
    with patch('sys.stdout', new=StringIO()), \
         patch('builtins.input', side_effect=['y']):
        check_experiment_existence(mock_dataset_handler, mock_data_folder)
    
    # Test with user choosing to exit
    with patch('sys.stdout', new=StringIO()), \
         patch('builtins.input', side_effect=['n']), \
         patch('sys.exit') as mock_exit:
        check_experiment_existence(mock_dataset_handler, mock_data_folder)
        mock_exit.assert_called_once()

def test_validate_data_folder(mock_data_folder):
    """Test validating data folder"""
    from archive.src.blech_data_transfer import validate_data_folder
    
    # Test with valid folder
    with patch('sys.stdout', new=StringIO()):
        result = validate_data_folder(mock_data_folder)
        assert result is None  # Function doesn't return anything
    
    # Test with invalid folder
    with patch('sys.stdout', new=StringIO()), \
         patch('sys.exit') as mock_exit:
        validate_data_folder('/nonexistent/path')
        mock_exit.assert_called_once()

def test_check_info_file(mock_data_folder):
    """Test checking for info file"""
    from archive.src.blech_data_transfer import check_info_file
    
    # Test with existing info file
    with patch('sys.stdout', new=StringIO()):
        result = check_info_file(mock_data_folder)
        assert result == os.path.join(mock_data_folder, 'test.info')
    
    # Remove the info file
    os.remove(os.path.join(mock_data_folder, 'test.info'))
    
    # Test with no info file, user chooses to exit
    with patch('sys.stdout', new=StringIO()), \
         patch('builtins.input', side_effect=['e']), \
         patch('sys.exit') as mock_exit:
        check_info_file(mock_data_folder)
        mock_exit.assert_called_once()
    
    # Test with no info file, user chooses to wait then finds file
    info_file_path = os.path.join(mock_data_folder, 'new.info')
    with patch('sys.stdout', new=StringIO()), \
         patch('builtins.input', side_effect=['w', '']), \
         patch('glob', side_effect=[[], [info_file_path]]):
        # Create the info file after the first glob call
        with open(info_file_path, 'w') as f:
            f.write('test info content')
        result = check_info_file(mock_data_folder)
        assert result == info_file_path

def test_select_user(mock_server_path):
    """Test selecting a user from the list"""
    from archive.src.blech_data_transfer import select_user
    
    _, server_path, data_mgmt_dir = mock_server_path
    
    # Read users list
    users_list = pd.read_csv(os.path.join(data_mgmt_dir, 'users_list.txt'))
    
    # Test with valid selection
    with patch('builtins.input', return_value='1'), \
         patch('sys.stdout', new=StringIO()):
        user, user_path = select_user(users_list, server_path)
        assert user == 'user1'
        assert 'user1_dir' in user_path
    
    # Test with invalid then valid selection
    with patch('builtins.input', side_effect=['invalid', '2']), \
         patch('sys.stdout', new=StringIO()):
        user, user_path = select_user(users_list, server_path)
        assert user == 'user2'
        assert 'user2_dir' in user_path

def test_select_subfolder(mock_server_path):
    """Test selecting a subfolder"""
    from archive.src.blech_data_transfer import select_subfolder
    
    _, server_path, _ = mock_server_path
    user_path = os.path.join(server_path, 'user1_dir')
    
    # Test selecting existing subfolder
    with patch('builtins.input', return_value='1'), \
         patch('sys.stdout', new=StringIO()):
        copy_dir = select_subfolder(user_path)
        assert copy_dir == os.path.join(user_path, 'subfolder1')
    
    # Test creating new subfolder
    with patch('builtins.input', side_effect=['-1', 'new_subfolder']), \
         patch('sys.stdout', new=StringIO()):
        copy_dir = select_subfolder(user_path)
        assert copy_dir == os.path.join(user_path, 'new_subfolder')
        assert os.path.exists(os.path.join(user_path, 'new_subfolder'))
    
    # Test with invalid then valid selection
    with patch('builtins.input', side_effect=['invalid', '2']), \
         patch('sys.stdout', new=StringIO()):
        copy_dir = select_subfolder(user_path)
        assert copy_dir == os.path.join(user_path, 'subfolder2')

def test_prepare_file_transfer(mock_data_folder, mock_server_path):
    """Test preparing file transfer"""
    from archive.src.blech_data_transfer import prepare_file_transfer
    
    _, server_path, _ = mock_server_path
    copy_dir = os.path.join(server_path, 'user1_dir', 'subfolder1')
    
    with patch('sys.stdout', new=StringIO()):
        dir_list, file_list, rel_file_list, server_data_folder = prepare_file_transfer(mock_data_folder, copy_dir)
    
    assert isinstance(dir_list, list)
    assert isinstance(file_list, list)
    assert isinstance(rel_file_list, list)
    assert os.path.exists(server_data_folder)
    assert os.path.basename(mock_data_folder) in server_data_folder
    
    # Check if session1 is in dir_list
    assert any('session1' in d for d in dir_list)
    
    # Check if test_file.txt is in rel_file_list
    assert any('test_file.txt' in f for f in rel_file_list)

def test_transfer_data(mock_data_folder, mock_server_path):
    """Test transferring data"""
    from archive.src.blech_data_transfer import transfer_data
    
    _, server_path, _ = mock_server_path
    copy_dir = os.path.join(server_path, 'user1_dir', 'subfolder1')
    server_data_folder = os.path.join(copy_dir, os.path.basename(mock_data_folder))
    os.makedirs(server_data_folder, exist_ok=True)
    
    # Get file lists
    dir_list = [os.path.join(mock_data_folder, 'session1')]
    file_list = [
        os.path.join(mock_data_folder, 'test.info'),
        os.path.join(mock_data_folder, 'session1', 'test_file.txt')
    ]
    rel_file_list = [
        'test.info',
        os.path.join('session1', 'test_file.txt')
    ]
    
    with patch('sys.stdout', new=StringIO()), \
         patch('tqdm', lambda x: x):
        transfer_data(mock_data_folder, server_data_folder, dir_list, rel_file_list)
    
    # Check if directories were created
    assert os.path.exists(os.path.join(server_data_folder, 'session1'))
    
    # Check if files were copied
    assert os.path.exists(os.path.join(server_data_folder, 'test.info'))
    assert os.path.exists(os.path.join(server_data_folder, 'session1', 'test_file.txt'))

def test_add_log_entry(mock_dataset_handler, mock_server_path, mock_data_folder):
    """Test adding log entry"""
    from archive.src.blech_data_transfer import add_log_entry
    
    _, server_path, data_mgmt_dir = mock_server_path
    
    # Create users list
    users_list = pd.read_csv(os.path.join(data_mgmt_dir, 'users_list.txt'))
    
    user = 'user1'
    server_data_folder = os.path.join(server_path, 'user1_dir', 'subfolder1', os.path.basename(mock_data_folder))
    
    # Mock add_entry method
    mock_dataset_handler.add_entry = MagicMock()
    
    with patch('sys.stdout', new=StringIO()):
        add_log_entry(mock_dataset_handler, users_list, user, mock_data_folder, server_data_folder)
    
    # Check if add_entry was called with correct arguments
    mock_dataset_handler.add_entry.assert_called_once()
    args = mock_dataset_handler.add_entry.call_args[0][0]
    assert args['user'] == user
    assert args['recording'] == os.path.basename(mock_data_folder)
    assert args['recording_path'] == server_data_folder
    assert args['info_file_exists'] == True
