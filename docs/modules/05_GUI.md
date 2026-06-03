# Module: Simple Tkinter GUI

## Purpose

This module implements Stage 5: a small local Tkinter desktop interface for
anonymizing one selected `.txt`, `.docx`, or `.pdf` file.

## Related files

- `src/gui.py`
- `src/main.py`
- `src/anonymizer.py`
- `tests/test_gui_workflow.py`

## Public API

```python
start_gui() -> None
anonymize_file(source_path: str | Path) -> tuple[Path, dict[str, int]]
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

The Stage 5 GUI supports this flow:

1. Open the application with `python src/main.py`.
2. Select one file.
3. Click `Anonymize`.
4. Review the status, category counters, output path, and manual review warning.
5. Manually inspect the anonymized output file before using or sharing it.

The GUI shows:

- selected file path,
- operation status,
- category counters,
- output file path,
- clear errors from unsupported file types or PDFs without extractable text,
- a reminder that manual review is required.

## Supported inputs and outputs

TXT input:

```text
document.txt -> document_ANON.txt
```

DOCX input:

```text
document.docx -> document_ANON.docx
```

Text-based PDF input:

```text
document.pdf -> document_ANON.txt
```

Original files are not modified.

## Safety assumptions

- The GUI processes one selected file only.
- The GUI displays category names and counts only.
- The GUI does not display original detected source values.
- No replacement map is created.
- No report file is created in Stage 5.
- No source data is logged.
- No OCR, AI, API, cloud service, database, drag and drop, batch processing, or
  PDF writing is added.

## How to test

Run:

```bash
python -m unittest discover -s tests
```

The Stage 5 test covers the non-Tk single-file integration dispatcher using
synthetic TXT data and unsupported extension handling. Fragile widget tests are
not included.

## Known limitations

- The GUI has no document preview or editing view.
- The GUI does not support batch processing, drag and drop, OCR, scanned PDFs,
  or anonymized PDF output.
- DOCX and PDF limitations from Stages 3 and 4 still apply.
- Manual review remains required before trusting any anonymized result.
