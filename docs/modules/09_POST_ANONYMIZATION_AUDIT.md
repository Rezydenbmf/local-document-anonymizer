# Module: Post-Anonymization Audit

## Purpose

This module implements Stage 9: a safe post-anonymization audit for text that
has already been written to an `_ANON` output file.

The audit is an additional safety layer before manual review. It is not a
guarantee that a document is fully anonymized.

## Related files

- `src/audit.py`
- `src/anonymizer.py`
- `src/report.py`
- `src/gui.py`
- `tests/test_audit.py`
- `tests/test_report.py`
- `tests/test_gui_workflow.py`

## Public API

```python
audit_text(text: str, sensitive_terms=None) -> dict[str, object]
anonymize_txt_file_with_audit(source_path, sensitive_terms=None)
anonymize_docx_file_with_audit(source_path, sensitive_terms=None)
anonymize_pdf_file_with_audit(source_path, sensitive_terms=None)
anonymize_file_with_audit(source_path, sensitive_terms=None)
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
    "findings": {
        "EMAIL": 1,
        "PESEL": 0,
        "TELEFON": 1,
        "DATA": 0,
        "SENSITIVE_DICTIONARY_TERM": 0,
        "CASE_REFERENCE": 1,
        "POSTAL_CODE": 0,
        "ADDRESS": 0,
    },
    "manual_review_required": True,
}
```

The audit result must never contain original values, text snippets, dictionary
terms, full document text, or a replacement map.

## Detected Warning Categories

The audit checks anonymized output text for conservative remaining patterns:

- `EMAIL`
- `PESEL`
- `TELEFON`
- `DATA`
- `SENSITIVE_DICTIONARY_TERM`
- `CASE_REFERENCE`
- `POSTAL_CODE`
- `ADDRESS`

Case/reference and address checks are intentionally simple and conservative.
They are warning signals only, not full entity detection.

## Workflow Integration

TXT and PDF workflows audit the anonymized text immediately after saving the
`_ANON` TXT output.

DOCX workflow audits the text extracted from the saved `_ANON.docx` copy, using
the same basic paragraph and simple-table scope as the existing DOCX reader.

The report module receives only the audit result metadata and writes a safe
`Post-anonymization audit` section to `_RAPORT.txt`.

The GUI shows audit status and counters by category only. It does not display
original detected values, text snippets, or dictionary terms.

## Safety Assumptions

- The audit runs locally only.
- No internet, API, cloud, AI, OCR, local LLM, database, batch processing, or
  replacement map is added.
- The audit does not store or return source values.
- The audit does not store or return text snippets.
- The audit does not store or return private dictionary terms.
- The audit does not inspect unsupported DOCX elements beyond the existing
  basic DOCX text scope.
- Manual review remains required even when the audit status is `ok`.

## How to Test

Run:

```bash
python -m unittest discover -s tests
```

The Stage 9 tests cover suspicious remaining email, PESEL, phone, date, private
dictionary terms, case/reference patterns, postal codes, address-like patterns,
OK status, report safety, and GUI/dispatcher audit metadata safety with
synthetic values only.

## Known Limitations

- The audit is regex-based and conservative.
- It can miss sensitive data.
- It can warn on harmless text.
- It does not prove that anonymization is complete.
- It does not add automatic names, cities, organizations, broad addresses,
  context-aware detection, OCR, AI, APIs, cloud services, local LLMs,
  databases, batch processing, or automatic deletion of originals.
