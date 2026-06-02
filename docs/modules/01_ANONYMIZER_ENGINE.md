# Module: Plain Text Anonymizer Engine

## Purpose

This module implements Stage 1: a small regex-based anonymization engine for
plain Python strings.

## Related files

- `src/anonymizer.py`
- `tests/test_anonymizer.py`

## Core Public API

```python
anonymize_text(text: str) -> tuple[str, dict[str, int]]
```

The function returns:

1. anonymized text,
2. a dictionary of category counters.

The report dictionary contains category names and counts only. It must not
contain original source values or a replacement map.

Stage 2 also exposes `anonymize_txt_file(...)` from `src/anonymizer.py`; that
file workflow is documented separately in `docs/modules/02_TXT_IO.md`. Stage 3
adds `anonymize_docx_file(...)`, documented in `docs/modules/03_DOCX_IO.md`.

## Supported categories

Stage 1 supports:

- `PESEL` replaced with `[PESEL]`
- `EMAIL` replaced with `[EMAIL]`
- `TELEFON` replaced with `[TELEFON]`
- `DATA` replaced with `[DATA]`

Address and postal-code detection are not implemented in Stage 1.

## How it works

The engine applies deterministic regular expressions in a fixed order:

1. `EMAIL`
2. `PESEL`
3. `TELEFON`
4. `DATA`

Counters are based on actual replacements performed by `re.subn`.

## Inputs

The module accepts only a plain Python string. Passing another type raises
`TypeError`.

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

## Safety assumptions

- No source values are stored in the report.
- No replacement map is created.
- Tests use only synthetic values.
- No real documents or generated output files are added.
- No network calls, APIs, AI services, OCR, local LLMs, databases, DOCX, PDF, or
  GUI code are part of the core engine.

## How to test

Run:

```bash
python -m unittest discover -s tests
```

The tests cover PESEL, email, phone, date, combined categories, repeated
occurrences, unchanged text, and report safety.

## Known limitations

- The engine is regex-only and conservative.
- PESEL detection checks only the 11-digit format, not checksum validity.
- Phone detection focuses on high-confidence Polish-style numeric forms with a
  prefix or separators.
- Date detection is limited to `YYYY-MM-DD` and `DD.MM.YYYY`.
- Names, surnames, cities, organizations, context-based detection, uppercase
  word detection, addresses, and postal codes are not implemented.
- PDF, GUI, OCR, AI, API calls, cloud services, local LLMs, and databases are
  not implemented.
