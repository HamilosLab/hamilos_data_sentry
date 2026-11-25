# How surgery sheets and surgery notes are stored on the share (ticket 15)

Researched 2026-11-25. Read-only listing of the share (`solexa_hamilos`). No file contents were opened, so "scan belongs to mouse X" below is always inferred from file names only.

Terms: `<share>` = `solexa_hamilos`; `Mouse Data` = the per-mouse folders. Mouse list = the 40 distinct values of the `mouse` column in `data_management/session_inventory.csv` (1303 session rows; counted with Python csv) plus the 8 other directories directly under `Mouse Data` that are not in the inventory (Chewbacca, Diana, KAJ, Megamind, Tim, Tests, fakemouse, "Fluopulse pH test").

## Short answer

- **Scanned surgery sheets are not stored with the mouse.** No PDF/image with a surgery/sheet/scan/implant name or parent folder exists anywhere inside any `Mouse Data/<mouse>/` tree. All scans live in one lab-wide folder: `<share>/surgery/surgery notebook scan/`.
- **Surgery notes as text** exist as `Surgery Notes.txt` in 4 mouse folders (mouse root) plus one variant, `Mimi/Baseline/Mimi Surgery Notes.txt`.
- Of the 40 inventory mice: **8 have a scan matched by exact name, 2 more a probable scan matched by alias, 5 have notes only, 25 have nothing found.** "Nothing found" does not mean no sheet exists: 51 scans have numeric file names that cannot be tied to a mouse without opening them (see Unknowns).

## Where each kind sits

| Kind | Location | Pattern | Count | How verified |
|---|---|---|---|---|
| Scanned sheets | `<share>/surgery/surgery notebook scan/` (outside `Mouse Data`) | `<N>.pdf` (51 files) or `<name>.pdf` (25 files) | 76 PDFs | `find` + `ls`; `pdfinfo` reports 1 page for every one, producer string is a Xerox multifunction scanner |
| Blank template | `<share>/surgery/surgery_note_template.pdf` | single file | 1 | `ls` (name only; inferred to be a blank form, not opened) |
| One more PDF | `<share>/surgery/<person> surgeries/<name>.pdf` | subfolder named after a person, one PDF | 1 | `find`. File name is not in the mouse list. Purpose unknown |
| Surgery notes (text) | `Mouse Data/<mouse>/Surgery Notes.txt` | exact name, at mouse root | 4 (Felix, Gunther, Lex, Luther) | `find` over every mouse folder |
| Surgery notes (variant) | `Mouse Data/Mimi/Baseline/Mimi Surgery Notes.txt` | `<mouse> Surgery Notes.txt` inside `Baseline/` | 1 | same |

Facts about the folders:
- All 76 scan PDFs, the template and the extra PDF have modification date 2025-10-20 (`ls -l`; looks like a copy date). Nothing in `surgery/` is newer.
- The 5 notes files are dated 2026-03-30 (Felix, Gunther, Lex), 2026-04-16 (Mimi), 2026-05-18 (Luther). Sizes are 88-352 bytes (`ls -l`), i.e. very short.
- None of the 48 directories under `Mouse Data` has a `surgery`, `scan` or `implant` subfolder (full `find` of each, excluding avi/mp4/mat/smrx/s2rx).
- Across every mouse folder, about 1,380 files have an image/doc extension (png, jpg, jpeg, tif, tiff, heic, pdf, doc, docx; Lois1/Lois2/MJ1/MJ2 hold about 1,120 of them, all png). There are no pdf, tif, tiff or heic files at all; the jpg/png files seen by name are analysis figures, photometry summary PNGs, settings screenshots or rasters. A name search (surg, implant, sheet, scan, operat) over all non-video, non-mat file names returned only the 5 notes files and one unrelated Excel worksheet.

Numeric file names (51): 1, 2, 3, 4, 6, 10, 12-24, 30-33, 35, 36, 38-42, 44, 45, 47, 50, 52-63, 66, 70, 73-75 (with gaps). Probably an animal or notebook-page index rather than a mouse name. Inference only; no mapping to mice is recorded anywhere I could see.

Named file names (25): 10 match a mouse folder exactly (Beauty, Bob, Cannoli, CannoliGP, Clover, Jupyter1, Jupyter2, Katniss, Peter, Sprite), 3 look like aliases of a mouse folder (OktB, Oktoberfest, Optimusprime), 5 match animal folder names under `<share>/HMS SERVER FILES/` (Fuschia, Jack, Lazarus, Loki, Thor), and 7 match no folder found.

## Other lab-wide folders checked

`find -maxdepth 4` for names containing surg, implant, scan or notebook in every top-level folder of `<share>` (90 s timeout each, all completed):
- `HMS SERVER FILES`: no match (per-animal folders of an older cohort; no scans by name).
- `rig testing files from dropbox/2 Neural correlates of strategy/Mouse surgery data/`: one HEIC (fiber layout) and one pptx (surgery plan). Planning material, not per-mouse sheets.
- One former member's personal folder holds three text files on surgery steps and one cohort's surgery dates (a different project). Not relevant to the mouse list.
- `Histology`, `Mouse Onboarding Training`, `Resources`, `Qinxin Mice HMS` and the other personal folders: no match.
- `~snapshot/` is the server's read-only hourly backup and only duplicates the above.

## Per-mouse coverage (40 inventory mice)

"Scan (exact)" = `<mouse>.pdf` or `<mouse><n>.pdf` in the scan folder. "Scan (alias)" = name differs but plausibly the same mouse (inference).

| Status | Mice | n |
|---|---|---|
| Scan (exact name) | Beauty, Bob, Cannoli (2 files), Clover, Jupyter (2 files), Katniss, Peter, Sprite | 8 |
| Scan (alias, inferred) | OktoberfestB (OktB.pdf and/or Oktoberfest.pdf), Prime (Optimusprime.pdf) | 2 |
| Notes only | Felix, Gunther, Lex, Luther, Mimi | 5 |
| Nothing found | Amber, Big Cheese, Dachary, DonVito, Ezio, Hector, Jessie, Julia, Lois1, Lois2, Lois3, Marsha, MJ1, MJ2, MJ3, Peanut, Puffin, Ratthew, Round, Sashimi, Spencer, Sushi, TestHist1, TestHist2, Zlatan | 25 |

Total 8 + 2 + 5 + 25 = 40. Mice with any surgery record found by name: 15 of 40.
Scan and notes together: none (verified that Felix.pdf, Gunther.pdf, Lex.pdf, Luther.pdf, Mimi.pdf do not exist in the scan folder).

The 8 extra directories: none has a scan or notes by name. Tests, fakemouse and "Fluopulse pH test" are not animals; Chewbacca, Diana, KAJ, Megamind and Tim are animals with no surgery record by name.

### Multiple scans per mouse

Yes. Cannoli (Cannoli, CannoliGP) and Jupyter (Jupyter1, Jupyter2) have two files each; OktoberfestB may have two (OktB, Oktoberfest). Every PDF is exactly 1 page, so a multi-page or two-sided sheet would show up as several files with ad hoc suffixes (`GP`, `1`, `2`), not a fixed pattern.

## Facts vs inferences

Facts (verified by listing): the location table, counts of PDFs and text files, absence of surgery-named scans under `Mouse Data`, page counts, dates, sizes.

Inferences: that a named PDF is the sheet of the mouse with that name; that OktB/Oktoberfest/Optimusprime mean OktoberfestB/Prime; that numeric PDFs are not mouse names; that the template is a blank form.

## Unknowns

- What the 51 numeric PDFs are keyed on (animal number, notebook page, cage id). If they are sheets for mice in the "nothing found" list, real scan coverage is higher than 10 of 40. Needs a person or a mapping table.
- Whether the 7 unmatched named PDFs are mice that have no folder in `Mouse Data`.
- Whether "no surgery sheet" is a deliberate, confirmed state for any mouse. Nothing on the share records that.
- Contents of the 5 notes files (not opened by design): whether they are complete surgery records or short remarks (sizes suggest short).
- Purpose of the single PDF in the person-named subfolder.
- Whether mice that started after 2025-10-20 have any agreed place for a scan: the scan folder has had no additions since that date (mtime of every file).

## Implication for the surgery sheet status ticket

A `surgery_sheet_scans` path outside `Mouse Data` matches how files are stored today. A checker needs an explicit per-mouse mapping (mouse name to zero, one or several scan files, since multiple scans occur) and an explicit "no surgery sheet" marker, with unset/NaN meaning "not yet clarified". The folder layout alone cannot express "confirmed none", and the numeric scans cannot be matched to mice automatically.
