# Module: Text-Based PDF Input and TXT Output

## Purpose

This module implements Stage 4: local text extraction from text-based PDF
files, anonymization through the existing plain text engine, and saving the
anonymized result as a TXT file. Stage 6 adds safe report file output after
successful anonymization. Stage 8 lets the workflow receive optional private
sensitive terms. Stage 9 audits the anonymized PDF-to-TXT output before saving
the safe report. Stage 10.1 lets the workflow receive a dictionary path and
report safe dictionary status. Stage 12 lets the workflow write to a selected
output folder with collision-safe names. Stage 19 keeps text-based extraction
first and adds optional local OCR fallback only when a PDF has no extractable
text layer.

## Related files

- `src/file_readers.py`
- `src/file_writers.py`
- `src/anonymizer.py`
- `src/ocr.py`
- `src/sensitive_terms.py`
- `tests/test_pdf_io.py`
- `tests/test_ocr.py`
- `tests/test_sensitive_terms.py`

## Runtime dependency

Stage 4 adds one runtime dependency:

```text
pypdf
```

The dependency is used locally to read extractable text from PDF files. Stage
19 can optionally use local OCR dependencies for scanned PDFs, but it does not
add internet calls, APIs, cloud services, AI, local LLMs, databases, or
batch-specific PDF logic.

## Public API

```python
read_pdf_file(file_path: str | Path) -> str
extract_text(file_path: str | Path) -> str
build_anonymized_pdf_txt_path(source_path: str | Path) -> Path
build_report_path(source_path: str | Path) -> Path
save_anonymized_pdf_txt_copy(source_path: str | Path, anonymized_text: str, output_dir=None) -> Path
anonymize_pdf_file(source_path: str | Path, sensitive_terms=None, sensitive_terms_path=None, output_dir=None) -> tuple[Path, dict[str, int]]
anonymize_pdf_file_with_audit(source_path: str | Path, sensitive_terms=None, sensitive_terms_path=None, output_dir=None)
```

`anonymize_pdf_file(...)` passes extracted PDF text through the existing
`anonymize_text(text: str, sensitive_terms=None)` engine. Stage 4 does not
create separate PDF-specific anonymization regex logic.

## How it works

The PDF workflow is:

1. `read_pdf_file()` extracts text from a local `.pdf` file with `pypdf`.
2. If no extractable text is found, Stage 19 attempts local OCR when optional
   dependencies are available.
3. `anonymize_pdf_file()` loads an optional dictionary path and passes the
   extracted text to `anonymize_text()`.
4. `save_anonymized_pdf_txt_copy()` writes the anonymized text as UTF-8 TXT.
5. The output file is saved with an `_ANON.txt` suffix, in the selected output
   folder when one is provided.
6. `audit_text()` checks the anonymized TXT output.
7. A safe report file is saved with a `_RAPORT.txt` suffix. The report includes
   safe dictionary status, label counters, and OCR metadata only.

Example:

```text
output folder / document_ANON.txt
output folder / document_RAPORT.txt
```

The original PDF file is not modified. Existing generated files are not
overwritten silently; numbered names are used when needed.

## Scanned PDFs and OCR

Stage 4 supports PDFs that already contain an extractable text layer. Stage 19
adds optional scanned-PDF fallback after that path fails.

If OCR dependencies or the local Tesseract engine are unavailable, the workflow
returns a controlled OCR status/error. It does not silently pretend that a
scanned PDF was processed.

The PDF workflow still does not support:

- PDF layout preservation,
- anonymized PDF output,
- handwritten text extraction.

## Safety assumptions

- PDF files are read locally.
- The original source PDF is left unchanged.
- PDF input produces TXT output only.
- Scanned PDF OCR is optional and local.
- No anonymized PDF file is created.
- The safe report file receives the `_RAPORT.txt` suffix.
- Generated files can be written to a selected output folder.
- Existing generated files are not overwritten silently.
- No replacement map is created.
- No source values are written to reports, metadata, or counters.
- The integration helper returns only the output path and category counters.
- Counters contain category names and counts only.
- Private dictionary terms are not written to reports, counters, or returned
  metadata.
- Dictionary workflow metadata contains only status names, labels, and
  counters.
- OCR metadata contains only used/status/input-type/page-count/warning fields.
- Audit results contain only status, category counters, and the manual review
  flag. They do not contain source values, snippets, dictionary terms, raw OCR
  text, or a replacement map.
- Tests use only generated synthetic temporary PDFs.

## How to test

Run:

```bash
python -m unittest discover -s tests
```

The Stage 4 tests cover reading a simple text-based PDF, rejecting PDFs without
extractable text at the reader layer, writing `_ANON.txt` output, preserving
the original PDF, PDF-to-TXT anonymization integration, safe counters without
source values, and the absence of `_ANON.pdf` output. Stage 19 tests cover
text-based PDF non-OCR regression, mocked scanned-PDF OCR fallback, and
controlled OCR-unavailable batch behavior.

## Known limitations

- Detection quality is still limited by the Stage 1 regex engine.
- Private dictionary matching is deterministic, case-insensitive, and
  whitespace-tolerant, but not fuzzy matching or automatic entity detection.
- Extracted PDF text may not preserve visual layout or reading order.
- Scanned PDF OCR requires optional local OCR dependencies and Tesseract.
- OCR can be inaccurate and must be manually reviewed.
- No anonymized PDF output is created.
- PDF input still writes `document_ANON.txt`, but Stage 12 collision-safe
  naming prevents silent overwrites in the output folder.
- Stage 9 audit checks only the extracted anonymized TXT output.
- Manual review is still required before trusting or sharing anonymized output.
