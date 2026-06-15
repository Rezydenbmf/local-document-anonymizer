# Module: Simple Tkinter GUI

## Purpose

This module implements a small local Tkinter desktop interface for anonymizing
selected `.txt`, `.docx`, or `.pdf` files. Stage 6 extends the GUI status
area to show the saved report file path. Stage 8 adds optional private
sensitive terms file selection. Stage 9 adds safe post-anonymization audit
status and counters. Stage 10.1 keeps the GUI path-based for dictionaries and
shows safe dictionary status after the workflow runs. Stage 12 adds multiple
input file selection, output folder selection, sequential batch processing,
collision-safe output names, and a safe batch summary report.

## Related files

- `src/gui.py`
- `src/main.py`
- `src/anonymizer.py`
- `src/sensitive_terms.py`
- `tests/test_gui_workflow.py`
- `tests/test_sensitive_terms.py`

## Public API

```python
start_gui() -> None
anonymize_file(source_path: str | Path, sensitive_terms=None, sensitive_terms_path=None, output_dir=None) -> tuple[Path, dict[str, int]]
anonymize_file_with_audit(source_path: str | Path, sensitive_terms=None, sensitive_terms_path=None, output_dir=None)
anonymize_batch(source_paths, output_dir, sensitive_terms=None, sensitive_terms_path=None)
```

`start_gui()` opens the Tkinter application.

`anonymize_file(...)` is the Stage 5 single-file application dispatcher. Stage
12 adds optional output-directory support and the `anonymize_batch(...)`
workflow. These live in `src/anonymizer.py` and call the existing file
workflows:

- `anonymize_txt_file(...)`
- `anonymize_docx_file(...)`
- `anonymize_pdf_file(...)`

The GUI does not parse TXT, DOCX, or PDF files itself and does not duplicate
anonymization logic.

## GUI behavior

The GUI supports this flow:

1. Open the application with `python src/main.py`.
2. Select one or more supported files.
3. Select an output folder.
4. Optionally select a private sensitive terms file. The GUI stores the path
   and the workflow loads the dictionary.
5. Click `Anonymize batch`.
6. Review the status, safe dictionary status, category counters, aggregate
   audit status counts, generated output filenames, generated report
   filenames, batch summary filename, and manual review warning.
7. Manually inspect every anonymized output file before using or sharing it.

The GUI shows:

- selected input filenames,
- selected output folder status,
- safe dictionary status,
- operation status,
- category counters,
- post-anonymization audit status counts,
- output filenames,
- report filenames and batch summary filename,
- clear errors from unsupported file types or PDFs without extractable text,
- a reminder that manual review is required.

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

Original files are not modified.

Batch run:

```text
output folder / _BATCH_SUMMARY.txt
```

If a generated file already exists, the workflow uses a numbered safe name such
as `document_ANON_2.txt`.

## Safety assumptions

- The GUI processes selected files sequentially.
- The GUI displays category names and counts only.
- The GUI displays audit status counts only.
- The GUI displays dictionary status names and safe match metadata only.
- The GUI does not display original detected source values.
- The GUI does not display private dictionary contents.
- The GUI does not display private dictionary terms or audit text snippets.
- The GUI displays generated filenames, not report contents or source values.
- No replacement map is created.
- Safe report files are created by the existing file workflow helpers.
- A safe batch summary is created by the batch workflow.
- No source data is logged.
- No OCR, AI, API, cloud service, database, drag and drop, preview, editing, or
  PDF writing is added.

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
workspace behavior is covered by `tests/test_batch_processing.py`. Fragile
widget tests are not included.

## Known limitations

- The GUI has no document preview or editing view.
- The GUI can select one private dictionary file path but does not manage,
  edit, validate before run, or display its contents.
- The GUI audit display is a warning summary only and does not prove complete
  anonymization.
- The GUI does not support drag and drop, OCR, scanned PDFs, or anonymized PDF
  output.
- DOCX and PDF limitations from Stages 3 and 4 still apply.
- Manual review remains required before trusting any anonymized result.
