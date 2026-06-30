# Module: Approved Workspace Staging

## Purpose

This module documents Stage 17: approved workspace and knowledge-base staging.

The approved workspace is a local staging area for anonymized files that the
user has manually marked as `approved`. By itself, it is not a knowledge index
and it does not guarantee complete anonymization.

## Related files

- `src/review.py`
- `src/gui.py`
- `tests/test_review_workflow.py`
- `tests/test_gui_workflow.py`
- `docs/modules/11_MANUAL_REVIEW_WORKFLOW.md`
- `docs/modules/06_REPORTING.md`

## Public API

```python
build_approved_workspace_path(output_dir) -> Path
build_approved_index_path(approved_dir) -> Path
build_approved_index_text(...) -> str
export_approved_workspace(output_dir) -> ApprovedExportResult
```

## Export Rules

The export reads `_REVIEW_STATUS.json` from the selected output/review folder.
It exports only items whose saved manual status is `approved`.

It may copy:

- matching `_ANON` files marked `approved`,
- matching `_RAPORT` files when available.

It must not copy:

- original source documents,
- `needs_review` files,
- `rejected` files,
- `_BATCH_SUMMARY.txt`,
- `_REVIEW_STATUS.json`,
- `_REVIEW_SUMMARY.txt`,
- private dictionaries,
- logs or local configuration files.

The export never modifies source files or the original output workspace files.

## Output Files

The approved workspace is created inside the selected output/review folder:

```text
approved/
```

The workflow writes a safe index:

```text
approved/_APPROVED_INDEX.txt
```

If the approved folder already exists, it is reused. If a copied file or index
already exists, the workflow uses numbered collision-safe names:

```text
approved/document_ANON.txt
approved/document_ANON_2.txt
approved/document_RAPORT.txt
approved/document_RAPORT_2.txt
approved/_APPROVED_INDEX.txt
approved/_APPROVED_INDEX_2.txt
```

## Approved Index

`_APPROVED_INDEX.txt` may contain:

- export timestamp,
- number of approved anonymized files exported,
- number of reports copied,
- missing-report count,
- copied `_ANON` basenames,
- copied `_RAPORT` basenames,
- missing reports by approved output basename,
- safe risk levels when already available,
- statement that approval is a manual user decision,
- statement that the approved workspace is a staging area, not a guarantee of
  complete anonymization.

The index must not contain:

- document text,
- document excerpts,
- source personal data,
- private dictionary terms,
- dictionary aliases,
- full local paths,
- tracebacks,
- replacement maps,
- automatic approval claims,
- automatic knowledge-base claims.

Only basenames are allowed in the index.

## GUI Behavior

The manual review section provides an `Export approved` button. The button
uses the saved `_REVIEW_STATUS.json`; unsaved in-memory GUI status choices are
not treated as export decisions until review status is saved.

The GUI reports:

- number of approved `_ANON` files exported,
- number of matching reports copied,
- warning count when reports are missing,
- approved index filename,
- a clear message if `_REVIEW_STATUS.json` is missing,
- a clear message if there are no approved files,
- a safe failure message if export cannot complete.

The GUI does not preview, inspect, edit, validate, or approve document
contents.

## Safety Assumptions

- `approved` means a manual user decision.
- Approved workspace export is not automatic approval.
- Approved workspace export is staging only; Stage 22 knowledge indexes are
  generated separately from approved anonymized TXT files.
- Approved workspace export does not prove complete anonymization.
- Original files are never copied into the approved workspace.
- `needs_review` and `rejected` files are never copied into the approved
  workspace.
- The index uses safe basenames and metadata only.
- No OCR, AI/API, cloud service, local LLM, NER, database, preview, editor, or
  release packaging is added.

## How to Test

Run:

```bash
python -m unittest discover -s tests
```

Stage 17 tests cover reading `_REVIEW_STATUS.json`, detecting approved files,
exporting only approved `_ANON` files, skipping `needs_review`, skipping
`rejected`, optional copying of matching `_RAPORT`, missing `_RAPORT` handling,
missing `_REVIEW_STATUS.json`, no approved files, collision-safe approved
export, safe `_APPROVED_INDEX.txt` generation, and approved index safety.
Stage 18 tests cover approved export as part of the complete synthetic MVP
workflow and confirm only approved generated outputs are copied.

## Known Limitations

- This is a staging workflow only.
- It does not validate anonymized document contents.
- It does not create or manage a knowledge index by itself.
- It does not route `needs_review` or `rejected` files to separate folders.
- It does not guarantee complete anonymization.
- Manual review remains required before using or sharing any generated output.
