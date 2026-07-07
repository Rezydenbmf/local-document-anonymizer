# Module: PDF Visual Redaction and Review Output

## Purpose

Stage 24 changes the default PDF review workflow after pilot feedback showed
that broad original-layout text search and token fallback could make real
review PDFs unreadable. A text-based PDF source now creates by default:

```text
document_ANON.txt
document_ANON_VISUAL.pdf
document_ANON_REVIEW.pdf
document_REVIEW_CHECKLIST.txt
document_RAPORT.txt
```

`document_ANON_VISUAL.pdf` is the primary manual review artifact for
text-based PDFs. It preserves source PDF pages and uses true PyMuPDF redaction
annotations with `apply_redactions()`. `document_ANON_REVIEW.pdf` is auxiliary
and rebuilt from anonymized text only. `document_REVIEW_CHECKLIST.txt` is the
privacy-safe manual review guide, and `document_ANON.txt` remains the text
source for approved-workspace indexing and the Local Knowledge Assistant.

The previous original-layout true-redaction workflow remains available only as
an explicit experimental mode and writes:

```text
document_ORIGINAL_REDACTED.pdf
```

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

Default original-layout visual PDF:

1. Extract PDF text from the text layer, or use OCR fallback only when the text
   layer is unavailable and local OCR is available.
2. Anonymize the extracted text through the normal dictionary, regex, and
   optional local NER workflow.
3. Save the anonymized text as `_ANON.txt`.
4. Extract per-page PDF words using PyMuPDF `page.get_text("words")`.
5. Build internal non-persisted detected spans for deterministic identifiers,
   contact-context phone numbers, private dictionary aliases,
   `PERSON_NAME_TYPO`, and exact NER person/org/location spans after
   allowlist filtering for selected public institutions, health-domain terms,
   ordinary words, and other known NER false positives.
6. Map each span to full word rectangles only. If a span cannot be mapped
   safely to whole words, skip it and report the category count as unmapped.
7. Add true redaction annotations to mapped rectangles and save
   `_ANON_VISUAL.pdf`.
8. Create auxiliary `_ANON_REVIEW.pdf` from anonymized text, with wrapped lines
   and `Source page N` headers when page text is available.
9. Save `_REVIEW_CHECKLIST.txt` with safe basenames, category counts, review
   tasks, PDF text extraction mode, visual/review PDF metadata, and
   anonymized-label context only.
10. Save `_RAPORT.txt` with safe metadata only.

Legacy experimental original-layout redaction:

- Uses PyMuPDF text search to locate exact text matches on source PDF pages.
- Adds redaction annotations and calls `apply_redactions()` before saving.
- Writes `_ORIGINAL_REDACTED.pdf` only when the experimental mode is selected.
- Keeps the broad token fallback disabled in safe mode.
- Strict mode can include broader selected NER spans and warns that it may
  over-redact.

## Reports and batch summaries

Per-file reports include safe PDF metadata:

- PDF text extraction used: `text_layer`, `ocr_fallback`, or future supported
  modes,
- visual PDF created: yes/no,
- visual PDF type and basename,
- redaction mapping mode, currently `word_coordinates`,
- review PDF created: yes/no,
- review PDF type: `rebuilt_from_anonymized_text`,
- review PDF basename,
- review checklist basename,
- layout-preserving original redaction used: yes/no,
- whether original-layout redaction is experimental,
- optional original-layout redaction status, scope, block count, and category
  counters,
- detected category counters,
- TXT-anonymized category counters,
- PDF-redacted category counters,
- detected-but-not-PDF-redacted category counters,
- unmapped PDF detections by category,
- weak phone-like numeric values skipped by count only,
- NER/PDF exclusion counters and line-break person candidate counts through the
  Local NER report section. Public/institution, disease/microbiology/vaccine,
  ordinary-word, version-like, and single-token person skips are reported by
  category and count only.

Reports, checklists, and batch summaries do not include source text, matched
values, private paths, raw PDF text, prompts, raw responses, or replacement
maps. Checklists may include short context from anonymized output labels only.

## Manual review behavior

The manual review workflow still detects the `_ANON.txt` output for a
PDF-derived file so the TXT can be approved and exported for the Local
Knowledge Assistant. It pairs `_REVIEW_CHECKLIST.txt` when present. When a
companion PDF exists, the GUI open-output action prefers `_ANON_VISUAL.pdf`,
then `_ORIGINAL_REDACTED.pdf`, then `_ANON_REVIEW.pdf`, then legacy
`_ANON.pdf`.

## Safety assumptions

- The source PDF is not modified.
- `_ANON_VISUAL.pdf` uses true redaction annotations applied to detected text
  coordinates.
- The auxiliary rebuilt review PDF contains anonymized text only, not original
  PDF pages as images or content layers.
- Generated PDF/TXT/checklist/report files use collision-safe names.
- Original-layout redaction is local, optional, and experimental.
- Reports and review checklists store safe metadata only.
- Manual review remains required.

## Known limitations

- `_ANON_VISUAL.pdf` depends on PyMuPDF text-layer word coordinates.
- `_ANON_REVIEW.pdf` is not layout-preserving and is auxiliary.
- Rebuilt review PDF quality depends on PDF text extraction or OCR text quality.
- Scanned-PDF/OCR bounding-box redaction is not implemented.
- Unusual encodings, fragmented glyphs, rotated text, forms, annotations, or
  text in images can be missed.
- Visual redaction skips unsafe or unlocatable spans instead of falling back to
  broad substring or token redaction.
- NER allowlist filtering is applied before visual PDF spans are converted into
  word-coordinate redaction rectangles; extracted non-breaking spaces, soft
  hyphens, and common Unicode dash variants are normalized for this check.
  Exact configured health-domain terms are excluded from visual NER spans
  regardless of whether the local model labels them as person, organization,
  location, or miscellaneous entities.
- Weak grouped numeric values in tables are left visible unless phone/contact
  context is present; reviewers still need to inspect phone-like numbers
  manually.
- Selected public/institution names and disease/microbiology/vaccine terms are
  intentionally not redacted by default NER/PDF scope unless the private
  dictionary or a deterministic high-confidence rule matches them.
- Single-token person-like NER detections are skipped unless strong person
  context exists.
- Strict legacy original-layout NER scope can over-redact.
- A clean audit, review checklist, review PDF, or redaction report is not proof
  that the PDF is fully safe.

## How to test

Run:

```bash
python -m unittest discover -s tests
```

The Stage 24 tests create synthetic PDFs only. They verify `_ANON_VISUAL.pdf`,
`_ANON_REVIEW.pdf`, `_ANON.txt`, `_REVIEW_CHECKLIST.txt`, and `_RAPORT.txt`
default creation; true removal of source values from the visual PDF; preserved
ordinary words in the visual PDF; bounded exact-span NER redaction; auxiliary
rebuilt review PDF metadata; explicit experimental `_ORIGINAL_REDACTED.pdf`
behavior; batch metadata; manual review PDF/checklist discovery; and the
`PERSON_NAME_TYPO` pattern.
