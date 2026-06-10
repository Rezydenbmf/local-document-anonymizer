# Module: TXT File Input and Output

## Purpose

This module implements Stage 2: reading UTF-8 TXT files, anonymizing their
content through the existing plain text engine, and saving a separate
anonymized TXT copy. Stage 6 reuses the TXT workflow and adds safe report file
output after successful anonymization. Stage 8 lets the workflow receive
optional private sensitive terms. Stage 9 audits the anonymized TXT output
before saving the safe report. Stage 10.1 lets the workflow receive a
dictionary path and report safe dictionary status.

## Related files

- `src/file_readers.py`
- `src/file_writers.py`
- `src/anonymizer.py`
- `src/sensitive_terms.py`
- `tests/test_txt_io.py`
- `tests/test_sensitive_terms.py`

## Public API

```python
read_txt_file(file_path: str | Path) -> str
extract_text(file_path: str | Path) -> str
build_anonymized_txt_path(source_path: str | Path) -> Path
build_report_path(source_path: str | Path) -> Path
save_anonymized_txt_copy(source_path: str | Path, anonymized_text: str) -> Path
save_anonymized_copy(source_path: str | Path, anonymized_text: str) -> str
anonymize_txt_file(source_path: str | Path, sensitive_terms=None, sensitive_terms_path=None) -> tuple[Path, dict[str, int]]
anonymize_txt_file_with_audit(source_path: str | Path, sensitive_terms=None, sensitive_terms_path=None)
```

## How it works

The TXT-specific helpers support only `.txt` files.

The file workflow is:

1. `read_txt_file()` reads the source file as UTF-8 text.
2. `anonymize_txt_file()` loads an optional dictionary path and passes that
   text to `anonymize_text()` with optional private sensitive terms.
3. `save_anonymized_txt_copy()` writes the anonymized text as UTF-8.
4. The output file is saved next to the source with an `_ANON` suffix.
5. `audit_text()` checks the anonymized output text and returns safe audit
   metadata.
6. A safe report file is saved next to the output with a `_RAPORT.txt` suffix.
   The report includes safe dictionary status and label counters only.

Example:

```text
document.txt -> document_ANON.txt
document.txt -> document_RAPORT.txt
```

The original TXT file is not modified.

## Unsupported files

DOCX support is implemented separately in Stage 3 and documented in
`docs/modules/03_DOCX_IO.md`. Text-based PDF input is implemented separately in
Stage 4 and documented in `docs/modules/04_PDF_IO.md`.

The Stage 5 GUI can call the TXT workflow for one selected file. Stage 6 also
shows the saved report path. OCR, AI, APIs, cloud services, databases, and
batch processing are not implemented.

TXT-specific helpers reject files without a `.txt` extension with a clear
`ValueError`.

## Safety assumptions

- TXT files are read and written locally.
- The original source file is left unchanged.
- The output file receives the `_ANON` suffix.
- The safe report file receives the `_RAPORT.txt` suffix.
- No replacement map is created.
- No source values are written to reports or metadata.
- The integration helper returns only the output path and category counters.
- Counters contain category names and counts only.
- Private dictionary terms are not written to reports, counters, or returned
  metadata.
- Dictionary workflow metadata contains only status names, labels, and
  counters.
- Audit results contain only status, category counters, and the manual review
  flag. They do not contain source values, snippets, dictionary terms, or a
  replacement map.
- Tests use only synthetic data and temporary files.

## How to test

Run:

```bash
python -m unittest discover -s tests
```

The Stage 2 tests cover TXT reading, anonymized copy writing, original file
preservation, unsupported extension rejection, full TXT integration, and result
safety. Stage 9 tests cover TXT workflow audit metadata through report and
dispatcher integration. Stage 10.1 tests cover dictionary path status, invalid
dictionary handling, and loaded-without-matches report output.

## Known limitations

- TXT-specific helpers still only accept `.txt` files.
- DOCX support exists in the separate Stage 3 DOCX workflow.
- Text-based PDF support exists in the separate Stage 4 PDF-to-TXT workflow.
- The Stage 5 GUI supports one selected file only.
- There is no OCR, AI, API integration, cloud service, database, batch
  processing, or detailed audit report generation with source snippets.
- Detection quality is still limited by the Stage 1 regex engine.
- Audit quality is limited by conservative Stage 9 regex checks.
- Manual review is still required before trusting anonymized output.
