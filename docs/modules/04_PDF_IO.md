# Module: Text-Based PDF Input and TXT Output

## Purpose

This module implements Stage 4: local text extraction from text-based PDF
files, anonymization through the existing plain text engine, and saving the
anonymized result as a TXT file.

## Related files

- `src/file_readers.py`
- `src/file_writers.py`
- `src/anonymizer.py`
- `tests/test_pdf_io.py`

## Runtime dependency

Stage 4 adds one runtime dependency:

```text
pypdf
```

The dependency is used locally to read extractable text from PDF files. It does
not add internet calls, APIs, cloud services, AI, OCR, local LLMs, databases, or
batch processing.

## Public API

```python
read_pdf_file(file_path: str | Path) -> str
extract_text(file_path: str | Path) -> str
build_anonymized_pdf_txt_path(source_path: str | Path) -> Path
save_anonymized_pdf_txt_copy(source_path: str | Path, anonymized_text: str) -> Path
anonymize_pdf_file(source_path: str | Path) -> tuple[Path, dict[str, int]]
```

`anonymize_pdf_file(...)` passes extracted PDF text through the existing
`anonymize_text(text: str)` engine. Stage 4 does not create separate
PDF-specific anonymization regex logic.

## How it works

The PDF workflow is:

1. `read_pdf_file()` extracts text from a local `.pdf` file with `pypdf`.
2. `anonymize_pdf_file()` passes that text to `anonymize_text()`.
3. `save_anonymized_pdf_txt_copy()` writes the anonymized text as UTF-8 TXT.
4. The output file is saved next to the source with an `_ANON.txt` suffix.

Example:

```text
document.pdf -> document_ANON.txt
```

The original PDF file is not modified.

## Unsupported PDFs

Stage 4 supports only PDFs that already contain an extractable text layer. If a
PDF has no extractable text, the reader raises a clear `ValueError`.

Stage 4 does not support:

- scanned PDFs,
- OCR,
- PDF layout preservation,
- anonymized PDF output,
- image text extraction,
- handwritten text extraction.

## Safety assumptions

- PDF files are read locally.
- The original source PDF is left unchanged.
- PDF input produces TXT output only.
- No anonymized PDF file is created.
- No replacement map is created.
- No source values are written to reports, metadata, or counters.
- The integration helper returns only the output path and category counters.
- Counters contain category names and counts only.
- Tests use only generated synthetic temporary PDFs.

## How to test

Run:

```bash
python -m unittest discover -s tests
```

The Stage 4 tests cover reading a simple text-based PDF, rejecting PDFs without
extractable text, writing `_ANON.txt` output, preserving the original PDF,
PDF-to-TXT anonymization integration, safe counters without source values, and
the absence of `_ANON.pdf` output.

## Known limitations

- Detection quality is still limited by the Stage 1 regex engine.
- Extracted PDF text may not preserve visual layout or reading order.
- Scanned PDFs are not supported.
- OCR is not included.
- No anonymized PDF output is created.
- Manual review is still required before trusting or sharing anonymized output.
