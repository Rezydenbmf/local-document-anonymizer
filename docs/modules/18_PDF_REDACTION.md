# Module: Layout-Preserving PDF Redaction MVP

## Purpose

Stage 23 adds a narrow layout-preserving visual output for text-based PDF
inputs. A PDF source now creates both:

```text
document_ANON.pdf
document_ANON.txt
document_RAPORT.txt
```

`document_ANON.pdf` is for visual manual review in the original PDF layout.
`document_ANON.txt` remains the text source for approved-workspace indexing and
the Local Knowledge Assistant.

## Related files

- `src/pdf_redaction.py`
- `src/anonymizer.py`
- `src/file_writers.py`
- `src/report.py`
- `src/review.py`
- `src/gui.py`
- `tests/test_pdf_io.py`
- `tests/test_report.py`
- `tests/test_batch_processing.py`
- `tests/test_review_workflow.py`

## How it works

The redaction helper uses PyMuPDF to open a text-based PDF, locate
deterministic sensitive-text matches on each page, add redaction annotations,
and call `apply_redactions()` before saving the `_ANON.pdf` copy.

This is intended to remove the matched source text from the generated PDF
content, not merely cover it with a rectangle.

The MVP redacts:

- `EMAIL`
- `PESEL`
- `TELEFON`
- `DATA`
- `POSTAL_CODE`
- simple labeled address contexts such as `Address: ...`
- private dictionary aliases when their exact text can be located
- conservative `PERSON_NAME_TYPO` matches such as `Firstname-Lastname Lastname`
- exact local NER spans for `NER_PERSON`, `NER_ORG`, `NER_LOCATION`, and
  `NER_MISC` when NER is enabled, available, and the span can be located in
  the text-based PDF

The visual color legend is recorded in the safe report:

- red: PESEL and strong numeric identifiers
- orange: phone numbers and conservative person-name typo matches
- blue: email and electronic identifiers
- gray/purple: dates, organizations, locations, and other markers

## Reports and batch summaries

Per-file reports include safe PDF redaction metadata:

- whether the visual PDF output was created,
- redaction status,
- generated PDF basename,
- whether true redaction was used,
- redaction block count,
- detected category counters,
- TXT-anonymized category counters,
- PDF-redacted category counters,
- detected-but-not-PDF-redacted category counters,
- color legend.

Batch summaries include PDF redaction status counts and generated PDF
basenames when present. If detected categories were not PDF-redacted, reports
and batch summaries use `completed_with_warnings` and include a safe warning.
They do not include source text, matched values, snippets, private paths, raw
PDF text, or replacement maps.

## Manual review behavior

The manual review workflow still detects the `_ANON.txt` output for a
PDF-derived file so the TXT can be approved and exported for the Local
Knowledge Assistant. When a companion `_ANON.pdf` exists, the GUI open action
prefers that visual PDF for manual review.

## Safety assumptions

- The source PDF is not modified.
- Generated PDF/TXT/report files use collision-safe names.
- Redaction is local and uses the installed PyMuPDF dependency.
- Reports store safe metadata only.
- Manual review remains required.

## Known limitations

- Stage 23 supports text-based PDF redaction only.
- Scanned-PDF/OCR bounding-box redaction is not implemented.
- Matching depends on text that PyMuPDF can locate on the page; unusual
  encodings, fragmented glyphs, rotated text, forms, annotations, or text in
  images can be missed.
- Font preservation is not the goal; layout and redaction locations matter
  more than visual perfection.
- NER span redaction uses exact text search only; it can miss spans when the
  PDF text layer differs from extracted text or when the local NER model misses
  or misclassifies an entity.
- A clean audit or redaction report is not proof that the PDF is fully safe.

## How to test

Run:

```bash
python -m unittest discover -s tests
```

The Stage 23 tests create synthetic PDFs only. They verify `_ANON.pdf`,
`_ANON.txt`, and `_RAPORT.txt` creation, true-redaction extraction behavior,
safe report metadata, detected/TXT/PDF coverage metadata, partial-coverage
warnings, batch summary metadata, manual-review PDF open preference, and the
`PERSON_NAME_TYPO` pattern.
