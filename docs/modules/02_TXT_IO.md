# Module: TXT File Input and Output

## Purpose

This module implements Stage 2: reading UTF-8 TXT files, anonymizing their
content through the existing plain text engine, and saving a separate
anonymized TXT copy. Stage 6 reuses the TXT workflow and adds safe report file
output after successful anonymization. Stage 8 lets the workflow receive
optional private sensitive terms. Stage 9 audits the anonymized TXT output
before saving the safe report. Stage 10.1 lets the workflow receive a
dictionary path and report safe dictionary status. Stage 12 lets the workflow
write to a selected output folder with collision-safe names.

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
save_anonymized_txt_copy(source_path: str | Path, anonymized_text: str, output_dir=None) -> Path
save_anonymized_copy(source_path: str | Path, anonymized_text: str, output_dir=None) -> str
anonymize_txt_file(source_path: str | Path, sensitive_terms=None, sensitive_terms_path=None, output_dir=None) -> tuple[Path, dict[str, int]]
anonymize_txt_file_with_audit(source_path: str | Path, sensitive_terms=None, sensitive_terms_path=None, output_dir=None)
```

## How it works

The TXT-specific helpers support only `.txt` files.

The file workflow is:

1. `read_txt_file()` reads the source file as UTF-8 text.
2. `anonymize_txt_file()` loads an optional dictionary path and passes that
   text to `anonymize_text()` with optional private sensitive terms.
3. `save_anonymized_txt_copy()` writes the anonymized text as UTF-8.
4. The output file is saved with an `_ANON` suffix, in the selected output
   folder when one is provided.
5. `audit_text()` checks the anonymized output text and returns safe audit
   metadata.
6. A safe report file is saved with a `_RAPORT.txt` suffix. The report includes
   safe dictionary status and label counters only.

Example:

```text
output folder / document_ANON.txt
output folder / document_RAPORT.txt
```

The original TXT file is not modified. Existing generated files are not
overwritten silently; numbered names are used when needed.

## Unsupported files

DOCX support is implemented separately in Stage 3 and documented in
`docs/modules/03_DOCX_IO.md`. Text-based PDF input is implemented separately in
Stage 4 and documented in `docs/modules/04_PDF_IO.md`.

The GUI can call the TXT workflow through the Stage 12 batch workflow. OCR, AI,
APIs, cloud services, databases, drag and drop, preview, and editing are not
implemented.

TXT-specific helpers reject files without a `.txt` extension with a clear
`ValueError`.

## Safety assumptions

- TXT files are read and written locally.
- The original source file is left unchanged.
- The output file receives the `_ANON` suffix.
- The safe report file receives the `_RAPORT.txt` suffix.
- Generated files can be written to a selected output folder.
- Existing generated files are not overwritten silently.
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
dictionary handling, and loaded-without-matches report output. Stage 12 tests
cover output workspace behavior and collision-safe names.

## Known limitations

- TXT-specific helpers still only accept `.txt` files.
- DOCX support exists in the separate Stage 3 DOCX workflow.
- Text-based PDF support exists in the separate Stage 4 PDF-to-TXT workflow.
- There is no OCR, AI, API integration, cloud service, database, drag and drop,
  preview, editing, or detailed audit report generation with source snippets.
- Detection quality is still limited by the Stage 1 regex engine.
- Audit quality is limited by conservative Stage 9 regex checks.
- Manual review is still required before trusting anonymized output.
