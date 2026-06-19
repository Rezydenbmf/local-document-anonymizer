# Module: Private Sensitive Terms Dictionary

## Purpose

This module documents optional private local sensitive terms dictionary
support. Stage 8 introduced the dictionary. Stage 11 adds aliases,
case-insensitive matching, whitespace-tolerant term matching, and synthetic
candidate/seed examples.

The dictionary lets the user manually specify terms and aliases that should be
anonymized, for example:

```text
Person One Example = [IMIE NAZWISKO]
Person One Example | P. One Example = [IMIE NAZWISKO]
```

The real dictionary is private user input. It must not be committed to the
repository. The repository contains only a synthetic example dictionary at
`examples/sensitive_terms.example.txt`.

Stage 9 can audit anonymized output for private dictionary terms that still
remain. Stage 11 makes the audit use the same case-insensitive and
whitespace-tolerant dictionary matching semantics as anonymization. The audit
still returns only the safe category `SENSITIVE_DICTIONARY_TERM` and a count.

Stage 10.1 fixes the GUI/dispatcher path flow. The GUI stores the selected
dictionary path, the workflow loads it centrally, and reports/GUI output show
only safe dictionary status and label counters.

Stage 12 batch processing uses the same dictionary path flow for each supported
file in the selected batch. Batch summaries still expose only safe labels,
counts, statuses, and filenames.

## Related files

- `src/sensitive_terms.py`
- `src/anonymizer.py`
- `src/gui.py`
- `src/report.py`
- `examples/sensitive_terms.example.txt`
- `examples/sensitive_terms.seed.example.txt`
- `examples/dictionary_candidates.example.txt`
- `tests/test_sensitive_terms.py`

## Public API

```python
SensitiveTerm(term: str, label: str)
parse_sensitive_terms(text: str) -> list[SensitiveTerm]
load_sensitive_terms(file_path: str | Path) -> list[SensitiveTerm]
apply_sensitive_terms(text: str, sensitive_terms) -> tuple[str, dict[str, int]]
anonymize_text(text: str, sensitive_terms=None) -> tuple[str, dict[str, int]]
anonymize_file(source_path: str | Path, sensitive_terms=None, sensitive_terms_path=None, output_dir=None) -> tuple[Path, dict[str, int]]
anonymize_file_with_audit(source_path: str | Path, sensitive_terms=None, sensitive_terms_path=None, output_dir=None)
anonymize_batch(source_paths, output_dir, sensitive_terms=None, sensitive_terms_path=None)
```

The file workflows also accept optional `sensitive_terms`:

```python
anonymize_txt_file(source_path, sensitive_terms=None, sensitive_terms_path=None, output_dir=None)
anonymize_docx_file(source_path, sensitive_terms=None, sensitive_terms_path=None, output_dir=None)
anonymize_pdf_file(source_path, sensitive_terms=None, sensitive_terms_path=None, output_dir=None)
```

## Dictionary Format

The dictionary file is UTF-8 text. Supported lines use either the original
single-term format or the Stage 11 alias format:

```text
term = [LABEL]
alias | alias = [LABEL]
```

Examples:

```text
Person One Example = [IMIE NAZWISKO]
Person One Example | P. One Example | PERSON ONE EXAMPLE = [IMIE NAZWISKO]
Example Institution | Example Inst. = [NAZWA PODMIOTU]
```

Rules:

- empty lines are ignored,
- lines starting with `#` are comments,
- aliases on one line are separated with `|`,
- malformed lines raise `ValueError` with a safe line number,
- equivalent aliases for the same label are treated as one match entry,
- equivalent aliases mapped to different labels are rejected with a safe line
  number,
- labels are stored without brackets in counters,
- replacement text uses brackets, for example `[IMIE NAZWISKO]`.
- matching is case-insensitive,
- extra whitespace inside matched terms is tolerated,
- longer aliases are applied before shorter aliases.

Malformed-line and duplicate-alias errors must not include the original private
term or alias.

## Implementation and User Notes

Dictionary files are expected to be UTF-8 text files. The GUI/pipeline
dictionary flow was manually validated in Stage 10.2 with small synthetic
UTF-8 TXT and dictionary files. A leading UTF-8 BOM at the start of the
dictionary file is ignored so it cannot become part of the first alias.
Reports and GUI output must show only safe dictionary status, labels, and
counters; they must not expose original dictionary aliases or terms.

Stage 11 adds a synthetic candidate workflow example at
`examples/dictionary_candidates.example.txt`. It is only a safe example of how
a human reviewer can collect missing terms before manually approving them for a
real private dictionary. Real candidates must not be stored in the repository.

## How It Works

1. The user optionally selects a private dictionary file path in the GUI, or a
   caller passes parsed `SensitiveTerm` items to the engine.
2. The dictionary is loaded locally from UTF-8 text.
3. Private aliases are applied before the regex categories.
4. Longer aliases are processed before shorter aliases.
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

- original private dictionary aliases or terms,
- original document text,
- replacement maps,
- full input paths,
- source filenames,
- logs containing source values,
- audit snippets or private terms found after anonymization.

Stage 9 audit reports may contain `SENSITIVE_DICTIONARY_TERM: N`, but never the
private alias or term values.

The report module receives counters and safe dictionary metadata only, not
original private aliases or terms.

## Safety Assumptions

- The real dictionary must stay private.
- The real dictionary must not be committed.
- A real dictionary can live outside the repository or inside ignored
  `private/`.
- The repository contains only synthetic dictionary examples and tests.
- No replacement map is created.
- No source aliases or terms are written to reports or returned counters.
- No source aliases or terms are written to audit results or audit report
  sections.
- Invalid dictionary status does not expose the malformed line content or the
  source term value.
- No internet, APIs, cloud services, AI, OCR, local LLM, database, NER, or
  automatic deletion of originals is added.
- Manual review of anonymized output is still required.

## How to Test

Run:

```bash
python -m unittest discover -s tests
```

The tests cover valid parsing, ignored comments and empty lines, dictionary
replacement, alias parsing, backward compatibility with `term = [LABEL]`,
case-insensitive matching, whitespace normalization, counters by label only,
safe object representation, longer-alias replacement order, malformed-line
validation, behavior without a dictionary, regex integration, safe report
output, path-based dispatcher flow, report status, invalid dictionary status,
loaded-without-matches status, TXT/DOCX/PDF dictionary-path compatibility, and
audit integration. Stage 18 stabilization tests cover BOM-prefixed dictionary
files so the first alias and later aliases on the same line are both matched.
Stage 12 tests cover dictionary-path use in a safe batch summary.

## Known Limitations

- Matching is deterministic, case-insensitive, and whitespace-tolerant, but not
  fuzzy or language-aware.
- The dictionary does not add automatic names, addresses, organizations, cities,
  or context-based detection.
- The dictionary does not support OCR, scanned PDFs, AI, APIs, cloud services,
  local LLMs, databases, NER, inflection handling, or automatic deletion of
  originals.
- The dictionary is not a replacement map and is not generated by the app.
- Stage 9 audit can warn that private dictionary aliases may remain, but it
  does not display those aliases and does not guarantee all dictionary terms
  were handled.
- Manual review remains required before trusting or sharing anonymized output.
