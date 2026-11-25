# Day-notebook metadata: fields, fill rates, and consistency with path

Research for ticket #14. Planning/reading only; nothing on the share was modified.
Report holds field names, vocabularies, counts and mismatch counts only; no free text from notebooks.

## Method

- Located notebooks from `data_management/session_inventory.csv` (snapshot dated 2026-09-11, 1303 session rows, 40 mice, column `day_notebook_paths`). That gives **1138 notebooks, 34 mice**.
- Listed every `<Mouse>/Training/` folder on the share (read-only `os.listdir`) and found **260 more clean `<name> Day <N>.txt` notebooks** that the inventory does not list (see "Coverage gaps"). Parsed those too, so the headline population is **1398 notebooks, 39 mice**. Inventory-only numbers are given where they differ.
- Parsed with a throwaway script kept outside the repo (scratchpad). Parsing is line based: `LABEL: value`, optional leading `[x]` checkbox, label matched case-insensitively with whitespace collapsed. All files decode as text (0 decode errors); 1388 of 1398 use CRLF line endings.
- "Filled" = label present and value not blank and not just `?`/`??`/`???`.
- Date comparison uses the timestamp embedded in video filenames (`<Mouse>_<N>-MMDDYYYYHHMMSS-NNNN.avi`) from the inventory's `video_raw_paths`, so it is only possible where the inventory row has video.
- Excluded from parsing: 22 variant-named files (`Day temp`, `Day <N>_bad`, `_donotuse`, `_exclude`, `Day <N>_<M>`, `_water`, `_9%juice` suffixes). Not analysed.

## Notebook layout (verified)

A notebook is a semi-structured checklist, not a form. Verified by reading label census over all 1398 files:

1. A header block before `GENOTYPE`: first line is usually a recording-type label (1248 of 1398 contain the word "recording"), sometimes a line with a URL, then (last non-blank line without `:`/`=`) the **mouse name**. 100% of notebooks have such a line.
2. A metadata block: `GENOTYPE`, `GENDER`, `TASK`, `DAY`, `RIG`, `SURGERY`, `HEADPOST STYLE`, weights, `VLS-right/left`.
3. Task parameter dump (`params`, `Using File`, `Version Code`, then `name<TAB>value` rows), video setup, rig checklist, after-session checklist, `NOTES`.

339 distinct labels exist across the 1398 notebooks (after case/space folding). 29 occur in at least half of notebooks; 199 occur in fewer than 5. The long tail is checklist items, task parameters and one-off annotations. Animal-level and session-level metadata is a short list.

Labels present in the inventory's 1138 notebooks (count, in decreasing order; core metadata first):

| Label | Notebooks | Note |
|---|---|---|
| WEIGHT TODAY, GENOTYPE, TASK, GENDER | 1138 each (100%) | |
| NOTES | 1137 | free text; not read |
| RIG | 1118 | |
| DAY | 1117 | |
| INIT WEIGHT | 1096 | |
| SURGERY | 888 | `SURGERY DATE` is a second spelling in 191 more |
| TARGET WEIGHT | 855 | |
| HEADPOST STYLE | 827 | |
| VLS-right (several spellings) | 459 + 258 + 97 + ... | 17 spelling variants of the VLS labels |
| VLS-left (several spellings) | 372 + 261 + 96 + ... | |
| DATE | 291 | a second place for the session date |
| VIRUS | 96 | label present, **never filled** |
| GOLDPIN SURGERY | 53 | one mouse only |
| DOB | 13 (union) | only age-like field; 13 notebooks |
| Post-session weight | 6 spellings, union (`WEIGHT AFTER SESSION`, `POST-SESSION WEIGHT`, `END WEIGHT`, ...) | spelling drift |

Absent from every notebook (no label found in a regex search of labels): strain/litter/cohort, injection coordinates, virus titre as its own field, explicit "sensor" or "fiber side" label. Only 2 notebooks have an `INJECTION DONE` label. Sensor identity lives inside the `VLS-*` lines (below).

## Fill rates (1398 notebooks, 39 mice; inventory-only % in brackets)

Mice "any" = at least one notebook filled; "all" = every notebook of the mouse filled.

| Field | Label present | Filled | Mice any | Mice all |
|---|---|---|---|---|
| GENDER | 100% | 100% [100%] | 39/39 | 39/39 |
| GENOTYPE | 100% | 92.1% [90.2%] (111 blank) | 38/39 | 34/39 |
| TASK | 100% | 98.6% [98.2%] | 39/39 | 38/39 |
| DAY | 98.5% | 98.5% [98.2%] | 39/39 | 37/39 |
| RIG | 98.6% | 98.6% [98.2%] | 39/39 | 38/39 |
| SURGERY (either spelling) | 95.3% | 84.0% [82.9%] | 39/39 | 28/39 |
| HEADPOST STYLE | 72.2% | 72.2% [72.7%] | 32/39 | 23/39 |
| INIT WEIGHT | 92.0% | 64.9% [67.8%] | 25/39 | 15/39 |
| TARGET WEIGHT | 77.3% | 74.7% [74.2%] | 29/39 | 21/39 |
| WEIGHT TODAY | 100% | 98.3% [98.1%] | 39/39 | 23/39 |
| VLS-right value (strict label match) | 66.8% | 64.3% [65.1%] | 29/39 | 16/39 |
| VLS-left value (strict label match) | 63.2% | 60.4% [64.0%] | 28/39 | 18/39 |
| VIRUS | 11.4% | **0%** | 0/39 | 0/39 |
| DATE (separate from DAY) | 25.9% | 25.9% | 16/39 | 8/39 |
| GOLDPIN SURGERY | 3.9% | 3.9% | 1/39 | 0/39 |

Notes on the table:

- **Sensor identity is better covered than the strict VLS value fill suggests.** In 1363 notebooks (97.5%) some line begins with `VLS`, and in 1337 (95.6%) those lines contain a sensor keyword (tdt, rdlight, dlight, yfp/eyfp, ...) in the label or the value. 35 of 39 mice have it in at least one notebook; the 4 without are Peanut, Diana, Megamind, Tim. The strict-value rows undercount because many notebooks put the sensor in the label itself (for example a label that ends in the sensor name) and leave the value blank.
- **Session date.** A parsable date exists in `DAY` for 990 notebooks (70.8%), in `DATE` for 362, and in either for 1352 (96.7%). Where both exist they never disagree (0 conflicts). 32 of 39 mice have a date in every notebook; every mouse has at least one.
- **Surgery date.** 1169 notebooks (83.6%) carry a parsable surgery date. In 4 notebooks the surgery date is later than the session date.
- The `DAY` field holds the session number in 1367 notebooks (rest absent or unparsable: 31, all from the inventory set).

## Value vocabularies (constrained vs free text)

| Field | Vocabulary | Verdict |
|---|---|---|
| GENDER | `M`, `F`, `m`, `f` (M 534, F 532, m 211, f 121) | constrained; needs case folding |
| GENOTYPE | 13 distinct raw strings: a DAT-cre family (`DAT-cre`, `DAT-cre HET`, `DAT-Cre(+/-)`), `GCG-cre WT` / `GCG-Cre WT`, `wt` / `WT` (two with a family note in parentheses), `DAT-cre HET x TFAM-Flox HOMO` (+ a `HETa` typo variant and a `(MitoPark)` note) | constrained with spelling/case drift and parenthetical notes; DAT-cre vs DAT-cre HET vs DAT-Cre(+/-) are probably the same genotype written three ways (inference) |
| HEADPOST STYLE | 3 values in the inventory set: `stereotaxic dual` 754, `4 fiber + headpost` 42, `dual` 31 | constrained |
| RIG | integer 1 to 5 | constrained |
| TASK | 611 distinct strings built from tokens: `op0` (1101), `late` (445), `sucrose` (328), `photometry`/`photo` (375), `juice` (279), `op500` (131), `water` (127), `hyb500` (126), `sham` (101), `pretrain*` (143), `refresh` (33) | token-based free text; tokens are regular enough to parse, strings are not |
| SURGERY | `m/d/yy` followed by an optional `\| N days PO` tail. Forms: date + `N days PO` 448, date only 301, date + empty tail 151 or `N?` 95 or bare `\|` 97, plus `?` and blank | date is constrained; tail is a hand-typed counter |
| DAY (inventory set) | `day N \| m/d/yy` 795, `day [N]` 182, `day N` 75, bare `N` 37, a few others | mixed formats (about 12 shapes) |
| DATE | `m/d/yy` or `[m/d/yy]` | 2 shapes |
| WEIGHT fields | decimal number, sometimes with a unit letter or a parenthetical | mostly numeric |
| VLS-right/left value | sensor keyword plus any of: laser power (`uw`), current (`ma`), injection volume (`nl`), dilution, colour word, checkbox | free text with a small sensor vocabulary: tdt 319 / 428 (right/left), rdlight 292 / 160, dlight 226 / 178, yfp+eyfp 49 / 78 (keyword counts, strict value only) |
| VIRUS | never filled | n/a |

## Consistency of notebook content with folder and filename

### Coverage gaps in the inventory (affects what can be checked)

- 260 notebooks with clean `<name> Day <N>.txt` names are on the share but not in `day_notebook_paths`.
  - 141 have a modification time after the inventory snapshot (2026-09-11); they are simply newer than the scan. They include 3 mice absent from the inventory (Megamind, Tim, Diana; 21 notebooks).
  - 119 are older than the snapshot. 111 are OktoberfestB (issue #8: folder `OktoberfestB`, filenames `Oktoberfest B Day N`) and 6 are Ratthew (folder `Ratthew`, filenames spelled `Rattew`). Both fail `DAY_NOTEBOOK_RE_TMPL = r'^{mouse} Day (?P<n>\d+)\b'` in `src/data_sentry.py` (line 92), which requires the filename to start with the folder name (verified by reading the code; case-insensitive). The remaining 2 older-than-snapshot files (1 Dachary, 1 Ezio) I could not explain; unverified guess is a copied file that kept an old modification time.
  - So issue #8 is not unique: **Ratthew is a second mouse whose notebooks are invisible to the inventory for the same reason** (filename prefix differs from folder name), 0 of its 6 inventory sessions show a notebook while 17 exist.
- 6 of 40 inventory mice have no inventory notebook: OktoberfestB and Ratthew (name mismatch, above) plus Big Cheese, Jessie, TestHist1, TestHist2 (no notebook files found in `Training/` at all).
- Session-number agreement between filename and inventory `session_n` is 100% (0 of 1138 differ), but that is by construction since the inventory derives `session_n` from the filename.

### Mouse name

- **Filename vs folder:** 130 of 1398 differ literally. Breakdown: OktoberfestB / `Oktoberfest B` 111 (space), Ratthew / `Rattew` 17 (spelling), DonVito / `Donvito` 2 (case, the only one inside the inventory set). Ignoring case, spaces and punctuation, only the 17 Ratthew files disagree.
- **Mouse line inside the notebook vs folder:** 73 of 1398 (5.2%) disagree, across 13 mice (inventory set: 63 notebooks, 10 mice). Parenthetical annotations on the name line are stripped before comparing (45 notebooks have one). Causes, by type:
  - Longer or alternate name for the same animal, 48 notebooks: Prime 44 (all of Prime's notebooks use a longer name), Beauty 2, Lois2/Lois3 1 each (a short alias). Alias reading is an inference.
  - Another mouse's name, probably a notebook copied from that mouse as a template, 24 notebooks: Marsha 8 (carry Mimi's name, sessions 1-8), Ratthew 8 (carry Dachary's name, sessions 1-8), Ezio 3 (Dachary, sessions 1-3), Cannoli 1 (Bob, session 1), Peter 1 and Puffin 1 (OktoberfestB, first session), Diana 1 (Megamind), OktoberfestB 1 (Beauty, one session in the middle). In every case the foreign name appears in the first sessions of that mouse (except the OktoberfestB blip), consistent with "started from another animal's notebook and fixed the name later". The animal-level fields in those notebooks are the ones to distrust (next section).
  - Unparsable name line, 1 notebook (DonVito, a line describing the session type).

### Session number

- `DAY` number inside the notebook vs filename number: 139 of 1367 parsable (10.2%) disagree, across 28 mice (inventory set: 97 of 1107, 8.8%, 24 mice). Offsets: -1 in 87, -2 in 30, -3 in 11, -4 in 3, -5 in 2, and 6 outliers (+27, +10, -11, +1, and two more). So the notebook is almost always **behind** the filename.
- In 131 of the 139, the (wrong) `DAY` number equals the `DAY` number already used by an earlier notebook of the same mouse, which fits **copy-forward without updating** (inference). Consecutive notebooks of one mouse carry the same `DAY` number in 116 of 1317 pairs.
- 31 notebooks have no usable `DAY` number.

### Date

- Notebook `DAY` date vs the date in the first video filename of that session: 793 sessions comparable; **64 (8.1%) disagree, across 18 mice, and in all 64 the notebook date is earlier than the video date.** 48 differ by 1 to 7 days; 6 by 300+ days (year typos or very old template date); the other 10 by 8 to 22 days. In 54 of the 64, the notebook date equals the date of an earlier notebook of the same mouse (stale copy-forward; inference).
- Consecutive notebooks of one mouse share an identical `DAY` date in 67 of 953 pairs (7.0%). Whether any are legitimate same-day sessions is unknown.
- `DATE` vs `DAY` date: 0 conflicts.
- 1 session has video from more than one calendar date, so "the" session date is ambiguous there.
- Not checked: `DAY` date vs CED/MBI timestamps (not in the inventory).

### Other

- 4 notebooks are byte-identical (decoded text) to another notebook in the set.
- `N days PO` tail of `SURGERY`: present in 548 notebooks across 21 mice; consecutive notebooks of a mouse have the same N in 443 of 527 pairs, so it is not updated per session. Of the 437 inventory-set notebooks where N, the `DAY` date and the surgery date all parse, only 53 (12%) have N equal to (session date minus surgery date). Do not treat `N days PO` as a computed field; derive it from dates instead.

## Per-mouse consistency of animal-level facts (1398 notebooks, 39 mice)

Sessions of one mouse sorted by filename session number; "step" means a value changes once and stays changed.

| Fact | Mice with more than one distinct value | Detail |
|---|---|---|
| Sex (`GENDER`) | 4 by raw value, 3 after case folding | Amber: M for sessions 1-7, F for 8-28 (step). Dachary: M 1-12, F 13-14, M 15, F 16-26. Ezio: M 1-16, F 17-19 (step). The 4th (Bob) is `m` vs `M` only. **Which value is true is unknown from the notebooks alone.** |
| Genotype | 3 | Lois2: a one-letter typo variant in 2 notebooks. OktoberfestB: `DAT-cre` (3) vs `DAT-Cre(+/-)` (108), notation only. Sprite: a DAT-cre value for sessions 1-17, then a GCG-cre WT value for sessions 18-47 (step; a real conflict, not notation). Also 111 blank genotypes. |
| Surgery date | 4 | Lois3: 31 notebooks agree, 2 single-session deviations (typo-like). Marsha, Megamind, Tim: the earliest notebook(s) of each carry one date shared by all three mice, later notebooks carry a different date (step; template carry-over, inference). |
| Headpost style | 0 | consistent wherever filled |
| Virus | n/a | never filled |
| Sensor keyword, VLS-right (value only) | 4 | Bob: rdlight sessions 1-75 then tdt 76-119 (step). Jupyter: rdlight 1-12 then tdt 13-45 (step). Round: rdlight 1-19 then dlight 20-63 (step). Katniss: one-session blip. |
| Sensor keyword, VLS-left (value only) | 3 | Round: tdt 1-19 then eyfp 20-63 (step). Dachary: yfp to eyfp (spelling). Katniss: one-session blip. |
| Rig | 26 | expected; session-level, not animal-level |

Readings (inferences):

- Animal-level disagreement within a mouse is rare (about 3 mice for sex, 1 for real genotype change, 3 to 4 for surgery date) and almost always a **single step or single-session blip**, not interleaved noise. That pattern fits template copy-forward or a mid-series correction.
- The mice with a wrong name line (Marsha, Ratthew, Ezio) are the same mice whose early animal-level fields look suspect (Marsha surgery date; Ezio sex). Ratthew's fields are constant, and Ratthew's early notebooks carry Dachary's name line, so a foreign name line does not by itself prove the animal fields are wrong.
- Sensor changes for Bob, Jupyter and Round may be real (different recording configuration across a series) or label drift; the notebooks do not say. The sensor check uses the value text only, so it is a lower bound on disagreement for notebooks whose sensor is in the label.

## What this means for downstream tickets

- A registry built from notebooks should take sex, genotype and surgery date **per mouse with a vote or a conflict flag**, not from any single notebook. Sex needs case folding; genotype needs a small normalisation table (DAT-cre / DAT-cre HET / DAT-Cre(+/-); WT / wt).
- Session-level date and `DAY` number inside notebooks are unreliable (8 to 10% wrong, always stale). Prefer filename session number and video/CED timestamps; use the notebook date only as a cross-check.
- The name-line check will flag about 5% of notebooks; most are aliases or template carry-over, so an alias table is needed rather than a hard failure.
- Virus is never recorded as its own field, and no notebook has a surgery-sheet reference. Surgery-sheet cross-checking would add information that the notebooks do not hold (surgery date is the only overlap, present for all 39 mice but for all sessions in only 28).
- The inventory should also match filenames that differ from the folder name only by space or spelling (OktoberfestB, Ratthew), and it should be re-run: 141 notebooks are newer than the snapshot.

## Unknowns

- Ground truth for sex of Amber, Dachary, Ezio and genotype of Sprite.
- Whether sensor changes within Bob, Jupyter, Round are real.
- Whether the 3 folders with notebooks that are absent from the inventory (Megamind, Tim, Diana) belong in the registry.
- Why 1 Dachary and 1 Ezio notebook older than the snapshot are missing from the inventory.
- `DAY` date was only compared with video timestamps; no comparison with CED/MBI timestamps or with a surgery-sheet source.
- Parsing is regex based on labels; labels I did not enumerate (long tail of 339) may hold more metadata, and the 31 notebooks without a usable `DAY` number were not inspected by hand.

## Sources

- `data_management/session_inventory.csv` (columns `day_notebook_present`, `day_notebook_paths`, `video_raw_paths`, `session_n`).
- `src/data_sentry.py`: lines 60-62 (day_notebook glob, case-insensitive fnmatch at line 316), line 92 (`DAY_NOTEBOOK_RE_TMPL`), lines 261-265 and 344-349 (matching).
- Day-notebook files under `<Mouse>/Training/` on the share, read-only; analysis script was kept outside the repo.
