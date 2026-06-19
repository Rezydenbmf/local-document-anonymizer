# Module: Manual Review Workflow

## Purpose

This module documents Stage 13: safe manual review status tracking for output
folders created by batch processing.

Stage 13 helps the user organize generated anonymized outputs after the batch
workflow. It distinguishes between generated files, manually approved files,
files that still need review or correction, and rejected files. It does not
approve files automatically and does not replace human review.

Stage 16 lets the workflow read safe risk levels from paired `_RAPORT.txt`
files so higher-risk generated outputs can be reviewed first. This remains
metadata only and does not inspect document contents.

Stage 17 adds approved workspace export from saved review decisions. It reads
`_REVIEW_STATUS.json`, copies only `_ANON` files marked `approved` into an
`approved/` staging folder, optionally copies matching `_RAPORT` files, and
writes a safe `_APPROVED_INDEX.txt` manifest. This is not automatic approval
and not a guarantee of complete anonymization.

## Related files

- `src/review.py`
- `src/gui.py`
- `tests/test_review_workflow.py`
- `docs/modules/05_GUI.md`
- `docs/modules/06_REPORTING.md`

## Public API

```python
detect_review_workspace(output_dir) -> ReviewWorkspace
load_review_workspace(output_dir) -> ReviewWorkspace
apply_review_statuses(items, statuses_by_output_name) -> list[ReviewItem]
build_review_status_payload(...) -> dict[str, object]
build_review_summary_text(...) -> str
save_review_status_file(...) -> Path
save_review_summary_file(...) -> Path
save_review_files(...) -> ReviewSaveResult
export_approved_workspace(output_dir) -> ApprovedExportResult
```

## Review Items

Each review item represents one generated `_ANON` output file. The stored item
metadata is intentionally small:

- generated anonymized output basename,
- matching report basename when present,
- safe risk level from a paired Stage 16 report when present,
- missing-report state when no report is paired,
- manual status.

The supported manual statuses are:

- `approved`,
- `needs_review`,
- `rejected`.

`approved` means the user manually approved the file. It does not mean the
application guaranteed complete anonymization.

## Detection Rules

The workflow scans an output folder for generated anonymized files:

```text
document_ANON.txt
document_ANON.docx
document_ANON_2.txt
```

It pairs matching report files when present:

```text
document_RAPORT.txt
document_RAPORT_2.txt
```

It also records safe batch summary basenames such as:

```text
_BATCH_SUMMARY.txt
_BATCH_SUMMARY_2.txt
```

The workflow uses basenames only. It does not store full paths.

When a paired report is present, the workflow reads only the safe `Risk level:`
line and accepts only `ok`, `warning`, or `high_risk`. Missing, unreadable, or
pre-Stage-16 reports leave the risk level unknown. Review items are sorted by
risk priority first: `high_risk`, then `warning`, then `ok`, then unknown.

## Output Files

Saving review metadata writes:

```text
_REVIEW_STATUS.json
_REVIEW_SUMMARY.txt
```

`_REVIEW_STATUS.json` is the latest status manifest for the output folder.
`_REVIEW_SUMMARY.txt` is collision-safe. If a summary already exists, a
numbered summary is written:

```text
_REVIEW_SUMMARY_2.txt
_REVIEW_SUMMARY_3.txt
```

Stage 17 approved workspace export writes:

```text
approved/
approved/document_ANON.txt
approved/document_RAPORT.txt
approved/_APPROVED_INDEX.txt
```

If a copied file or approved index already exists, the workflow uses numbered
safe names such as `document_ANON_2.txt`, `document_RAPORT_2.txt`, or
`_APPROVED_INDEX_2.txt`.

## Safety Rules

Review metadata may contain:

- generated output basenames,
- report basenames,
- safe risk levels,
- batch summary basenames,
- manual status values,
- status counts,
- timestamp,
- manual review completed yes/no.

Approved workspace index metadata may contain:

- export timestamp,
- copied approved `_ANON` basenames,
- copied `_RAPORT` basenames,
- missing-report basenames by approved output basename,
- safe risk levels when already available,
- copied counts,
- manual-decision and staging disclaimers.

Review metadata must not contain:

- source document contents,
- anonymized document contents,
- document excerpts,
- original sensitive values,
- private dictionary terms,
- dictionary aliases,
- replacement maps,
- full local paths,
- tracebacks,
- automatic approval claims.
- source risk evidence beyond the safe risk level.

The workflow does not open generated documents to inspect their contents. It
only scans filenames in the selected output folder.

Approved workspace export must not copy original source documents,
`needs_review` files, or `rejected` files. The approved workspace is a staging
area only; it is not a knowledge base.

## GUI Behavior

The GUI provides a manual review section that can:

1. Select an output folder.
2. Load detected generated outputs.
3. Show output basename, risk level, report basename or `missing`, and manual
   status.
4. Sort `high_risk` items first when safe risk metadata is available.
5. Open the selected generated output with the operating system default
   application.
6. Open the matching report with the operating system default application when
   one is detected.
7. Assign `approved`, `needs_review`, or `rejected` to one or more selected
   rows.
8. Save the review status and summary files.
9. Export files marked `approved` into the approved workspace after review
   status has been saved.

The GUI does not show full document content, report content, dictionary
contents, source values, audit snippets, or replacement maps.

The open actions are convenience shortcuts only. They do not inspect document
contents, validate anonymization, edit files, move files, or approve anything
automatically.

The export action reports the number of approved `_ANON` files exported, the
number of reports copied, missing-report warnings when applicable, a clear
message if `_REVIEW_STATUS.json` is missing, a clear message if there are no
approved files, and a safe failure message if export cannot complete.

## How to Test

Run:

```bash
python -m unittest discover -s tests
```

Stage 13 tests cover generated output detection, report pairing, missing report
handling, supported statuses, safe `_REVIEW_STATUS.json`, safe
`_REVIEW_SUMMARY.txt`, collision-safe review summary naming, Stage 12 batch
output regression, and report/audit regression. Stage 16 tests cover safe risk
level parsing from reports, high-risk-first ordering, and risk metadata in the
safe review summary. Stage 17 tests cover approved export from
`_REVIEW_STATUS.json`, skipping `needs_review` and `rejected`, optional report
copying, missing reports, missing status files, no approved files,
collision-safe export names, and safe approved index contents. Stage 18 tests
cover the full workflow chain from synthetic batch outputs to manual decisions
and approved export.

## Known Limitations

- Status tracking only.
- Risk sorting is based on safe report metadata only and is not a guarantee of
  complete anonymization.
- No document preview or editor.
- No document-content inspection or validation.
- External file opening is delegated to the operating system default
  application and is not an in-app preview.
- No automatic approval based on audit results.
- No file moving into needs-review or rejected folders.
- Approved workspace export is copying into a staging area only; it is not a
  knowledge base and does not validate document contents.
- No OCR, AI, API calls, cloud services, local LLMs, NER, or database.
- Manual review remains required before using or sharing any generated output.
