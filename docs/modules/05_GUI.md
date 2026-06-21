# Module: Simple Tkinter GUI

## Purpose

This module implements a small local Tkinter desktop interface for anonymizing
selected `.txt`, `.docx`, `.pdf`, or OCR-capable image files. Stage 6 extends the GUI status
area to show the saved report file path. Stage 8 adds optional private
sensitive terms file selection. Stage 9 adds safe post-anonymization audit
status and counters. Stage 10.1 keeps the GUI path-based for dictionaries and
shows safe dictionary status after the workflow runs. Stage 12 adds multiple
input file selection, output folder selection, sequential batch processing,
collision-safe output names, and a safe batch summary report. Stage 13 adds a
manual review section for loading an output folder, assigning manual statuses,
and saving safe review metadata. Stage 15 improves GUI usability with a
scrollable main layout, selected-file count, clear/remove actions for the GUI
input list, a readiness hint beside the anonymization button, clearer status
messages, and manual-review shortcuts for opening a selected generated output
or matching report with the operating system default application. Stage 16 adds
aggregate risk counts to the audit display and a safe risk column to the manual
review list. Stage 17 adds an `Export approved` action that creates an
approved staging workspace from saved manual review decisions. Stage 18
validates the complete GUI-backed MVP workflow with synthetic end-to-end tests
and a manual smoke checklist. Stage 19 adds minimal image-file selection and
safe aggregate OCR status display without redesigning the GUI.
Stage 20 adds one optional local NER checkbox and safe aggregate NER status
display without redesigning the GUI.

## Related files

- `src/gui.py`
- `src/main.py`
- `src/anonymizer.py`
- `src/review.py`
- `src/ocr.py`
- `src/ner.py`
- `src/sensitive_terms.py`
- `tests/test_gui_workflow.py`
- `tests/test_review_workflow.py`
- `tests/test_sensitive_terms.py`

## Public API

```python
start_gui() -> None
anonymize_file(source_path: str | Path, sensitive_terms=None, sensitive_terms_path=None, output_dir=None) -> tuple[Path, dict[str, int]]
anonymize_file_with_audit(source_path: str | Path, sensitive_terms=None, sensitive_terms_path=None, output_dir=None)
anonymize_batch(source_paths, output_dir, sensitive_terms=None, sensitive_terms_path=None)
load_review_workspace(output_dir)
save_review_files(output_dir, items, batch_summary_names=None)
export_approved_workspace(output_dir)
```

`start_gui()` opens the Tkinter application.

`anonymize_file(...)` is the Stage 5 single-file application dispatcher. Stage
12 adds optional output-directory support and the `anonymize_batch(...)`
workflow. These live in `src/anonymizer.py` and call the existing file
workflows:

- `anonymize_txt_file(...)`
- `anonymize_docx_file(...)`
- `anonymize_pdf_file(...)`
- `anonymize_image_file(...)`

The GUI does not parse TXT, DOCX, or PDF files itself and does not duplicate
anonymization logic.

## GUI behavior

The GUI supports this flow:

1. Open the application with `python src/main.py` or `python -m src.gui`.
2. Add one or more supported files and check the selected-file count.
3. Select an output folder.
4. Optionally select a private sensitive terms file. The GUI stores the path
   and the workflow loads the dictionary.
5. Leave `Use local NER if available` checked to request local NER, or uncheck
   it for dictionary/regex-only processing.
6. Check the readiness hint if `Anonymize batch` is disabled.
7. Click `Anonymize batch`.
8. Review the status, safe dictionary status, category counters, aggregate
   audit status counts, aggregate risk counts, aggregate OCR/NER status,
   generated output filenames, generated report filenames, batch summary
   filename, and manual review warning.
9. Manually inspect every anonymized output file before using or sharing it.
10. Load the output folder in the manual review section.
11. Optionally open the selected `_ANON` output or matching `_RAPORT` report in
   the operating system default application.
12. Assign each generated output one manual status: `approved`,
   `needs_review`, or `rejected`.
13. Save `_REVIEW_STATUS.json` and a collision-safe `_REVIEW_SUMMARY.txt`.
14. Optionally click `Export approved` to copy approved `_ANON` files into
    `approved/` and write `_APPROVED_INDEX.txt`.

`Remove selected` and `Clear files` affect only the GUI selected-file list.
They do not delete source files from disk.

The GUI shows:

- selected input filenames,
- selected input file count,
- anonymization readiness: missing input files, missing output folder, or ready
  file count,
- selected output folder status,
- safe dictionary status,
- operation status,
- category counters,
- post-anonymization audit status counts,
- post-anonymization risk level counts,
- aggregate audit warning categories,
- aggregate OCR status counts,
- aggregate NER status counts,
- output filenames,
- report filenames and batch summary filename,
- generated output filenames detected for manual review,
- risk level for review items when paired Stage 16 reports are present,
- report filenames paired with review items when present,
- manual review statuses,
- clear status messages when selected generated outputs or reports are opened
  or missing,
- review status and summary filenames after save,
- approved workspace export counts and approved index filename,
- missing-report warnings during approved export,
- clear errors from unsupported file types or PDFs without extractable text,
- clear controlled errors when local OCR dependencies or Tesseract are
  unavailable,
- clear errors when `_REVIEW_STATUS.json` is missing or no approved files
  exist,
- a reminder that manual review is required.

The readiness hint updates when input files are added, removed, or cleared, when
an output folder is selected, and when dictionary selection changes the current
GUI state. It does not display document contents, source values, private
dictionary terms, or full local paths.

Dictionary status values shown by the GUI are:

- `not selected`: no dictionary path was provided.
- `loaded`: the selected dictionary loaded successfully.
- `invalid`: the selected dictionary could not be loaded or parsed.
- `loaded; matches found: no`: the dictionary loaded but no dictionary terms
  were replaced.

## Supported inputs and outputs

TXT input:

```text
output folder / document_ANON.txt
output folder / document_RAPORT.txt
```

DOCX input:

```text
output folder / document_ANON.docx
output folder / document_RAPORT.txt
```

Text-based PDF input:

```text
output folder / document_ANON.txt
output folder / document_RAPORT.txt
```

OCR image input:

```text
output folder / scan_ANON.txt
output folder / scan_RAPORT.txt
```

Original files are not modified.

Batch run:

```text
output folder / _BATCH_SUMMARY.txt
```

Manual review run:

```text
output folder / _REVIEW_STATUS.json
output folder / _REVIEW_SUMMARY.txt
```

Approved workspace export:

```text
output folder / approved / document_ANON.txt
output folder / approved / document_RAPORT.txt
output folder / approved / _APPROVED_INDEX.txt
```

If a generated file already exists, the workflow uses a numbered safe name such
as `document_ANON_2.txt`. Review summaries use numbered safe names such as
`_REVIEW_SUMMARY_2.txt` when a previous summary exists.
Approved workspace exports use the same numbered safe names for copied files
and approved indexes.

## Safety assumptions

- The GUI processes selected files sequentially.
- The GUI displays category names and counts only.
- The GUI displays audit status counts, risk counts, and audit category counts
  only.
- The GUI displays OCR status counts only.
- The GUI displays NER status counts only.
- The GUI displays dictionary status names and safe match metadata only.
- The GUI does not display original detected source values.
- The GUI does not display private dictionary contents.
- The GUI does not display private dictionary terms or audit text snippets.
- The GUI displays generated filenames, not report contents or source values.
- The GUI displays manual review item filenames, safe risk levels, and statuses
  only.
- The GUI can ask the operating system to open a selected generated output or
  matching report, but it does not preview or inspect those files itself.
- `approved` is a manual user decision, not an automatic application decision.
- No replacement map is created.
- Safe report files are created by the existing file workflow helpers.
- A safe batch summary is created by the batch workflow.
- Safe review status and summary files are created by the review workflow.
- Approved workspace files and the approved index are created by the review
  workflow from saved manual decisions.
- The approved workspace is a staging area only, not a knowledge base or
  guarantee of complete anonymization.
- No source data is logged.
- OCR and NER are optional and local; no AI, API, cloud service, database,
  drag and drop, preview, editing, edited image output, or PDF writing is
  added.

## How to test

Run:

```bash
python -m unittest discover -s tests
```

The Stage 5 test covers the non-Tk single-file integration dispatcher using
synthetic TXT data and unsupported extension handling. Stage 6 report creation
is covered by `tests/test_report.py`. Stage 8 dictionary integration is covered
by `tests/test_sensitive_terms.py`. Stage 9 audit metadata safety is covered by
`tests/test_gui_workflow.py` and `tests/test_audit.py`. Stage 12 batch/output
workspace behavior is covered by `tests/test_batch_processing.py`. Stage 13
manual review metadata is covered by `tests/test_review_workflow.py`. Stage 15
selected-file count, anonymization readiness helper text, list removal, safe
batch status, and missing external file open handling are covered by
`tests/test_gui_workflow.py`. Stage 16 risk display helpers are covered by
`tests/test_gui_workflow.py` and `tests/test_review_workflow.py`. Stage 17
approved export helper text is covered by `tests/test_gui_workflow.py`, and
approved export behavior is covered by `tests/test_review_workflow.py`. Stage
18 end-to-end workflow coverage is in `tests/test_stage18_end_to_end.py`.
Stage 19 OCR GUI-adjacent status formatting is covered by
`tests/test_ocr.py` and `tests/test_gui_workflow.py`. Stage 20 NER status
formatting is covered by `tests/test_ner.py` and `tests/test_gui_workflow.py`.
Fragile widget tests are not included.

## Known limitations

- The GUI has no document preview or editing view.
- External open buttons delegate to the operating system default application;
  they do not add an in-app viewer or validator.
- The GUI can select one private dictionary file path but does not manage,
  edit, validate before run, or display its contents.
- The GUI audit display is a warning summary only and does not prove complete
  anonymization.
- Risk counts and per-file risk levels are review-prioritization hints only.
- The manual review section tracks statuses only and does not inspect,
  validate, preview, edit, or automatically approve generated document
  contents.
- Approved export copies manually approved outputs into a staging folder only;
  it does not validate contents or create a knowledge base.
- OCR requires optional local dependencies and Tesseract; the GUI does not
  install or configure those dependencies.
- NER requires optional local spaCy dependencies and a local Polish model; the
  GUI does not install, download, or configure those dependencies.
- The GUI does not support drag and drop, preview, split-screen review,
  highlighting, edited image output, or anonymized PDF output.
- DOCX and PDF limitations from Stages 3 and 4 still apply.
- Manual review remains required before trusting any anonymized result.
