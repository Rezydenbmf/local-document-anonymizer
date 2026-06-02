# Module: TXT File Input and Output

## Purpose

This module implements Stage 2: reading UTF-8 TXT files, anonymizing their
content through the existing plain text engine, and saving a separate
anonymized TXT copy. TXT support remains unchanged after Stages 3 and 4.

## Related files

- `src/file_readers.py`
- `src/file_writers.py`
- `src/anonymizer.py`
- `tests/test_txt_io.py`

## Public API

```python
read_txt_file(file_path: str | Path) -> str
extract_text(file_path: str | Path) -> str
build_anonymized_txt_path(source_path: str | Path) -> Path
save_anonymized_txt_copy(source_path: str | Path, anonymized_text: str) -> Path
save_anonymized_copy(source_path: str | Path, anonymized_text: str) -> str
anonymize_txt_file(source_path: str | Path) -> tuple[Path, dict[str, int]]
```

## How it works

The TXT-specific helpers support only `.txt` files.

The file workflow is:

1. `read_txt_file()` reads the source file as UTF-8 text.
2. `anonymize_txt_file()` passes that text to `anonymize_text()`.
3. `save_anonymized_txt_copy()` writes the anonymized text as UTF-8.
4. The output file is saved next to the source with an `_ANON` suffix.

Example:

```text
document.txt -> document_ANON.txt
```

The original TXT file is not modified.

## Unsupported files

DOCX support is implemented separately in Stage 3 and documented in
`docs/modules/03_DOCX_IO.md`. Text-based PDF input is implemented separately in
Stage 4 and documented in `docs/modules/04_PDF_IO.md`.

GUI workflows, OCR, AI, APIs, cloud services, databases, batch processing, and
report files are not implemented.

TXT-specific helpers reject files without a `.txt` extension with a clear
`ValueError`.

## Safety assumptions

- TXT files are read and written locally.
- The original source file is left unchanged.
- The output file receives the `_ANON` suffix.
- No replacement map is created.
- No source values are written to reports or metadata.
- The integration helper returns only the output path and category counters.
- Counters contain category names and counts only.
- Tests use only synthetic data and temporary files.

## How to test

Run:

```bash
python -m unittest discover -s tests
```

The Stage 2 tests cover TXT reading, anonymized copy writing, original file
preservation, unsupported extension rejection, full TXT integration, and result
safety.

## Known limitations

- TXT-specific helpers still only accept `.txt` files.
- DOCX support exists in the separate Stage 3 DOCX workflow.
- Text-based PDF support exists in the separate Stage 4 PDF-to-TXT workflow.
- There is no GUI, OCR, AI, API integration, cloud service, database, batch
  processing, or final report file generation.
- Detection quality is still limited by the Stage 1 regex engine.
- Manual review is still required before trusting anonymized output.
