# Module: PDF Input, TXT Output, and Review PDF Output

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
text layer. Stage 24 makes the default PDF review artifact an original-layout
`_ANON_VISUAL.pdf` created from detected full-word text coordinates with true
PyMuPDF redaction annotations. `_ANON_REVIEW.pdf` remains an auxiliary rebuilt
review PDF generated from anonymized text only. The legacy text-search
original-layout workflow remains available only as explicit experimental
`_ORIGINAL_REDACTED.pdf` output.

## Related files

- `src/file_readers.py`
- `src/file_writers.py`
- `src/anonymizer.py`
- `src/pdf_redaction.py`
- `src/ocr.py`
- `src/sensitive_terms.py`
- `tests/test_pdf_io.py`
- `tests/test_ocr.py`
- `tests/test_sensitive_terms.py`

## Runtime dependency

Stage 4 adds one runtime dependency and Stage 23 uses the existing PyMuPDF
dependency:

```text
pypdf
PyMuPDF
```

`pypdf` is used locally to read extractable text from PDF files. PyMuPDF is
used locally for true redaction of text-based PDF output. Stage 19 can
optionally use local OCR dependencies for scanned PDFs, but Stage 23 does not
add scanned-PDF bounding-box redaction, internet calls, APIs, cloud services,
AI, local LLMs, databases, or broad PDF editor behavior.

## Public API

```python
read_pdf_file(file_path: str | Path) -> str
extract_text(file_path: str | Path) -> str
build_anonymized_pdf_txt_path(source_path: str | Path) -> Path
build_pdf_visual_path(source_path: str | Path) -> Path
build_pdf_review_path(source_path: str | Path) -> Path
build_original_redacted_pdf_path(source_path: str | Path) -> Path
build_report_path(source_path: str | Path) -> Path
save_anonymized_pdf_txt_copy(source_path: str | Path, anonymized_text: str, output_dir=None) -> Path
save_word_coordinate_redacted_pdf_copy(source_path, word_pages, spans, output_dir=None) -> dict[str, object]
save_rebuilt_review_pdf_from_text(source_path, anonymized_text, page_texts=None, output_dir=None) -> dict[str, object]
save_redacted_pdf_copy(source_path, sensitive_terms=None, extra_redaction_terms=None, output_dir=None) -> dict[str, object]
anonymize_pdf_file(source_path: str | Path, sensitive_terms=None, sensitive_terms_path=None, output_dir=None, pdf_output_mode="visual_redaction", pdf_redaction_scope="safe") -> tuple[Path, dict[str, int]]
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
3. `anonymize_pdf_file()` loads an optional dictionary path, applies
   deterministic replacements, and optionally applies local NER.
4. `save_anonymized_pdf_txt_copy()` writes the anonymized text as UTF-8 TXT.
5. By default, `save_word_coordinate_redacted_pdf_copy()` creates
   `_ANON_VISUAL.pdf` from detected spans mapped to full PDF word rectangles.
6. `save_rebuilt_review_pdf_from_text()` creates auxiliary `_ANON_REVIEW.pdf`
   from anonymized text only, with simple source-page headers and wrapped
   lines.
7. If the experimental original-layout mode is explicitly selected,
   `save_redacted_pdf_copy()` creates `_ORIGINAL_REDACTED.pdf` using PyMuPDF
   redaction annotations and `apply_redactions()`. Safe mode uses deterministic
   matches, dictionary aliases, typo-shaped names, and conservative exact
   `NER_PERSON` spans when the full span can be located. Broad token fallback
   is disabled.
8. The output file is saved with an `_ANON.txt` suffix, in the selected output
   folder when one is provided.
9. `audit_text()` checks the anonymized TXT output.
10. A safe `_REVIEW_CHECKLIST.txt` file is saved as the manual review guide. It
   contains safe basenames, counts, review tasks, PDF text extraction mode,
   visual/review PDF type, and short anonymized-label context only.
11. A safe report file is saved with a `_RAPORT.txt` suffix. The report includes
   safe dictionary status, label counters, OCR metadata, visual PDF metadata,
   review PDF metadata, checklist filename, and redaction coverage metadata
   only.

Example:

```text
output folder / document_ANON.txt
output folder / document_ANON_VISUAL.pdf
output folder / document_ANON_REVIEW.pdf
output folder / document_REVIEW_CHECKLIST.txt
output folder / document_RAPORT.txt
```

Experimental original-layout mode can additionally create:

```text
output folder / document_ORIGINAL_REDACTED.pdf
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

- scanned-PDF/OCR bounding-box visual redaction,
- handwritten text extraction.

## Safety assumptions

- PDF files are read locally.
- The original source PDF is left unchanged.
- PDF input produces TXT, a true-redacted visual PDF, an auxiliary rebuilt
  review PDF, a review checklist, and a report by default for text-based PDFs.
- Scanned/OCR-only PDF input can produce a rebuilt review PDF from OCR text, but
  no scanned-PDF visual redaction is created.
- Scanned PDF OCR is optional and local.
- No scanned/OCR-only original-layout redacted PDF file is created.
- The safe report file receives the `_RAPORT.txt` suffix.
- The safe review checklist receives the `_REVIEW_CHECKLIST.txt` suffix.
- Generated files can be written to a selected output folder.
- Existing generated files are not overwritten silently.
- No replacement map is created.
- No source values are written to reports, metadata, or counters.
- No source values are written to review checklists.
- The integration helper returns only the output path and category counters.
- Counters contain category names and counts only.
- Private dictionary terms are not written to reports, counters, or returned
  metadata.
- Dictionary workflow metadata contains only status names, labels, and
  counters.
- OCR metadata contains only used/status/input-type/page-count/warning fields.
- PDF metadata contains only text extraction mode, visual/review PDF
  status/type, safe generated basenames, redaction scope/status, redaction
  counts, category names, coverage counters, unmapped category counters, safe
  partial-coverage warnings, safe-scope NER exclusion notes, strict-scope
  warnings, and a color legend.
- Checklist findings come from anonymized output labels only, not original PDF
  source text.
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
source values. Stage 19 tests cover text-based PDF non-OCR regression, mocked
scanned-PDF OCR fallback, and controlled OCR-unavailable batch behavior. Stage
Stage 24 tests cover `_ANON_VISUAL.pdf` default creation, auxiliary
`_ANON_REVIEW.pdf` creation, visual/review PDF report metadata, anonymized
labels in the rebuilt PDF, absence of source values in the visual/review PDFs,
experimental `_ORIGINAL_REDACTED.pdf` behavior, bounded original-layout
redaction, batch metadata, and conservative `PERSON_NAME_TYPO` handling.

## Known limitations

- Detection quality is still limited by the Stage 1 regex engine.
- Private dictionary matching is deterministic, case-insensitive, and
  whitespace-tolerant, but not fuzzy matching or automatic entity detection.
- Extracted PDF text may not preserve visual layout or reading order.
- Scanned PDF OCR requires optional local OCR dependencies and Tesseract.
- OCR can be inaccurate and must be manually reviewed.
- `_ANON_VISUAL.pdf` depends on text-layer word coordinates and can miss text
  that cannot be mapped safely to whole words.
- `_ANON_REVIEW.pdf` output is an auxiliary readable review aid generated from
  anonymized text, not proof of complete anonymization and not a
  layout-preserving copy.
- Default visual PDF redaction skips unmappable spans instead of falling back to
  broad substring or token redaction. Strict legacy scope can include broader
  selected exact NER spans, but depends on local NER quality and PyMuPDF text
  matching; strict scope may over-redact.
- Single-token person-like NER detections and known public/legal or
  disease/scientific false positives are skipped by default unless stronger
  person context exists.
- Weak grouped phone-like numeric values in tables are left visible unless
  explicit contact context is nearby.
- Scanned-PDF/OCR original-layout visual redaction is not implemented.
- PDF input still writes `document_ANON.txt` for indexing, and by default also
  writes `document_ANON_VISUAL.pdf` and `document_ANON_REVIEW.pdf`; Stage 12
  collision-safe naming prevents silent overwrites in the output folder.
- Stage 9 audit checks only the extracted anonymized TXT output.
- Manual review is still required before trusting or sharing anonymized output.
