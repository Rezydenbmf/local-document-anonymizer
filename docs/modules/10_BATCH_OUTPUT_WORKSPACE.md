# Module: Batch Output Workspace

## Purpose

This module documents Stage 12: safe output workspace and batch processing.

Stage 12 lets the user select multiple supported files and one output folder.
All generated `_ANON`, `_RAPORT`, and `_BATCH_SUMMARY` files are written to
that output folder instead of next to the source files. Generated names are
collision-safe, so existing files are not silently overwritten.

## Related files

- `src/anonymizer.py`
- `src/file_writers.py`
- `src/report.py`
- `src/gui.py`
- `tests/test_batch_processing.py`

## Public API

```python
anonymize_file(source_path, sensitive_terms=None, sensitive_terms_path=None, output_dir=None)
anonymize_file_with_audit(source_path, sensitive_terms=None, sensitive_terms_path=None, output_dir=None)
anonymize_batch(source_paths, output_dir, sensitive_terms=None, sensitive_terms_path=None)
build_collision_safe_path(candidate_path)
build_batch_summary_path(output_dir)
build_batch_summary_text(...)
save_batch_summary_file(...)
```

The existing single-file helpers keep their original return shapes. Stage 12
adds optional `output_dir` arguments so callers can send generated files to a
chosen output workspace.

`anonymize_batch(...)` returns safe batch metadata including the summary path,
input count, success count, error count, aggregate counters, audit status
counts, risk level counts, aggregate audit category counters, and per-file
result entries using filenames only.

## Output Workspace

The output folder is selected by the user in the GUI. The workflow writes:

```text
document.txt  -> document_ANON.txt  + document_RAPORT.txt
document.docx -> document_ANON.docx + document_RAPORT.txt
document.pdf  -> document_ANON.txt  + document_RAPORT.txt
batch run     -> _BATCH_SUMMARY.txt
```

Only generated output goes to the selected output folder. Source files are not
modified.

## Collision-Safe Naming

Before writing a generated file, the workflow checks whether the target path
already exists. If it does, the next numbered name is used:

```text
document_ANON.txt
document_ANON_2.txt
document_ANON_3.txt
```

The same rule applies to `_RAPORT.txt` reports and `_BATCH_SUMMARY.txt` batch
summary reports.

## Batch Processing

Batch processing is sequential. Each input path is processed through the same
TXT, DOCX, or text-based PDF workflow used by the single-file dispatcher.

If one file fails, the batch continues with later files. Unsupported files are
recorded as safe errors. Runtime errors are converted to controlled safe error
descriptions before they enter the batch summary.

## Batch Summary Report

The `_BATCH_SUMMARY.txt` report may contain:

- number of input files,
- number of successful files,
- number of errors,
- aggregate category counters,
- audit status counts,
- risk level counts,
- aggregate audit warning category counters,
- safe input filenames,
- safe generated output filenames,
- safe generated report filenames,
- controlled safe error descriptions,
- manual review requirement.

The batch summary must not contain:

- source document text,
- original sensitive values,
- private dictionary terms,
- dictionary aliases,
- replacement maps,
- full source paths,
- full output paths,
- raw exception messages,
- logs or snippets.

## GUI Behavior

The GUI now supports this Stage 12 flow:

1. Select one or more supported input files.
2. Select an output folder.
3. Optionally select a private dictionary file.
4. Run `Anonymize batch`.
5. Review the completion status, aggregate counters, aggregate audit status,
   aggregate risk levels, output filenames, report filenames, and batch summary
   filename.
6. Manually review every generated anonymized output.

The GUI shows safe filenames and counts. It does not show source values,
dictionary contents, audit snippets, or raw exception text.

## Safety Assumptions

- Processing remains local and offline.
- No OCR, AI, API, cloud service, local LLM, NER, or database is added.
- No drag and drop, document preview, or editor is added.
- Original files are not modified.
- Reports do not store replacement maps.
- Batch errors are sanitized before being written to `_BATCH_SUMMARY.txt`.
- Risk levels are prioritization metadata only and do not approve files.
- Manual review remains required for every generated output.

## How to Test

Run:

```bash
python -m unittest discover -s tests
```

Stage 12 tests cover collision-safe naming, output workspace behavior,
sequential batch processing across TXT/DOCX/text-based PDF, safe continuation
after unsupported files, and safe batch summary contents. Stage 16 tests cover
aggregate risk counts, aggregate audit category counters, and source-value-safe
risk metadata in the batch summary. Stage 18 tests cover batch output as part
of the complete MVP chain through manual review and approved export.

## Known Limitations

- Batch processing is sequential only.
- The GUI does not show a per-file progress table.
- The batch summary is a plain TXT report.
- Risk counts and audit warning categories are conservative review hints only.
- The batch summary uses safe filenames, but filenames themselves should still
  be chosen carefully by the user.
- Manual review is still required.
