# Module: Text-Based PDF Input and TXT Output

## Purpose

This module implements Stage 4: local text extraction from text-based PDF
files, anonymization through the existing plain text engine, and saving the
anonymized result as a TXT file. Stage 6 adds safe report file output after
successful anonymization. Stage 8 lets the workflow receive optional private
sensitive terms. Stage 9 audits the anonymized PDF-to-TXT output before saving
the safe report.

## Related files

- `src/file_readers.py`
- `src/file_writers.py`
- `src/anonymizer.py`
- `src/sensitive_terms.py`
- `tests/test_pdf_io.py`
- `tests/test_sensitive_terms.py`

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
build_report_path(source_path: str | Path) -> Path
save_anonymized_pdf_txt_copy(source_path: str | Path, anonymized_text: str) -> Path
anonymize_pdf_file(source_path: str | Path, sensitive_terms=None) -> tuple[Path, dict[str, int]]
anonymize_pdf_file_with_audit(source_path: str | Path, sensitive_terms=None)
```

`anonymize_pdf_file(...)` passes extracted PDF text through the existing
`anonymize_text(text: str, sensitive_terms=None)` engine. Stage 4 does not
create separate PDF-specific anonymization regex logic.

## How it works

The PDF workflow is:

1. `read_pdf_file()` extracts text from a local `.pdf` file with `pypdf`.
2. `anonymize_pdf_file()` passes that text to `anonymize_text()`.
3. `save_anonymized_pdf_txt_copy()` writes the anonymized text as UTF-8 TXT.
4. The output file is saved next to the source with an `_ANON.txt` suffix.
5. `audit_text()` checks the anonymized TXT output.
6. A safe report file is saved next to the output with a `_RAPORT.txt` suffix.

Example:

```text
document.pdf -> document_ANON.txt
document.pdf -> document_RAPORT.txt
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
- The safe report file receives the `_RAPORT.txt` suffix.
- No replacement map is created.
- No source values are written to reports, metadata, or counters.
- The integration helper returns only the output path and category counters.
- Counters contain category names and counts only.
- Private dictionary terms are not written to reports, counters, or returned
  metadata.
- Audit results contain only status, category counters, and the manual review
  flag. They do not contain source values, snippets, dictionary terms, or a
  replacement map.
- Tests use only generated synthetic temporary PDFs.

## How to test

Run:

```bash
python -m unittest discover -s tests
```

The Stage 4 tests cover reading a simple text-based PDF, rejecting PDFs without
extractable text, writing `_ANON.txt` output, preserving the original PDF,
PDF-to-TXT anonymization integration, safe counters without source values, and
the absence of `_ANON.pdf` output. Stage 9 tests cover audit report safety and
dispatcher audit metadata.

## Known limitations

- Detection quality is still limited by the Stage 1 regex engine.
- Private dictionary matching is literal and case-sensitive.
- Extracted PDF text may not preserve visual layout or reading order.
- Scanned PDFs are not supported.
- OCR is not included.
- No anonymized PDF output is created.
- Stage 9 audit checks only the extracted anonymized TXT output and does not
  add OCR or scanned PDF support.
- Manual review is still required before trusting or sharing anonymized output.
