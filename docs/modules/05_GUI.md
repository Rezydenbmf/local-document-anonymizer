# Module: Simple Tkinter GUI

## Purpose

This module implements a small local Tkinter desktop interface for anonymizing
one selected `.txt`, `.docx`, or `.pdf` file. Stage 6 extends the GUI status
area to show the saved report file path. Stage 8 adds optional private
sensitive terms file selection.

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
anonymize_file(source_path: str | Path, sensitive_terms=None) -> tuple[Path, dict[str, int]]
```

`start_gui()` opens the Tkinter application.

`anonymize_file(...)` is the Stage 5 single-file application dispatcher. It
lives in `src/anonymizer.py` and calls the existing file workflows:

- `anonymize_txt_file(...)`
- `anonymize_docx_file(...)`
- `anonymize_pdf_file(...)`

The GUI does not parse TXT, DOCX, or PDF files itself and does not duplicate
anonymization logic.

## GUI behavior

The GUI supports this flow:

1. Open the application with `python src/main.py`.
2. Select one file.
3. Optionally select a private sensitive terms file.
4. Click `Anonymize`.
5. Review the status, category counters, output path, report path, and manual review warning.
6. Manually inspect the anonymized output file before using or sharing it.

The GUI shows:

- selected file path,
- whether a sensitive terms file is selected,
- operation status,
- category counters,
- output file path,
- report file path,
- clear errors from unsupported file types or PDFs without extractable text,
- a reminder that manual review is required.

## Supported inputs and outputs

TXT input:

```text
document.txt -> document_ANON.txt
document.txt -> document_RAPORT.txt
```

DOCX input:

```text
document.docx -> document_ANON.docx
document.docx -> document_RAPORT.txt
```

Text-based PDF input:

```text
document.pdf -> document_ANON.txt
document.pdf -> document_RAPORT.txt
```

Original files are not modified.

## Safety assumptions

- The GUI processes one selected file only.
- The GUI displays category names and counts only.
- The GUI does not display original detected source values.
- The GUI does not display private dictionary contents.
- The GUI displays report paths only, not report contents or source values.
- No replacement map is created.
- Safe report files are created by the existing file workflow helpers.
- No source data is logged.
- No OCR, AI, API, cloud service, database, drag and drop, batch processing, or
  PDF writing is added.

## How to test

Run:

```bash
python -m unittest discover -s tests
```

The Stage 5 test covers the non-Tk single-file integration dispatcher using
synthetic TXT data and unsupported extension handling. Stage 6 report creation
is covered by `tests/test_report.py`. Stage 8 dictionary integration is covered
by `tests/test_sensitive_terms.py`. Fragile widget tests are not included.

## Known limitations

- The GUI has no document preview or editing view.
- The GUI can select one private dictionary file but does not manage, edit, or
  display its contents.
- The GUI does not support batch processing, drag and drop, OCR, scanned PDFs,
  or anonymized PDF output.
- DOCX and PDF limitations from Stages 3 and 4 still apply.
- Manual review remains required before trusting any anonymized result.
