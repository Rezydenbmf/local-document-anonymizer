# Project State

## Current Status

The project is in Stage 10.1: manual validation fixes.

The Stage 0-10.1 MVP implementation contains a narrow regex-based engine that
accepts a Python string and returns anonymized text plus category counters. It
also contains optional private exact-term dictionary support, TXT file readers
and writers, basic DOCX readers and writers, text-based PDF text extraction,
small integration helpers for saving separate anonymized TXT, DOCX, and
PDF-to-TXT outputs, a simple Tkinter GUI for anonymizing one selected supported
file, safe TXT report generation without source values, and a safe
post-anonymization audit with category counters only.

Stage 10.1 fixes manual validation findings around the private dictionary flow.
The GUI stores the selected dictionary path, the workflow loads it centrally,
reports include safe dictionary status and label counters, and the audit checks
remaining dictionary terms when a dictionary loaded successfully. It does not
add OCR, AI, cloud services, APIs, local LLMs, databases, batch processing,
automatic replacement-map generation, source-value logging, or automatic
deletion of originals.

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
- Private sensitive terms parsing and replacement in `src/sensitive_terms.py`.
- Post-anonymization audit in `src/audit.py`.
- Optional `sensitive_terms_path` arguments in the TXT, DOCX, PDF, and
  single-file dispatcher workflows, while the plain text engine still accepts
  preloaded `sensitive_terms`.
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
- Unit tests for Stage 8 private dictionary parsing, replacement order,
  integration, and report safety using synthetic values only.
- Unit tests for Stage 9 post-anonymization audit detection, report safety,
  workflow integration, and GUI/dispatcher audit metadata safety using
  synthetic values only.
- Unit tests for Stage 10.1 dictionary path flow, dictionary report status,
  invalid dictionary handling, loaded-without-matches status, and TXT/DOCX/PDF
  dictionary-path compatibility using synthetic values only.
- Synthetic sample text files in `tests/sample_data/`.
- Synthetic example dictionary in `examples/sensitive_terms.example.txt`.
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
- Detailed report generation beyond safe counters, safe audit metadata, and
  manual review notes.
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
- TXT outputs are written next to the source with an `_ANON` suffix.
- DOCX outputs are written next to the source with an `_ANON` suffix.
- PDF input is extracted as text and saved as `_ANON.txt`; no anonymized PDF is
  created.
- TXT and PDF inputs with the same base name in the same folder can still
  create confusing or colliding `_ANON.txt` and `_RAPORT.txt` paths. Stage 10.1
  documents this limitation rather than adding a new output folder workflow.
- Reports contain only safe metadata, category counters, and manual review
  notices. They do not contain source values, full input paths, filenames,
  dictionary source terms, or replacement maps.
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
- Private dictionary matching is literal and case-sensitive. It is useful for
  exact user-specified terms, but it is not automatic entity recognition.
- The real private dictionary must stay outside git, either outside the
  repository or inside an ignored folder such as `private/`.
- Post-anonymization audit matching is conservative and regex-based. It can
  miss sensitive data and can warn on harmless text.
- Audit status `ok` does not prove complete anonymization. Manual review is
  still required.
- Audit results and reports include only categories and counters, never source
  values, snippets, dictionary terms, full document text, or replacement maps.

## Last Completed Committed Stage

Stage 9: post-anonymization audit.

Last committed implementation before the Stage 10.1 working tree:

```text
782eee1 Implement Stage 9 post-anonymization audit
```

Current working tree stage:

```text
Stage 10.1: manual validation fixes
```

## Next Logical Step

After Stage 10.1 review, the safest next step is a small implementation commit
for the manual validation fixes. Later work should stay separate and require an
explicit project decision, especially OCR, batch processing, installer work,
better NLP, stronger entity detection, packaging, or release automation.

## Warning

This repository is still an early-stage portfolio MVP. Do not use it to
anonymize real documents without manual review and project-specific safety
checks.
