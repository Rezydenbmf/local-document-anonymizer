# Project State

## Current Status

The project is in Stage 7: portfolio polish and release review.

The Stage 0-6 MVP implementation contains a narrow regex-based engine that
accepts a Python string and returns anonymized text plus category counters. It
also contains TXT file readers and writers, basic DOCX readers and writers,
text-based PDF text extraction, small integration helpers for saving separate
anonymized TXT, DOCX, and PDF-to-TXT outputs, a simple Tkinter GUI for
anonymizing one selected supported file, and safe TXT report generation without
source values.

Stage 7 is a documentation, safety, test, and portfolio review stage. It does
not add application features or change the MVP scope.

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
- Safe report text generation in `src/report.py`.
- Report path helper `build_report_path(...)`, which saves `_RAPORT.txt`
  reports next to anonymized outputs.
- TXT, DOCX, PDF, and dispatcher flows that create safe reports after
  successful anonymization.
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
- Synthetic sample text files in `tests/sample_data/`.
- Project, user, security, roadmap, and module documentation.
- `.gitignore` rules for private data and local artifacts.
- Stage 7 portfolio/release review documentation updates for README quality,
  user guidance, technical flow clarity, roadmap status, security assumptions,
  and honest portfolio text.

## What Does Not Exist Yet

- Advanced GUI preview or editing workflow.
- Batch processing.
- Drag and drop.
- OCR, AI, API calls, cloud services, local LLMs, or databases.
- Detailed report generation beyond safe counters and metadata.
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
- Reports contain only safe metadata, category counters, and manual review
  notices. They do not contain source values, full input paths, filenames, or
  replacement maps.
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
- Report files are plain TXT only and do not include a detailed audit trail.

## Last Completed Stage

Stage 6: safe report file output.

Last implementation commit:

```text
decc8ad Implement Stage 6 safe report output
```

Current review stage:

```text
Stage 7: portfolio polish and release review
```

## Next Logical Step

After Stage 7 review, the safest next step is user review and a small
documentation-only commit. Later work should stay separate and require an
explicit project decision, especially OCR, batch processing, installer work,
better NLP, stronger entity detection, packaging, or release automation.

## Warning

This repository is still an early-stage portfolio MVP. Do not use it to
anonymize real documents without manual review and project-specific safety
checks.
