import os
import tempfile
import shutil
from io import StringIO
from unittest.mock import patch, MagicMock

import pytest
import pandas as pd

from src.data_sentry import (
    parse_arguments,
    get_server_path,
    setup_output_dir,
    handle_blacklist,
    load_scan_config,
    get_directories_to_scan,
    discover_sessions,
    build_session_inventory,
    write_results,
    main,
    DEFAULT_CONFIG,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_server_path(temp_dir):
    """Create a mock server path structure"""
    local_only_dir = os.path.join(temp_dir, 'local_only_files')
    os.makedirs(local_only_dir, exist_ok=True)

    server_path = os.path.join(temp_dir, 'server')
    os.makedirs(server_path, exist_ok=True)

    with open(os.path.join(local_only_dir, 'server_path.txt'), 'w') as f:
        f.write(server_path)

    return temp_dir, server_path


def _write(path, content='data'):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)


@pytest.fixture
def mock_server_structure(mock_server_path):
    """
    Build a mock Mouse Data tree:
      - Bob_42: full session (video, CED, MBI, day-notebook, exclusions,
        gfit, statObj, provenance, videoQC obj) duplicated across two
        Analysis cohort groupings, plus one unparsed video-folder name.
      - Amber_16: partial session (video + CED only, no Training/Analysis
        metadata) -- no Analysis dir at all for this mouse.
    """
    dir_path, server_path = mock_server_path

    data_mgmt_dir = os.path.join(server_path, 'data_management')
    os.makedirs(data_mgmt_dir, exist_ok=True)

    # --- Bob ---
    bob = os.path.join(server_path, 'Bob')
    _write(os.path.join(bob, 'video', 'Bob_42', 'Bob_42-01012025120000-0000.avi'))
    _write(os.path.join(bob, 'video', 'Bob_notasession', 'placeholder.avi'))
    _write(os.path.join(bob, 'Training', 'Bob_42_CED.mat'))
    _write(os.path.join(bob, 'Training', 'Bob_42_MBI_20250101.mat'))
    _write(os.path.join(bob, 'Training', 'Bob Day 42.txt'))
    _write(os.path.join(bob, 'Training', 'Bob_42_exclusions_videoQC_autopull.txt'))
    _write(os.path.join(
        bob, 'Analysis', 'ALL SESSIONS', 'VLS', 'Bob_VLS_42', 'gfit.mat'))
    _write(os.path.join(
        bob, 'Analysis', 'ALL SESSIONS', 'VLS', 'Bob_VLS_42',
        'Bob_REVISED_VLS_statObj.mat'))
    _write(os.path.join(
        bob, 'Analysis', 'ALL SESSIONS', 'VLS', 'Bob_VLS_42',
        'provenance_runID1__20250101_00_00.txt'))
    _write(os.path.join(
        bob, 'Analysis', 'juice vs no juice', 'no juice', 'VLS', 'Bob_VLS_42',
        'gfit.mat'))
    _write(os.path.join(bob, 'Analysis', 'VideoQC', 'Bob_42video_videoQCobj.mat'))

    # --- Amber ---
    amber = os.path.join(server_path, 'Amber')
    _write(os.path.join(amber, 'video', 'Amber_16', 'Amber_16-01022025120000-0000.avi'))
    _write(os.path.join(amber, 'Training', 'Amber_16_CED.mat'))

    return dir_path, server_path, data_mgmt_dir


def test_parse_arguments():
    with patch('sys.argv', ['data_sentry.py']):
        args = parse_arguments()
        assert not args.ignore_blacklist

    with patch('sys.argv', ['data_sentry.py', '--ignore_blacklist']):
        args = parse_arguments()
        assert args.ignore_blacklist


def test_get_server_path(mock_server_path):
    dir_path, server_path = mock_server_path

    with patch('sys.stdout', new=StringIO()):
        result = get_server_path(dir_path)

    assert result == server_path

    with patch('os.path.exists', return_value=False), \
         patch('builtins.exit') as mock_exit, \
         patch('sys.stdout', new=StringIO()):
        get_server_path(dir_path)
        mock_exit.assert_called_once()


def test_setup_output_dir(mock_server_path):
    """Output lives locally next to the repo, not on the (read-only) share"""
    dir_path, _ = mock_server_path

    output_dir = os.path.join(dir_path, 'data_management')
    if os.path.exists(output_dir):
        os.rmdir(output_dir)

    with patch('sys.stdout', new=StringIO()):
        result = setup_output_dir(dir_path)

    assert result == output_dir
    assert os.path.exists(output_dir)

    with patch('sys.stdout', new=StringIO()):
        result = setup_output_dir(dir_path)

    assert result == output_dir


def test_handle_blacklist(mock_server_structure):
    dir_path, server_path, data_mgmt_dir = mock_server_structure

    with patch('sys.stdout', new=StringIO()):
        blacklist, blacklist_file, blacklist_str = handle_blacklist(
            data_mgmt_dir, dir_path, False)

    assert blacklist == []
    assert blacklist_file is None
    assert blacklist_str == 'None'

    blacklist_content = "Amber\nignore_dir"
    with open(os.path.join(data_mgmt_dir, 'sentry_blacklist.txt'), 'w') as f:
        f.write(blacklist_content)

    with patch('sys.stdout', new=StringIO()):
        blacklist, blacklist_file, blacklist_str = handle_blacklist(
            data_mgmt_dir, dir_path, False)

    assert blacklist == ['Amber', 'ignore_dir']
    assert blacklist_file == os.path.join(data_mgmt_dir, 'sentry_blacklist.txt')
    assert blacklist_str == blacklist_content

    with patch('sys.stdout', new=StringIO()):
        blacklist, blacklist_file, blacklist_str = handle_blacklist(
            data_mgmt_dir, dir_path, True)

    assert blacklist == []
    assert blacklist_file is None
    assert blacklist_str == 'None'


def test_load_scan_config_defaults(tmp_path):
    """With no sentry_config.yaml present, defaults are used"""
    with patch('sys.stdout', new=StringIO()):
        config = load_scan_config(str(tmp_path))
    assert config == DEFAULT_CONFIG


def test_load_scan_config_override(tmp_path):
    local_only_dir = tmp_path / 'local_only_files'
    local_only_dir.mkdir()
    (local_only_dir / 'sentry_config.yaml').write_text(
        "ignore_names: ['.DS_Store', 'Thumbs.db']\n")

    with patch('sys.stdout', new=StringIO()):
        config = load_scan_config(str(tmp_path))

    assert config['ignore_names'] == ['.DS_Store', 'Thumbs.db']
    # Unset keys still fall back to defaults
    assert config['paths'] == DEFAULT_CONFIG['paths']
    assert config['file_categories'] == DEFAULT_CONFIG['file_categories']


def test_get_directories_to_scan(mock_server_structure):
    _, server_path, _ = mock_server_structure

    with patch('sys.stdout', new=StringIO()):
        mouse_dirs, mouse_dirs_str = get_directories_to_scan(server_path, [])

    assert set(mouse_dirs) == {'Bob', 'Amber', 'data_management'}
    assert 'Bob' in mouse_dirs_str
    assert 'Amber' in mouse_dirs_str

    with patch('sys.stdout', new=StringIO()):
        mouse_dirs, mouse_dirs_str = get_directories_to_scan(server_path, ['data_management'])

    assert set(mouse_dirs) == {'Bob', 'Amber'}


def test_discover_sessions(mock_server_structure):
    _, server_path, _ = mock_server_structure

    with patch('sys.stdout', new=StringIO()):
        sessions, unparsed = discover_sessions(server_path, ['Bob', 'Amber'], DEFAULT_CONFIG)

    assert set(sessions['Bob'].keys()) == {42}
    assert set(sessions['Amber'].keys()) == {16}

    bob_42 = sessions['Bob'][42]
    assert bob_42['video_dir'] is not None
    # Deduped session found under two different Analysis cohort groupings
    assert len(bob_42['analysis_dirs']) == 2
    assert {c for c, _ in bob_42['analysis_dirs']} == {'VLS'}

    assert 'Bob' in unparsed
    assert any('Bob_notasession' in name for name in unparsed['Bob'])


def test_build_session_inventory(mock_server_structure):
    _, server_path, _ = mock_server_structure

    with patch('sys.stdout', new=StringIO()):
        sessions, _ = discover_sessions(server_path, ['Bob', 'Amber'], DEFAULT_CONFIG)
        inventory = build_session_inventory(server_path, sessions, DEFAULT_CONFIG)

    assert len(inventory) == 2

    bob_row = inventory.loc[inventory['session_key'] == 'Bob_42'].iloc[0]
    assert bob_row['video_raw_present']
    assert bob_row['ced_present']
    assert bob_row['mbi_present']
    assert bob_row['day_notebook_present']
    assert bob_row['exclusions_present']
    assert bob_row['gfit_present']
    assert bob_row['gfit_count'] == 2  # duplicated across two cohort dirs
    assert bob_row['stat_obj_present']
    assert bob_row['provenance_present']
    assert bob_row['videoqc_obj_present']
    assert bob_row['marker_present']
    assert bob_row['metadata_present']
    assert bob_row['n_analysis_copies'] == 2

    amber_row = inventory.loc[inventory['session_key'] == 'Amber_16'].iloc[0]
    assert amber_row['video_raw_present']
    assert amber_row['ced_present']
    assert not amber_row['mbi_present']
    assert not amber_row['gfit_present']
    assert amber_row['marker_present']  # ced is a marker category
    assert not amber_row['metadata_present']  # no mbi/day_notebook/exclusions/provenance


def test_write_results(mock_server_structure):
    _, _, data_mgmt_dir = mock_server_structure

    dataset_frame = pd.DataFrame({
        'mouse': ['Bob'],
        'session_n': [42],
        'session_key': ['Bob_42'],
    })

    start_time = 1000
    blacklist_str = "Amber"
    mouse_dirs_str = "Bob\nAmber"
    unparsed = {'Bob': ['video/Bob_notasession']}

    with patch('sys.stdout', new=StringIO()):
        write_results(dataset_frame, data_mgmt_dir, start_time, blacklist_str, mouse_dirs_str, unparsed)

    assert os.path.exists(os.path.join(data_mgmt_dir, 'session_inventory.csv'))
    assert os.path.exists(os.path.join(data_mgmt_dir, 'unparsed_names.txt'))
    assert os.path.exists(os.path.join(data_mgmt_dir, 'last_scan.txt'))

    with open(os.path.join(data_mgmt_dir, 'unparsed_names.txt')) as f:
        content = f.read()
        assert 'Bob: video/Bob_notasession' in content

    with open(os.path.join(data_mgmt_dir, 'last_scan.txt')) as f:
        content = f.read()
        assert 'Time taken:' in content
        assert 'Blacklist:\nAmber' in content
        assert 'Mouse directories processed:\nBob\nAmber' in content
        assert 'Sessions found: 1' in content


@patch('src.data_sentry.parse_arguments')
@patch('src.data_sentry.get_server_path')
@patch('src.data_sentry.setup_output_dir')
@patch('src.data_sentry.handle_blacklist')
@patch('src.data_sentry.get_directories_to_scan')
@patch('src.data_sentry.load_scan_config')
@patch('src.data_sentry.discover_sessions')
@patch('src.data_sentry.build_session_inventory')
@patch('src.data_sentry.write_results')
def test_main(mock_write, mock_build, mock_discover, mock_load_config, mock_get_dirs,
              mock_handle, mock_setup, mock_get_path, mock_parse):
    mock_args = MagicMock()
    mock_args.ignore_blacklist = False
    mock_parse.return_value = mock_args

    mock_get_path.return_value = '/mock/server/path'
    mock_setup.return_value = '/mock/repo/path/data_management'
    mock_handle.return_value = (['user3'], '/mock/blacklist/file', 'user3')
    mock_get_dirs.return_value = (['Bob', 'Amber'], 'Bob\nAmber')
    mock_load_config.return_value = DEFAULT_CONFIG
    mock_discover.return_value = ({'Bob': {}}, {})
    mock_build.return_value = pd.DataFrame({'col1': [1, 2]})

    main()

    mock_parse.assert_called_once()
    mock_setup.assert_called_once()  # called with this repo's base_dir_path
    mock_get_dirs.assert_called_once()
    mock_discover.assert_called_once()
    mock_build.assert_called_once()
    mock_write.assert_called_once()
