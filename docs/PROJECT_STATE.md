# Project State

## Current Status

The project is in Stage 5: simple Tkinter GUI.

The repository now contains a narrow regex-based engine that accepts a Python
string and returns anonymized text plus category counters. It also contains
TXT file readers and writers, basic DOCX readers and writers, text-based PDF
text extraction, small integration helpers for saving separate anonymized TXT,
DOCX, and PDF-to-TXT outputs, and a simple Tkinter GUI for anonymizing one
selected supported file.

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
- Single-file application dispatcher `anonymize_file(...)`.
- Simple Tkinter GUI in `src/gui.py`.
- Default GUI entry point in `src/main.py`.
- Runtime dependency on `python-docx`.
- Runtime dependency on `pypdf`.
- Unit tests for the Stage 1 anonymizer using synthetic values only.
- Unit tests for Stage 2 TXT input/output using synthetic temporary files only.
- Unit tests for Stage 3 DOCX input/output using synthetic temporary files only.
- Unit tests for Stage 4 text-based PDF input/output using generated
  synthetic temporary PDFs only.
- Unit tests for the Stage 5 single-file dispatcher using synthetic temporary
  TXT files only.
- Synthetic sample text files in `tests/sample_data/`.
- Project, user, security, roadmap, and module documentation.
- `.gitignore` rules for private data and local artifacts.

## What Does Not Exist Yet

- Advanced GUI preview or editing workflow.
- Batch processing.
- Drag and drop.
- OCR, AI, API calls, cloud services, local LLMs, or databases.
- Final report file generation.
- Names, surnames, cities, organizations, or context-based detection.
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
- TXT outputs are written next to the source with an `_ANON` suffix.
- DOCX outputs are written next to the source with an `_ANON` suffix.
- PDF input is extracted as text and saved as `_ANON.txt`; no anonymized PDF is
  created.
- Reports contain only category counters and no source values.
- Date detection is limited to high-confidence numeric formats.
- Phone detection is intentionally conservative.
- Address and postal-code detection are not implemented in Stage 1.
- DOCX formatting preservation is basic only.
- DOCX headers, footers, comments, footnotes, form fields, text in images, and
  advanced elements are not handled.
- PDF support requires an existing text layer. Scanned PDFs are not supported,
  OCR is not included, and PDF layout preservation is not guaranteed.
- The GUI processes one selected file at a time and does not include document
  preview, editing, drag and drop, or batch processing.
- Report files remain unimplemented.

## Last Completed Stage

Stage 5: simple Tkinter GUI.

## Next Logical Step

Stage 6: safe report file generation without source values.

## Warning

This repository is still an early-stage tool. Do not use it to anonymize real
documents without manual review and without completing the later file workflow
and safety checks.
