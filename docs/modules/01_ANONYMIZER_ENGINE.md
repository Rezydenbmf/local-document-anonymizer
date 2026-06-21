# Module: Plain Text Anonymizer Engine

## Purpose

This module implements the plain text anonymization engine for plain Python
strings. Stage 8 extends the engine with optional private sensitive terms
dictionary input. Stage 9 keeps the core text engine unchanged and adds
workflow helpers that return safe post-anonymization audit metadata. Stage 10.1
adds optional dictionary-path loading to the file workflows and dispatcher while
keeping the plain text engine API unchanged. Stage 11 improves private
dictionary matching while preserving that API.
Stage 12 adds optional output-directory support to file workflows and a
sequential batch workflow while keeping the plain text engine API unchanged.
Stage 16 adds audit risk metadata around the engine workflow without changing
the plain text engine return shape.
Stage 20 adds keyword-only optional local NER controls. Existing callers remain
dictionary/regex-only unless `use_ner=True` is passed.

## Related files

- `src/anonymizer.py`
- `src/ner.py`
- `src/sensitive_terms.py`
- `tests/test_anonymizer.py`
- `tests/test_sensitive_terms.py`

## Core Public API

```python
anonymize_text(text: str, sensitive_terms=None, use_ner=False, ner_model_name="pl_core_news_sm") -> tuple[str, dict[str, int]]
anonymize_file(source_path: str | Path, sensitive_terms=None, sensitive_terms_path=None, output_dir=None, use_ner=False, ner_model_name="pl_core_news_sm") -> tuple[Path, dict[str, int]]
anonymize_file_with_audit(source_path: str | Path, sensitive_terms=None, sensitive_terms_path=None, output_dir=None)
anonymize_batch(source_paths, output_dir, sensitive_terms=None, sensitive_terms_path=None, use_ner=False, ner_model_name="pl_core_news_sm")
```

The function returns:

1. anonymized text,
2. a dictionary of category counters.

The counter dictionary contains category names and counts only. It must not
contain original source values or a replacement map.

Stage 2 also exposes `anonymize_txt_file(...)` from `src/anonymizer.py`; that
file workflow is documented separately in `docs/modules/02_TXT_IO.md`. Stage 3
adds `anonymize_docx_file(...)`, documented in `docs/modules/03_DOCX_IO.md`.
Stage 4 adds `anonymize_pdf_file(...)`, documented in
`docs/modules/04_PDF_IO.md`. Stage 5 adds `anonymize_file(...)`, documented in
`docs/modules/05_GUI.md`, which dispatches one supported file to the existing
TXT, DOCX, or PDF workflow. Stage 6 adds safe report output, documented in
`docs/modules/06_REPORTING.md`. Stage 8 adds optional private dictionary
support, documented in `docs/modules/08_PRIVATE_DICTIONARY.md`. Stage 9 adds
post-anonymization audit workflow variants, documented in
`docs/modules/09_POST_ANONYMIZATION_AUDIT.md`. Stage 10.1 adds safe dictionary
status metadata to those workflows and reports. Stage 12 adds
`docs/modules/10_BATCH_OUTPUT_WORKSPACE.md`.

## Supported categories

Stage 1 supports:

- `PESEL` replaced with `[PESEL]`
- `EMAIL` replaced with `[EMAIL]`
- `TELEFON` replaced with `[TELEFON]`
- `DATA` replaced with `[DATA]`

The engine can also replace user-provided private dictionary aliases with
labels from a private dictionary, for example `[IMIE NAZWISKO]`. These labels
are dynamic and are not automatic entity detection.

When local NER is explicitly enabled and available, Stage 20 can also emit
internal labels `NER_PERSON`, `NER_ORG`, `NER_LOCATION`, and `NER_MISC`.

Address and postal-code detection are not implemented as automatic regex
categories.

## How it works

The engine first applies optional private sensitive terms, if provided. Private
dictionary matching is deterministic, case-insensitive, and tolerant of extra
internal whitespace. Longer aliases are processed before shorter aliases.

The engine then applies deterministic regular expressions in a fixed order:

1. `EMAIL`
2. `PESEL`
3. `TELEFON`
4. `DATA`

If `use_ner=True`, the engine then applies local spaCy NER to the remaining
text and skips existing placeholders to avoid double replacement.

Counters are based on actual replacements performed by `re.subn`.

## Inputs

The module accepts only a plain Python string. Passing another type raises
`TypeError`. The optional `sensitive_terms` argument accepts parsed
`SensitiveTerm` items from `src/sensitive_terms.py`. File workflows and the
single-file dispatcher also accept `sensitive_terms_path`; they load the
dictionary centrally before calling the engine.

## Outputs

The module returns anonymized text and a counter dictionary. Categories with no
matches are omitted from the dictionary.

Example:

```python
anonymize_text("Email tester@example.test on 2026-06-01.")
```

Returns:

```python
("Email [EMAIL] on [DATA].", {"EMAIL": 1, "DATA": 1})
```

Example with private dictionary terms:

```python
anonymize_text(
    "Person One Example emailed tester@example.test.",
    sensitive_terms=[SensitiveTerm("Person One Example", "IMIE NAZWISKO")],
)
```

Returns:

```python
("[IMIE NAZWISKO] emailed [EMAIL].", {"IMIE NAZWISKO": 1, "EMAIL": 1})
```

## Safety assumptions

- No source values are stored in the report.
- No replacement map is created.
- Private dictionary terms are not stored in counters or reports.
- Workflow dictionary metadata contains only status names, labels, and
  counters.
- Post-anonymization audit results contain only status, risk level, categories,
  counters, safe dictionary metadata, and a manual review flag.
- Batch summary metadata contains safe filenames, counters, audit status
  counts, risk level counts, aggregate audit category counters, and controlled
  error descriptions only.
- Tests use only synthetic values.
- No real documents or generated output files are added.
- No network calls, APIs, AI services, OCR, local LLMs, databases, DOCX, PDF, or
  GUI code are part of the core engine. File workflows call this engine from
  separate modules.

## How to test

Run:

```bash
python -m unittest discover -s tests
```

The tests cover PESEL, email, phone, date, combined categories, repeated
occurrences, unchanged text, private dictionary replacement, replacement order,
regex integration, report safety, and post-anonymization audit integration.
Stage 10.1 tests also cover dictionary-path workflow status and report safety.
Stage 11 tests cover aliases, case-insensitive matching, whitespace
normalization, label-only counters, and audit dictionary matching. Stage 12
tests cover output workspace dispatch and batch processing. Stage 16 tests
cover audit risk levels and safe risk metadata propagation. Stage 20 tests
cover optional local NER with mocked model output.

## Known limitations

- The default engine path is dictionary/regex-only and conservative.
- PESEL detection checks only the 11-digit format, not checksum validity.
- Phone detection focuses on high-confidence Polish-style numeric forms with a
  prefix or separators.
- Date detection is limited to `YYYY-MM-DD` and `DD.MM.YYYY`.
- Production-grade names, surnames, cities, organizations, context-based
  detection, uppercase word detection, addresses, and postal codes are not
  implemented.
- Private dictionary matching is deterministic, case-insensitive, and
  whitespace-tolerant, but not fuzzy matching, inflection handling, NER, or
  automatic entity detection.
- PDF file input is handled by the Stage 4 file workflow, not by new regex
  logic in the core engine.
- OCR, API calls, cloud services, local LLMs, databases, and replacement maps
  are not implemented in the core engine.
- Safe report files are created by the file workflows in Stage 6; the core
  engine itself still returns only anonymized text and counters.
- Stage 9/16 audit is conservative and does not guarantee complete
  anonymization.
- Stage 12 batch processing is sequential. Stage 20 NER remains optional and
  local; it does not add APIs, cloud services, local LLMs, databases, preview,
  or editing.
