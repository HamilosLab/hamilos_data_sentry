![image](https://github.com/user-attachments/assets/cb03c5c9-da50-40fa-9fbe-99e29376615c)
Courtesy of ChatGPT

# Introduction

Scans the Hamilos Lab network share for mouse sessions and builds a per-session data inventory:
which of the known file categories (raw video, CED, MBI, lab notebook, exclusions, gfit, videoQC
object, statObj, provenance) exist for each `(mouse, session)`. This is a database of what data
already exists, not just a metadata-completeness gate.

Mounting the network share is outside this repo's job -- it assumes
`local_only_files/server_path.txt` already points at an accessible, mounted path (e.g.
`/media/whitehead_drives/solexa_hamilos/Mouse Data`). That share is mounted **read-only**, so scan
output is written locally, next to this repo (`data_management/`), not onto the share.

Sessions are keyed by a per-mouse integer session number `N`, used consistently across:
- `<server_path>/<Mouse>/video/<Mouse>_<N>/` -- raw video
- `<server_path>/<Mouse>/Training/<Mouse>_<N>_*` and `"<Mouse> Day <N>....txt"` -- CED, MBI, lab
  notebook, exclusions
- `<server_path>/<Mouse>/Analysis/.../<Mouse>_<Cohort>_<N>/` -- gfit, statObj, provenance (the same
  session is sometimes duplicated across multiple ad hoc `Analysis` grouping folders; the scanner
  dedupes by `(mouse, N)`)

# Scripts in the src directory

## data_sentry.py

Scans `local_only_files/server_path.txt` for mice, discovers sessions under each mouse's
`video/`, `Training/`, and `Analysis/` subfolders, and checks which file categories are present
for each session (see `local_only_files/sentry_config.yaml` for the glob patterns and subdirectory
name variants used). Writes, to a local `data_management/` directory next to this repo (the share
itself is read-only):

- `data_management/session_inventory.csv` -- one row per session, with `<category>_present` /
  `<category>_count` / `<category>_paths` columns, plus `marker_present` (a session MATLAB object
  exists) and `metadata_present` (the day-notebook/exclusions/MBI files exist) convenience columns.
- `data_management/unparsed_names.txt` -- names that looked session-like (started with a mouse's
  name) but didn't parse as `<Mouse>_<N>`, for manual review.
- `data_management/last_scan.txt` -- scan timestamp, duration, blacklist, and mouse directories
  processed.

# How to use

## data_sentry.py
```
usage: python -m src.data_sentry [--ignore_blacklist]

Scan the Hamilos Lab server for sessions and build a per-session data inventory.

options:
  -h, --help          show this help message and exit
  --ignore_blacklist  Ignore the blacklist file when scanning directories
```

## Configuration

- `local_only_files/server_path.txt` -- the mounted root to scan (one mouse folder per line item
  under it).
- `local_only_files/sentry_blacklist.txt` -- newline list of top-level directory names to skip
  (e.g. non-mouse folders, or mice to exclude from a given scan).
- `local_only_files/sentry_config.yaml` -- optional; overrides subdirectory name variants and
  file-category glob patterns. See the comments in that file for the defaults.

# Archived

`archive/` holds the original Katz Lab transfer tool (manual local-to-server copy gated on a
metadata file), its recording-log handler, the Katz personnel roster, and the old CIFS mount
script. These don't match how Hamilos Lab data arrives (rig-generated, landing directly on the
network share) and aren't run in CI -- see `archive/README.md`.
