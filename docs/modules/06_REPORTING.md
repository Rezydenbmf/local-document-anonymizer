# Module: Safe Report File Output

## Purpose

This module implements safe report file output without source values or
replacement maps. Stage 8 allows reports to include private dictionary labels
and counts, but never original dictionary terms. Stage 9 adds a safe
post-anonymization audit section with audit status and counters only. Stage
10.1 adds a safe dictionary section with used/status/matches-found metadata and
dictionary label counters only.

## Related files

- `src/report.py`
- `src/file_writers.py`
- `src/anonymizer.py`
- `src/gui.py`
- `src/sensitive_terms.py`
- `tests/test_report.py`
- `tests/test_sensitive_terms.py`

## Public API

```python
build_report_text(...) -> str
save_report_file(...) -> Path
build_report_path(source_path: str | Path) -> Path
```

The existing anonymization helpers keep their Stage 2-5 return values:

```python
anonymize_txt_file(source_path, sensitive_terms=None, sensitive_terms_path=None) -> tuple[Path, dict[str, int]]
anonymize_docx_file(source_path, sensitive_terms=None, sensitive_terms_path=None) -> tuple[Path, dict[str, int]]
anonymize_pdf_file(source_path, sensitive_terms=None, sensitive_terms_path=None) -> tuple[Path, dict[str, int]]
anonymize_file(source_path, sensitive_terms=None, sensitive_terms_path=None) -> tuple[Path, dict[str, int]]
```

After a successful anonymized output is saved, these helpers also save a report
file next to the output.

## Report Naming

Reports are saved with the `_RAPORT.txt` suffix:

```text
document.txt -> document_ANON.txt + document_RAPORT.txt
document.docx -> document_ANON.docx + document_RAPORT.txt
document.pdf -> document_ANON.txt + document_RAPORT.txt
```

Original files are not modified.

Stage 10.1 does not change output naming. A TXT file and PDF file with the
same base name in the same folder can still produce confusing or colliding
`_ANON.txt` and `_RAPORT.txt` paths, so manual tests should use distinct names
or folders.

## Report Contents

The report contains only safe metadata:

- status,
- input type,
- output type,
- counters by supported category,
- dictionary used/status/matches-found metadata,
- optional private dictionary label counters,
- post-anonymization audit status,
- post-anonymization audit counters by warning category,
- manual review requirement,
- confirmation that original sensitive values are not stored,
- confirmation that no replacement map was created.

## Deliberately Excluded

The report must not contain:

- original document text,
- detected original sensitive values,
- original PESEL values,
- original e-mail addresses,
- original phone numbers,
- original dates in source form,
- original private dictionary terms,
- text snippets,
- audit source values,
- replacement maps,
- full input paths,
- full input filenames,
- logs containing document content.

Dictionary status meanings:

- `not selected`: no dictionary path was provided.
- `loaded`: a dictionary path was provided and parsed successfully.
- `invalid`: a dictionary path was provided but could not be loaded or parsed.

`Dictionary used: yes` means the dictionary loaded successfully. `Dictionary
matches found: yes` means at least one dictionary replacement occurred. Label
counters are grouped by dictionary label/category only.

## Safety Assumptions

The report module receives only counters, safe dictionary metadata, audit
metadata, and file-type metadata. It does not read source documents and does
not receive original source text, original private dictionary terms, text
snippets, or replacement maps.

Manual review is still required. A safe report confirms what the tool replaced
and what the audit warned about, but it does not prove the whole document is
anonymized.

## How to Test

Run:

```bash
python -m unittest discover -s tests
```

The tests cover report text generation, report path naming, safe report
content, TXT integration, DOCX integration, PDF integration, dispatcher report
safety, private dictionary report safety, and post-anonymization audit report
safety.

## Known Limitations

- The report is a plain TXT file only.
- The report contains anonymization and audit counters only, not a detailed
  audit trail.
- No replacement map is created.
- No original private dictionary terms are written to reports.
- No source filename is written into the report body.
- The report does not guarantee complete anonymization.
