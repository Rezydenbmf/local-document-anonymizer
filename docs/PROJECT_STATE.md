# Project State

## Current Status

The project is in Stage 15: GUI usability cleanup.

The Stage 0-13 MVP implementation contains a narrow regex-based engine that
accepts a Python string and returns anonymized text plus category counters. It
also contains optional private dictionary support with aliases,
case-insensitive matching, and whitespace-tolerant term matching, TXT file
readers and writers, basic DOCX readers and writers, text-based PDF text
extraction, small integration helpers for saving separate anonymized TXT, DOCX,
and PDF-to-TXT outputs, a simple Tkinter GUI for anonymizing selected
supported files into a chosen output folder, safe TXT report generation without
source values, a safe post-anonymization audit with category counters only,
batch processing, and manual review status tracking for generated output
folders.

Stage 10.1 fixes manual validation findings around the private dictionary flow.
The GUI stores the selected dictionary path, the workflow loads it centrally,
reports include safe dictionary status and label counters, and the audit checks
remaining dictionary terms when a dictionary loaded successfully. It did not
add OCR, AI, cloud services, APIs, local LLMs, databases, batch processing,
automatic replacement-map generation, source-value logging, or automatic
deletion of originals.

Stage 10.2 manually confirmed the Stage 10.1 dictionary fix with a GUI smoke
test using small synthetic UTF-8 files.

Stage 11 kept the existing local workflow and improved the private dictionary
foundation. Dictionary lines can contain multiple aliases separated by `|`,
matching is case-insensitive, excessive internal whitespace is tolerated, and
longer aliases are still applied before shorter aliases. Reports, GUI status,
audit metadata, and counters continue to expose labels and counts only.

Stage 12 adds a safe output workspace and batch processing. The GUI now lets
the user select multiple supported files and an output folder. `_ANON`,
`_RAPORT`, and `_BATCH_SUMMARY` files are written to that output folder with
collision-safe numbered names. Batch processing is sequential; an error for one
file is recorded in a safe form and does not stop later files. The batch
summary stores safe filenames, aggregate counters, audit status counts, and
controlled error descriptions only.

Stage 13 adds a manual review workflow for existing output folders. The app
detects generated `_ANON` files, pairs matching `_RAPORT` files when present,
lists `_BATCH_SUMMARY` files when present, lets the user mark outputs as
`approved`, `needs_review`, or `rejected`, and saves safe
`_REVIEW_STATUS.json` and collision-safe `_REVIEW_SUMMARY.txt` metadata.
`approved` is a manual user decision, not an automatic application decision,
and the workflow does not show, inspect, or store document contents.

Stage 15 improves the existing Tkinter GUI usability without changing the core
anonymization engine. The window is resizable with a smaller minimum size and a
scrollable main layout, the input selection is shown as a removable list with a
readable selected-file count, selected inputs can be cleared from the GUI
without deleting files, the anonymization button has a visible readiness hint
that explains missing input files or output folder, review statuses can be
applied to multiple selected review rows, and the manual review section can
open the selected generated `_ANON` output or matching `_RAPORT` report with
the operating system default application. The GUI still does not preview,
inspect, edit, or validate document contents inside the app.

## What Exists

- Repository structure.
- Regex-based plain text anonymization in `src/anonymizer.py`.
- Supported Stage 1 categories: `PESEL`, `EMAIL`, `TELEFON`, and `DATA`.
- UTF-8 TXT reading in `src/file_readers.py`.
- UTF-8 TXT anonymized copy writing in `src/file_writers.py`.
- TXT integration helper `anonymize_txt_file(...)`.
- Basic local DOCX paragraph and simple table text reading in
  `src/file_readers.py`.
- Basic DOCX anonymized copy writing in `src/file_writers.py`.
- DOCX integration helper `anonymize_docx_file(...)`.
- Text-based PDF extraction in `src/file_readers.py`.
- PDF integration helper `anonymize_pdf_file(...)`, which saves anonymized PDF
  text as `_ANON.txt`.
- Single-file application dispatcher `anonymize_file(...)`, with optional
  output directory support.
- Batch workflow `anonymize_batch(...)`.
- Simple Tkinter GUI in `src/gui.py` for selecting multiple input files, an
  output folder, an optional private dictionary, and an output folder for
  manual review status tracking.
- Scrollable Tkinter GUI layout with a readable selected-file count.
- GUI actions to remove selected inputs or clear the input list without
  deleting files from disk.
- GUI readiness hint that explains whether input files or an output folder are
  still needed before anonymization can start.
- Manual review GUI actions to open a selected `_ANON` output or matching
  `_RAPORT` report with the operating system default application.
- Default GUI entry point in `src/main.py`.
- Safe report text generation in `src/report.py`.
- Report path helper `build_report_path(...)`, which can target the selected
  output folder.
- Collision-safe path helper for `_ANON`, `_RAPORT`, and `_BATCH_SUMMARY`
  outputs.
- Private sensitive terms parsing and replacement in `src/sensitive_terms.py`.
- Dictionary alias parsing with `alias | alias = [LABEL]` support.
- Case-insensitive and whitespace-tolerant private dictionary matching.
- Post-anonymization audit in `src/audit.py`.
- Optional `sensitive_terms_path` arguments in the TXT, DOCX, PDF, and
single-file dispatcher and batch workflows, while the plain text engine still
accepts preloaded `sensitive_terms`.
- `_with_audit` TXT, DOCX, PDF, and dispatcher helpers that return safe audit
  metadata while existing helpers keep their Stage 2-5 return shape.
- Optional GUI selection of a private sensitive terms file path without
  displaying dictionary contents.
- GUI display of post-anonymization audit status and category counters only.
- GUI display of safe dictionary status: not selected, loaded, invalid, or
  loaded with no dictionary matches.
- Safe report counters for dictionary labels only.
- Safe report dictionary section with used/status/matches-found metadata.
- Safe report section for post-anonymization audit status and counters only.
- Shared dictionary matching semantics for anonymization and audit dictionary
  checks.
- TXT, DOCX, PDF, and dispatcher flows that create safe reports after
  successful anonymization.
- Batch summary report generation with safe filenames and no private paths.
- Manual review workflow in `src/review.py` for detecting generated `_ANON`
  outputs, pairing safe report basenames, applying manual statuses, and saving
  safe review metadata.
- GUI support for assigning `approved`, `needs_review`, or `rejected` statuses
  without previewing or editing document contents.
- Safe `_REVIEW_STATUS.json` review manifest output.
- Collision-safe `_REVIEW_SUMMARY.txt` review summary output.
- Runtime dependency on `python-docx`.
- Runtime dependency on `pypdf`.
- Unit tests for the Stage 1 anonymizer using synthetic values only.
- Unit tests for Stage 2 TXT input/output using synthetic temporary files only.
- Unit tests for Stage 3 DOCX input/output using synthetic temporary files only.
- Unit tests for Stage 4 text-based PDF input/output using generated
  synthetic temporary PDFs only.
- Unit tests for the Stage 5 single-file dispatcher using synthetic temporary
  TXT files only.
- Unit tests for Stage 6 safe report generation and TXT/DOCX/PDF report
  integration using synthetic temporary files only.
- Unit tests for Stage 8 private dictionary parsing, replacement order,
  integration, and report safety using synthetic values only.
- Unit tests for Stage 9 post-anonymization audit detection, report safety,
  workflow integration, and GUI/dispatcher audit metadata safety using
  synthetic values only.
- Unit tests for Stage 10.1 dictionary path flow, dictionary report status,
  invalid dictionary handling, loaded-without-matches status, and TXT/DOCX/PDF
  dictionary-path compatibility using synthetic values only.
- Unit tests for Stage 11 dictionary aliases, backward compatibility,
  case-insensitive matching, whitespace normalization, longer aliases before
  shorter aliases, label-only counters, safe alias reports, and audit
  dictionary matching using synthetic values only.
- Unit tests for Stage 12 collision-safe naming, output workspace behavior,
  batch TXT/DOCX/PDF processing, safe error continuation, and safe batch
  summary content using synthetic values only.
- Unit tests for Stage 13 generated output detection, report pairing, missing
  report handling, manual statuses, safe review status JSON, safe review
  summary text, collision-safe review summary naming, Stage 12 regression, and
  report/audit regression using synthetic values only.
- Synthetic sample text files in `tests/sample_data/`.
- Synthetic example dictionary in `examples/sensitive_terms.example.txt`.
- Synthetic seed dictionary example in `examples/sensitive_terms.seed.example.txt`.
- Synthetic manual-review candidate file in
  `examples/dictionary_candidates.example.txt`.
- Project, user, security, roadmap, and module documentation.
- `.gitignore` rules for private data and local artifacts.
- Stage 7 portfolio/release review documentation updates for README quality,
  user guidance, technical flow clarity, roadmap status, security assumptions,
  and honest portfolio text.

## What Does Not Exist Yet

- Advanced GUI preview or editing workflow.
- Drag and drop.
- OCR, AI, API calls, cloud services, local LLMs, or databases.
- Detailed report generation beyond safe counters, safe audit metadata, and
  manual review notes.
- Automatic approval based on audit results or report contents.
- Moving reviewed files into approved/rejected folders.
- Automatic names, surnames, cities, organizations, or context-based detection.
- Anonymized PDF output.
- Scanned PDF processing.

## How to Run

Run the GUI entry point:

```bash
python src/main.py
```

Run tests:

```bash
python -m unittest discover -s tests
```

## Current Limitations

- The core engine processes only a plain Python string.
- File input/output supports `.txt` files, basic `.docx` files, and
  text-based `.pdf` input.
- TXT outputs are written to the selected output folder with an `_ANON` suffix.
- DOCX outputs are written to the selected output folder with an `_ANON` suffix.
- PDF input is extracted as text and saved as `_ANON.txt`; no anonymized PDF is
  created.
- Existing output files are not overwritten silently; numbered suffixes such as
  `_2` and `_3` are used when needed.
- Batch processing is sequential and records per-file errors in the safe batch
  summary.
- Per-file reports contain only safe metadata, category counters, and manual
  review notices. They do not contain source values, full input paths,
  filenames, dictionary source aliases or terms, or replacement maps.
- Date detection is limited to high-confidence numeric formats.
- Phone detection is intentionally conservative.
- Address and postal-code detection are not implemented in Stage 1.
- DOCX formatting preservation is basic only.
- DOCX headers, footers, comments, footnotes, form fields, text in images, and
  advanced elements are not handled.
- PDF support requires an existing text layer. Scanned PDFs are not supported,
  OCR is not included, and PDF layout preservation is not guaranteed.
- The GUI processes selected files sequentially and does not include document
  preview, editing, or drag and drop.
- The manual review workflow tracks statuses only. It does not inspect,
  validate, preview, edit, or automatically approve anonymized document
  contents. Opening a selected output or report delegates to the operating
  system default application and does not add an in-app viewer.
- Review status and summary files contain safe generated basenames and status
  counts only, not full paths, source data, document excerpts, private
  dictionary terms, aliases, tracebacks, or replacement maps.
- Report files are plain TXT only and do not include a detailed audit trail.
- Private dictionary matching is deterministic, case-insensitive, and tolerant
  of extra internal spaces, but it is not fuzzy matching, inflection handling,
  automatic entity recognition, OCR, AI, or NER.
- The real private dictionary must stay outside git, either outside the
  repository or inside an ignored folder such as `private/`.
- Post-anonymization audit matching is conservative and regex-based. It can
  miss sensitive data and can warn on harmless text.
- Audit status `ok` does not prove complete anonymization. Manual review is
  still required.
- Audit results and reports include only categories and counters, never source
  values, snippets, dictionary terms, full document text, or replacement maps.

## Last Completed Committed Stage

Stage 12: safe output workspace and batch processing.

```text
e19d87c Implement Stage 12 batch output workspace
```

## Next Logical Step

Manually smoke test Stage 15 through the Tkinter GUI with synthetic files in a
local output folder: resizing/scrolling, selected-file count, clear/remove
actions, disabled-button readiness messages, batch run status messages, and
opening selected `_ANON`/`_RAPORT` files from manual review. Potential future
work requires an explicit project
decision, especially OCR, installer work, better NLP, stronger entity
detection, packaging, or release automation.

## Warning

This repository is still an early-stage portfolio MVP. Do not use it to
anonymize real documents without manual review and project-specific safety
checks.
