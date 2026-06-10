# Module: Private Sensitive Terms Dictionary

## Purpose

This module implements Stage 8: optional private local sensitive terms
dictionary support.

The dictionary lets the user manually specify exact terms that should be
anonymized, for example:

```text
Person One Example = [IMIE NAZWISKO]
```

The real dictionary is private user input. It must not be committed to the
repository. The repository contains only a synthetic example dictionary at
`examples/sensitive_terms.example.txt`.

Stage 9 can audit anonymized output for private dictionary terms that still
remain, but the audit returns only the safe category
`SENSITIVE_DICTIONARY_TERM` and a count.

Stage 10.1 fixes the GUI/dispatcher path flow. The GUI stores the selected
dictionary path, the workflow loads it centrally, and reports/GUI output show
only safe dictionary status and label counters.

## Related files

- `src/sensitive_terms.py`
- `src/anonymizer.py`
- `src/gui.py`
- `src/report.py`
- `examples/sensitive_terms.example.txt`
- `tests/test_sensitive_terms.py`

## Public API

```python
SensitiveTerm(term: str, label: str)
parse_sensitive_terms(text: str) -> list[SensitiveTerm]
load_sensitive_terms(file_path: str | Path) -> list[SensitiveTerm]
apply_sensitive_terms(text: str, sensitive_terms) -> tuple[str, dict[str, int]]
anonymize_text(text: str, sensitive_terms=None) -> tuple[str, dict[str, int]]
anonymize_file(source_path: str | Path, sensitive_terms=None, sensitive_terms_path=None) -> tuple[Path, dict[str, int]]
anonymize_file_with_audit(source_path: str | Path, sensitive_terms=None, sensitive_terms_path=None)
```

The file workflows also accept optional `sensitive_terms`:

```python
anonymize_txt_file(source_path, sensitive_terms=None, sensitive_terms_path=None)
anonymize_docx_file(source_path, sensitive_terms=None, sensitive_terms_path=None)
anonymize_pdf_file(source_path, sensitive_terms=None, sensitive_terms_path=None)
```

## Dictionary Format

The dictionary file is UTF-8 text. Supported lines use this format:

```text
term = [LABEL]
```

Rules:

- empty lines are ignored,
- lines starting with `#` are comments,
- malformed lines raise `ValueError` with a safe line number,
- duplicate terms are rejected,
- labels are stored without brackets in counters,
- replacement text uses brackets, for example `[IMIE NAZWISKO]`.

Malformed-line errors must not include the original private term.

## How It Works

1. The user optionally selects a private dictionary file path in the GUI, or a
   caller passes parsed `SensitiveTerm` items to the engine.
2. The dictionary is loaded locally from UTF-8 text.
3. Private terms are applied before the regex categories.
4. Longer terms are processed before shorter terms.
5. Regex categories such as `EMAIL`, `PESEL`, `TELEFON`, and `DATA` are applied
   after private dictionary replacements.
6. The function returns anonymized text plus counters by label only.

Example output counter:

```python
{"IMIE NAZWISKO": 2, "EMAIL": 1}
```

The counter must never use original terms as keys.

## GUI Behavior

The GUI adds optional sensitive terms file selection. If no dictionary is
selected, the app works as before.

The GUI stores the selected dictionary path and passes it to the workflow. It
may show safe dictionary status, but it must not display dictionary contents.
Counters shown in the GUI are labels and counts only.

Dictionary status values are:

- `not selected`: no dictionary path was provided.
- `loaded`: the selected dictionary was valid and loaded.
- `invalid`: a selected dictionary could not be loaded or parsed.
- loaded with no matches: the dictionary loaded, but no dictionary term was
  replaced.

## Report Behavior

Reports may contain dictionary used/status/matches-found metadata plus
dictionary labels and counts. Reports must not contain:

- original private dictionary terms,
- original document text,
- replacement maps,
- full input paths,
- source filenames,
- logs containing source values.
- audit snippets or private terms found after anonymization.

Stage 9 audit reports may contain `SENSITIVE_DICTIONARY_TERM: N`, but never the
private term values.

The report module receives counters and safe dictionary metadata only, not
original private terms.

## Safety Assumptions

- The real dictionary must stay private.
- The real dictionary must not be committed.
- A real dictionary can live outside the repository or inside ignored
  `private/`.
- The repository contains only synthetic dictionary examples and tests.
- No replacement map is created.
- No source terms are written to reports or returned counters.
- No source terms are written to audit results or audit report sections.
- Invalid dictionary status does not expose the malformed line content or the
  source term value.
- No internet, APIs, cloud services, AI, OCR, local LLM, database, batch
  processing, or automatic deletion of originals is added.
- Manual review of anonymized output is still required.

## How to Test

Run:

```bash
python -m unittest discover -s tests
```

The Stage 8 tests cover valid parsing, ignored comments and empty lines,
dictionary replacement, counters by label only, safe object representation,
longer-term replacement order, malformed-line validation, behavior without a
dictionary, regex integration, and safe report output. Stage 10.1 tests add
path-based dispatcher flow, report status, invalid dictionary status,
loaded-without-matches status, and TXT/DOCX/PDF dictionary-path compatibility.

## Known Limitations

- Matching is literal and case-sensitive.
- The dictionary does not add automatic names, addresses, organizations, cities,
  or context-based detection.
- The dictionary does not support OCR, scanned PDFs, AI, APIs, cloud services,
  local LLMs, databases, batch processing, or automatic deletion of originals.
- The dictionary is not a replacement map and is not generated by the app.
- Stage 9 audit can warn that exact private terms may remain, but it does not
  display those terms and does not guarantee all dictionary terms were handled.
- Manual review remains required before trusting or sharing anonymized output.
