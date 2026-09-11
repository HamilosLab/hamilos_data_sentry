"""
Scan the Hamilos Lab network share for mouse sessions and build a per-session
data inventory.

Sessions are keyed by (mouse, session_n), where session_n is the per-mouse
integer session number used consistently across video/<Mouse>_<N>/,
Training/<Mouse>_<N>_*, and Analysis/.../<Mouse>_<Cohort>_<N>/. For each
session, this script records which of the known file categories (raw video,
CED, MBI, lab notebook, exclusions, gfit, videoQC object, statObj,
provenance) are present, plus marker/metadata convenience columns. The
results are saved to a CSV file for tracking purposes.

Unlike the old info.rhd-based scan, there's no single raw-acquisition marker
file for this lab's data, so "marker" and "metadata" are configurable file
categories (see local_only_files/sentry_config.yaml) rather than hardcoded
literals.
"""

import argparse
import copy
import os
import re
from datetime import datetime
from fnmatch import fnmatch
from time import time

import pandas as pd
import yaml
from tqdm import tqdm

from src.utils.utils import base_dir_path as dir_path


DEFAULT_CONFIG = {
    'paths': {
        'video_subdir_names': ['video', 'Video'],
        'training_subdir_names': ['Training', 'training'],
        'analysis_subdir_names': ['Analysis', 'analysis', 'ANALYSIS'],
    },
    'ignore_names': ['.DS_Store'],
    # Each category's search location (video/, Training/, or a session's
    # Analysis/ dirs) is fixed in build_session_inventory, not configurable
    # here -- only `glob` (which filenames count) and the `is_marker` /
    # `is_metadata` flags can be overridden per category.
    'file_categories': {
        'video_raw': {
            'glob': ['*.avi'],
        },
        'ced': {
            # .smrx/.s2rx are raw Spike2 exports and count as CED files even
            # when the filename doesn't say "CED" (e.g. Amber_10.s2rx).
            'glob': ['*_CED.mat', '*.smrx', '*.s2rx'],
            'is_marker': True,
        },
        'mbi': {
            'glob': ['*_MBI_*.mat'],
            'is_marker': True,
            'is_metadata': True,
        },
        'day_notebook': {
            'glob': ['* Day *.txt'],
            'is_metadata': True,
        },
        'exclusions': {
            'glob': ['*exclusions*videoqc*.txt', '*exclusions*videoQC*.txt'],
            'is_metadata': True,
        },
        'gfit': {
            'glob': ['gfit.mat'],
        },
        'videoqc_obj': {
            'glob': ['*videoQCobj.mat'],
            'is_marker': True,
        },
        'stat_obj': {
            'glob': ['*_statObj.mat'],
        },
        'provenance': {
            'glob': ['*provenance*.txt'],
            'is_metadata': True,
        },
    },
}

# <Mouse>_<Cohort>_<N> (Analysis/) or <Mouse>_<N> (video/) session directories.
SESSION_DIR_RE_TMPL = r'^{mouse}_(?:(?P<cohort>[A-Za-z0-9]+)_)?(?P<n>\d+)$'
# <Mouse>_<N>_<rest> or <Mouse>_<N>.<ext> files in Training/ (e.g.
# Bob_100_CED.mat, but also raw Spike2 exports like Amber_10.s2rx that never
# got a "_CED" suffix).
TRAINING_PREFIX_RE_TMPL = r'^{mouse}_(?P<n>\d+)(?=[_.])'
# "<Mouse> Day <N>[ suffix].txt" lab notebook entries in Training/.
DAY_NOTEBOOK_RE_TMPL = r'^{mouse} Day (?P<n>\d+)\b'
# <Mouse>_<N>[video[s]][_]videoQCobj.mat, found flat under Analysis/.
VIDEOQC_FLAT_RE_TMPL = r'^{mouse}_(?P<n>\d+)(?:videos?)?_?videoqcobj\.mat$'


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Scan the Hamilos Lab server for sessions and build a per-session data inventory')
    parser.add_argument('--ignore_blacklist', action='store_true', help='Ignore the blacklist file')
    return parser.parse_args()


def get_server_path(dir_path):
    """Get and validate the server path from the configuration file"""
    server_path_file = os.path.join(dir_path, 'local_only_files', 'server_path.txt')
    with open(server_path_file, 'r') as f:
        server_path = f.read().strip()

    # Check that server_path exists and is accessible
    if not os.path.exists(server_path):
        print('Server path does not exist')
        exit()
    if not os.access(server_path, os.R_OK):
        print('Server path is not accessible')
        exit()

    print(f'Server path file: {server_path_file}')
    print(f'Server path: {server_path}')
    return server_path


def setup_output_dir(dir_path):
    """
    Set up the local output directory for scan results.

    The Hamilos Lab share (local_only_files/server_path.txt) is mounted
    read-only, so results can't be written alongside the data the way the
    old Katz-lab tool did -- output lives locally, next to this repo,
    instead.
    """
    output_dir = os.path.join(dir_path, 'data_management')
    if not os.path.exists(output_dir):
        print(f'Creating output directory: {output_dir}')
        os.mkdir(output_dir)
    else:
        print(f'Output directory already exists: {output_dir}')
    return output_dir


def handle_blacklist(output_dir, dir_path, ignore_blacklist):
    """Handle the blacklist file and return the blacklist and blacklist file path"""
    if not ignore_blacklist:
        # Look for blacklist file in both output_dir and dir_path
        blacklist_file_paths = [
                os.path.join(output_dir, 'sentry_blacklist.txt'),
                os.path.join(dir_path, 'local_only_files', 'sentry_blacklist.txt')
                ]
        for f in blacklist_file_paths:
            if os.path.exists(f):
                blacklist_file = f
                break
        else:
            print('Blacklist file not found')
            print('Continuing without blacklist')
            return [], None, 'None'

        print(f'Blacklist file: {blacklist_file}')
        print()

        # Read blacklist file
        with open(blacklist_file, 'r') as f:
            blacklist = [line for line in f.read().splitlines() if line.strip()]
        blacklist_str = '\n'.join(blacklist) if blacklist else 'None'
        print('Blacklist:\n'+'========='+'\n'+blacklist_str)
        print()
        return blacklist, blacklist_file, blacklist_str
    else:
        blacklist = []
        blacklist_str = 'None'
        print('Ignoring blacklist')
        print()
        return blacklist, None, blacklist_str


def load_scan_config(dir_path):
    """Load the scan configuration, falling back to DEFAULT_CONFIG for any unset keys"""
    config = copy.deepcopy(DEFAULT_CONFIG)
    config_path = os.path.join(dir_path, 'local_only_files', 'sentry_config.yaml')
    if os.path.exists(config_path):
        print(f'Loading scan config: {config_path}')
        with open(config_path, 'r') as f:
            user_config = yaml.safe_load(f) or {}
        for key, value in user_config.items():
            if value is not None:
                config[key] = value
    else:
        print('No sentry_config.yaml found, using built-in defaults')
    return config


def get_directories_to_scan(server_path, blacklist):
    """Get list of mouse directories to scan (one level below server_path)"""
    mouse_dirs = sorted(
            d for d in os.listdir(server_path)
            if os.path.isdir(os.path.join(server_path, d))
            )
    if blacklist:
        mouse_dirs = [d for d in mouse_dirs if d not in blacklist]

    mouse_dirs_str = '\n'.join(mouse_dirs)
    print('Mouse directories to scan:\n'+mouse_dirs_str)
    print()

    return mouse_dirs, mouse_dirs_str


def _find_subdir(root, name_variants):
    """Return the first existing subdirectory of `root` matching a name variant"""
    for name in name_variants:
        candidate = os.path.join(root, name)
        if os.path.isdir(candidate):
            return candidate
    return None


def discover_sessions(server_path, mouse_dirs, config):
    """
    For each mouse, discover the canonical set of (mouse, session_n) sessions
    by parsing video/, Training/, and Analysis/ subdirectory and file names.

    Returns:
        sessions: dict mouse -> {n: {'video_dir': str or None,
                                      'analysis_dirs': [(cohort, path), ...]}}
        unparsed: dict mouse -> sorted list of names that looked session-like
                  (started with the mouse's name) but didn't parse as a
                  session -- logged for manual review instead of dropped.
    """
    paths_cfg = config['paths']
    ignore_names = set(config.get('ignore_names', []))
    sessions = {}
    unparsed = {}

    print('Discovering sessions')
    for mouse in tqdm(mouse_dirs):
        mouse_path = os.path.join(server_path, mouse)
        mouse_sessions = {}
        mouse_unparsed = []

        def _get_session(n):
            return mouse_sessions.setdefault(n, {'video_dir': None, 'analysis_dirs': []})

        # video/<Mouse>_<N>/
        video_dir = _find_subdir(mouse_path, paths_cfg['video_subdir_names'])
        if video_dir:
            session_re = re.compile(SESSION_DIR_RE_TMPL.format(mouse=re.escape(mouse)), re.IGNORECASE)
            for name in os.listdir(video_dir):
                if name in ignore_names or not os.path.isdir(os.path.join(video_dir, name)):
                    continue
                m = session_re.match(name)
                if m:
                    _get_session(int(m.group('n')))['video_dir'] = os.path.join(video_dir, name)
                elif name.lower().startswith(mouse.lower() + '_'):
                    mouse_unparsed.append(os.path.join('video', name))

        # Training/<Mouse>_<N>_* and "<Mouse> Day <N>....txt"
        training_dir = _find_subdir(mouse_path, paths_cfg['training_subdir_names'])
        if training_dir:
            prefix_re = re.compile(TRAINING_PREFIX_RE_TMPL.format(mouse=re.escape(mouse)), re.IGNORECASE)
            day_re = re.compile(DAY_NOTEBOOK_RE_TMPL.format(mouse=re.escape(mouse)), re.IGNORECASE)
            for name in os.listdir(training_dir):
                if name in ignore_names or not os.path.isfile(os.path.join(training_dir, name)):
                    continue
                m = prefix_re.match(name) or day_re.match(name)
                if m:
                    _get_session(int(m.group('n')))
                elif name.lower().startswith(mouse.lower()):
                    mouse_unparsed.append(os.path.join('Training', name))

        # Analysis/.../<Mouse>_<Cohort>_<N>/ (arbitrary intermediate nesting,
        # e.g. "ALL SESSIONS/VLS/" or "juice vs no juice/no juice/VLS/")
        analysis_dir = _find_subdir(mouse_path, paths_cfg['analysis_subdir_names'])
        if analysis_dir:
            session_re = re.compile(SESSION_DIR_RE_TMPL.format(mouse=re.escape(mouse)), re.IGNORECASE)
            for root, dirnames, _ in os.walk(analysis_dir):
                for name in list(dirnames):
                    if name in ignore_names:
                        dirnames.remove(name)
                        continue
                    m = session_re.match(name)
                    if m:
                        cohort = m.group('cohort') or ''
                        session = _get_session(int(m.group('n')))
                        session['analysis_dirs'].append((cohort, os.path.join(root, name)))
                        # A matched session dir's contents are files, not
                        # further session folders -- don't descend into it.
                        dirnames.remove(name)
                    elif name.lower().startswith(mouse.lower() + '_'):
                        mouse_unparsed.append(
                                os.path.join(os.path.relpath(root, mouse_path), name))

        sessions[mouse] = mouse_sessions
        if mouse_unparsed:
            unparsed[mouse] = sorted(set(mouse_unparsed))

    n_sessions = sum(len(v) for v in sessions.values())
    print(f'Discovered {n_sessions} sessions across {len(mouse_dirs)} mice')
    return sessions, unparsed


def _list_files(d):
    """List files (not directories) directly inside `d`"""
    if not d:
        return []
    try:
        return [os.path.join(d, f) for f in os.listdir(d) if os.path.isfile(os.path.join(d, f))]
    except OSError:
        return []


def _match_patterns(paths, patterns):
    """Case-insensitive fnmatch of each path's basename against any of `patterns`"""
    return [
            p for p in paths
            if any(fnmatch(os.path.basename(p).lower(), pat.lower()) for pat in patterns)
            ]


def _category_result(server_path, name, cat_cfg, dirs=None, candidates=None):
    """
    Match cat_cfg['glob'] patterns against files found by listing `dirs`
    (directories to search directly inside) unioned with a pre-filtered
    `candidates` file list, and summarize as presence/count/paths columns.
    """
    pool = list(candidates or [])
    for d in (dirs or []):
        pool.extend(_list_files(d))
    matches = sorted(set(_match_patterns(pool, cat_cfg['glob'])))
    rel_paths = [os.path.relpath(m, server_path) for m in matches]
    return {
            f'{name}_present': len(matches) > 0,
            f'{name}_count': len(matches),
            f'{name}_paths': ';'.join(rel_paths),
            }


def _index_training_files(training_dir, mouse):
    """One pass over Training/: session_n -> list of that session's files"""
    index = {}
    if not training_dir:
        return index
    prefix_re = re.compile(TRAINING_PREFIX_RE_TMPL.format(mouse=re.escape(mouse)), re.IGNORECASE)
    day_re = re.compile(DAY_NOTEBOOK_RE_TMPL.format(mouse=re.escape(mouse)), re.IGNORECASE)
    for f in _list_files(training_dir):
        base = os.path.basename(f)
        m = prefix_re.match(base) or day_re.match(base)
        if m:
            index.setdefault(int(m.group('n')), []).append(f)
    return index


def _index_videoqc_objs(analysis_dir, mouse):
    """One pass over Analysis/: session_n -> list of flat videoQCobj.mat files"""
    index = {}
    if not analysis_dir:
        return index
    pattern = re.compile(VIDEOQC_FLAT_RE_TMPL.format(mouse=re.escape(mouse)), re.IGNORECASE)
    for root, _, files in os.walk(analysis_dir):
        for f in files:
            m = pattern.match(f)
            if m:
                index.setdefault(int(m.group('n')), []).append(os.path.join(root, f))
    return index


def build_session_inventory(server_path, sessions, config):
    """Build a wide per-session inventory dataframe from discovered sessions"""
    cats = config['file_categories']
    marker_cats = [name for name, c in cats.items() if c.get('is_marker')]
    metadata_cats = [name for name, c in cats.items() if c.get('is_metadata')]
    rows = []

    print('Building session inventory')
    for mouse, mouse_sessions in tqdm(sessions.items()):
        mouse_path = os.path.join(server_path, mouse)
        training_dir = _find_subdir(mouse_path, config['paths']['training_subdir_names'])
        analysis_dir = _find_subdir(mouse_path, config['paths']['analysis_subdir_names'])

        training_index = _index_training_files(training_dir, mouse)
        videoqc_index = _index_videoqc_objs(analysis_dir, mouse)

        for n, info in sorted(mouse_sessions.items()):
            training_files = training_index.get(n, [])
            analysis_session_dirs = [p for _, p in info['analysis_dirs']]

            row = {
                    'mouse': mouse,
                    'session_n': n,
                    'session_key': f'{mouse}_{n}',
                    'cohorts': ';'.join(sorted({c for c, _ in info['analysis_dirs'] if c})),
                    'n_analysis_copies': len(info['analysis_dirs']),
                    }

            row.update(_category_result(
                server_path, 'video_raw', cats['video_raw'],
                dirs=[info['video_dir']] if info['video_dir'] else []))
            row.update(_category_result(
                server_path, 'ced', cats['ced'], candidates=training_files))
            row.update(_category_result(
                server_path, 'mbi', cats['mbi'], candidates=training_files))
            row.update(_category_result(
                server_path, 'day_notebook', cats['day_notebook'], candidates=training_files))
            row.update(_category_result(
                server_path, 'exclusions', cats['exclusions'],
                dirs=analysis_session_dirs, candidates=training_files))
            row.update(_category_result(
                server_path, 'gfit', cats['gfit'], dirs=analysis_session_dirs))
            row.update(_category_result(
                server_path, 'stat_obj', cats['stat_obj'], dirs=analysis_session_dirs))
            row.update(_category_result(
                server_path, 'provenance', cats['provenance'], dirs=analysis_session_dirs))
            row.update(_category_result(
                server_path, 'videoqc_obj', cats['videoqc_obj'],
                candidates=videoqc_index.get(n, [])))

            row['marker_present'] = any(row.get(f'{c}_present') for c in marker_cats)
            row['metadata_present'] = any(row.get(f'{c}_present') for c in metadata_cats)

            rows.append(row)

    dataset_frame = pd.DataFrame(rows)
    if not dataset_frame.empty:
        dataset_frame = dataset_frame.sort_values(['mouse', 'session_n']).reset_index(drop=True)
    print(f'Found {len(dataset_frame)} sessions across {len(sessions)} mice')
    return dataset_frame


def write_results(dataset_frame, output_dir, start_time, blacklist_str, mouse_dirs_str, unparsed):
    """Write results to files"""
    now = datetime.now()
    date_time = now.strftime("%m/%d/%Y, %H:%M:%S")

    end_time = time()
    time_taken = end_time - start_time

    print('Writing session_inventory to csv file')
    out_path = os.path.join(output_dir, 'session_inventory.csv')
    print(f'Output path: {out_path}')
    dataset_frame.to_csv(out_path, index=False)

    unparsed_path = os.path.join(output_dir, 'unparsed_names.txt')
    print(f'Writing unparsed names to: {unparsed_path}')
    n_unparsed = sum(len(v) for v in unparsed.values())
    with open(unparsed_path, 'w') as f:
        for mouse, names in sorted(unparsed.items()):
            for name in names:
                f.write(f'{mouse}: {name}\n')

    print(f'Writing to log file : {output_dir}/last_scan.txt')
    with open(os.path.join(output_dir, 'last_scan.txt'), 'w') as f:
        f.write(date_time)
        f.write('\n\n')
        f.write(f'Time taken: {(time_taken)/60:.2f} minutes')
        f.write('\n\n')
        f.write('Blacklist:\n'+blacklist_str)
        f.write('\n\n')
        f.write('Mouse directories processed:\n'+mouse_dirs_str)
        f.write('\n\n')
        f.write(f'Sessions found: {len(dataset_frame)}')
        f.write('\n')
        f.write(f'Unparsed names found: {n_unparsed}')


def main():
    """Main function to run the script"""
    args = parse_arguments()
    start_time = time()

    # Get and validate server path
    server_path = get_server_path(dir_path)

    # Set up local output directory (the share is mounted read-only)
    output_dir = setup_output_dir(dir_path)

    # Handle blacklist
    blacklist, blacklist_file, blacklist_str = handle_blacklist(output_dir, dir_path, args.ignore_blacklist)

    # Get mouse directories to scan
    mouse_dirs, mouse_dirs_str = get_directories_to_scan(server_path, blacklist)

    # Load scan config
    config = load_scan_config(dir_path)

    # Discover sessions and build the inventory
    sessions, unparsed = discover_sessions(server_path, mouse_dirs, config)
    dataset_frame = build_session_inventory(server_path, sessions, config)

    # Write results
    write_results(dataset_frame, output_dir, start_time, blacklist_str, mouse_dirs_str, unparsed)


if __name__ == "__main__":
    main()
