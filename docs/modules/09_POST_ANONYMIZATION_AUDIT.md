# Module: Post-Anonymization Audit

## Purpose

This module implements the safe post-anonymization audit for text that has
already been written to an `_ANON` output file.

The audit is an additional safety layer before manual review. It is not a
guarantee that a document is fully anonymized. Stage 10.1 ensures that when a
private dictionary loads successfully, its terms are also checked in the
anonymized output. Stage 11 makes dictionary audit matching case-insensitive
and whitespace-tolerant, using the same private dictionary matcher as
anonymization.
Stage 12 aggregates per-file audit statuses into the safe batch summary. Stage
16 adds stronger deterministic warning categories and a per-file risk level for
manual-review prioritization.

## Related files

- `src/audit.py`
- `src/anonymizer.py`
- `src/report.py`
- `src/gui.py`
- `tests/test_audit.py`
- `tests/test_report.py`
- `tests/test_gui_workflow.py`
- `tests/test_batch_processing.py`

## Public API

```python
audit_text(text: str, sensitive_terms=None) -> dict[str, object]
anonymize_txt_file_with_audit(source_path, sensitive_terms=None, sensitive_terms_path=None, output_dir=None)
anonymize_docx_file_with_audit(source_path, sensitive_terms=None, sensitive_terms_path=None, output_dir=None)
anonymize_pdf_file_with_audit(source_path, sensitive_terms=None, sensitive_terms_path=None, output_dir=None)
anonymize_file_with_audit(source_path, sensitive_terms=None, sensitive_terms_path=None, output_dir=None)
anonymize_batch(source_paths, output_dir, sensitive_terms=None, sensitive_terms_path=None)
```

The existing Stage 2-5 helpers still return the original two-value tuple:

```python
anonymize_txt_file(...) -> tuple[Path, dict[str, int]]
anonymize_docx_file(...) -> tuple[Path, dict[str, int]]
anonymize_pdf_file(...) -> tuple[Path, dict[str, int]]
anonymize_file(...) -> tuple[Path, dict[str, int]]
```

These existing helpers still run the audit and save it into the report, but
they keep their previous return shape for compatibility.

## Audit Result

The audit result contains only safe metadata:

```python
{
    "status": "warning",
    "risk_level": "high_risk",
    "findings": {
        "EMAIL": 1,
        "PESEL": 0,
        "TELEFON": 1,
        "DATA": 0,
        "SENSITIVE_DICTIONARY_TERM": 0,
        "CASE_REFERENCE": 1,
        "POSTAL_CODE": 0,
        "ADDRESS_LIKE": 0,
        "STREET_LIKE": 0,
        "INITIAL_SURNAME": 0,
        "ID_LIKE_NUMBER": 0,
        "LONG_NUMBER_SEQUENCE": 0,
    },
    "manual_review_required": True,
}
```

The audit result must never contain original values, text snippets, dictionary
terms, full document text, or a replacement map. The risk level is only a
review-prioritization helper and is not a safety guarantee.

## Detected Warning Categories

The audit checks anonymized output text for conservative remaining patterns:

- `EMAIL`
- `PESEL`
- `TELEFON`
- `DATA`
- `SENSITIVE_DICTIONARY_TERM`
- `CASE_REFERENCE`
- `POSTAL_CODE`
- `ADDRESS_LIKE`
- `STREET_LIKE`
- `INITIAL_SURNAME`
- `ID_LIKE_NUMBER`
- `LONG_NUMBER_SEQUENCE`

Case/reference, address, street, initial/surname, ID-like number, and long
number checks are intentionally simple and conservative. They are warning
signals only, not full entity detection.

## Risk Level Logic

The audit assigns one of three safe risk levels:

- `ok`: no audit warning counters.
- `warning`: warning counters exist, but no high-risk condition is met.
- `high_risk`: at least one high-risk category is present or total audit
  warnings reach 3.

High-risk categories are:

- `EMAIL`
- `PESEL`
- `TELEFON`
- `SENSITIVE_DICTIONARY_TERM`
- `ADDRESS_LIKE`
- `ID_LIKE_NUMBER`
- `LONG_NUMBER_SEQUENCE`

The threshold is intentionally small and deterministic: 3 total audit warnings
also produce `high_risk`, even when each individual category is otherwise a
warning-level signal. `DATA`, `CASE_REFERENCE`, `POSTAL_CODE`, `STREET_LIKE`,
and `INITIAL_SURNAME` are warning-level categories unless the total warning
threshold is reached.

## Workflow Integration

TXT and PDF workflows audit the anonymized text immediately after saving the
`_ANON` TXT output.

DOCX workflow audits the text extracted from the saved `_ANON.docx` copy, using
the same basic paragraph and simple-table scope as the existing DOCX reader.

When a dictionary path is selected and parsed successfully, the workflow passes
the loaded aliases into the audit. Remaining dictionary aliases are counted
under `SENSITIVE_DICTIONARY_TERM` using Stage 11 matching semantics. If no
dictionary is selected or the selected dictionary is invalid, the audit runs
without dictionary terms and the report records the safe dictionary status
separately.

The report module receives only the audit result metadata and writes a safe
`Post-anonymization audit` section to `_RAPORT.txt`, including status, risk
level, category counters, and manual review requirement.

The batch workflow counts per-file audit statuses, risk levels, and aggregate
audit category counters in `_BATCH_SUMMARY.txt`. The GUI shows aggregate audit
status counts, risk counts, and aggregate audit warning categories. It does not
display original detected values, text snippets, or dictionary terms.

## Safety Assumptions

- The audit runs locally only.
- No internet, API, cloud, AI, OCR, local LLM, database, NER, or replacement
  map is added.
- The audit does not store or return source values.
- The audit does not store or return text snippets.
- The audit does not store or return private dictionary terms.
- Dictionary audit findings contain only `SENSITIVE_DICTIONARY_TERM` counters,
  never the aliases or terms.
- Risk levels are safe metadata only and do not approve files automatically.
- The audit does not inspect unsupported DOCX elements beyond the existing
  basic DOCX text scope.
- Manual review remains required even when the audit status and risk level are
  `ok`.

## How to Test

Run:

```bash
python -m unittest discover -s tests
```

The tests cover suspicious remaining email, PESEL, phone, date, private
dictionary terms, Stage 11 dictionary audit matching, case/reference patterns,
postal codes, address-like patterns, street-like patterns, initial/surname
patterns, ID-like numbers, long number sequences, `ok`, `warning`, and
`high_risk` risk levels, report safety, and GUI/dispatcher audit metadata
safety with synthetic values only. Stage 10.1 tests add workflow coverage for
loaded dictionary status and dictionary path integration across TXT, DOCX, and
PDF. Stage 12/16 tests cover audit status, risk level, and category aggregation
in the batch summary.

## Known Limitations

- The audit is regex-based and conservative.
- It can miss sensitive data.
- It can warn on harmless text.
- It does not prove that anonymization is complete.
- It does not add automatic names, cities, organizations, broad addresses,
  context-aware detection, OCR, AI, APIs, cloud services, local LLMs,
  databases, NER, or automatic deletion of originals.
