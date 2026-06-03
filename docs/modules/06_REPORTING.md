# Module: Safe Report File Output

## Purpose

This module implements Stage 6: safe report file output without source values
or replacement maps.

## Related files

- `src/report.py`
- `src/file_writers.py`
- `src/anonymizer.py`
- `src/gui.py`
- `tests/test_report.py`

## Public API

```python
build_report_text(...) -> str
save_report_file(...) -> Path
build_report_path(source_path: str | Path) -> Path
```

The existing anonymization helpers keep their Stage 2-5 return values:

```python
anonymize_txt_file(source_path) -> tuple[Path, dict[str, int]]
anonymize_docx_file(source_path) -> tuple[Path, dict[str, int]]
anonymize_pdf_file(source_path) -> tuple[Path, dict[str, int]]
anonymize_file(source_path) -> tuple[Path, dict[str, int]]
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

## Report Contents

The report contains only safe metadata:

- status,
- input type,
- output type,
- counters by supported category,
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
- replacement maps,
- full input paths,
- full input filenames,
- logs containing document content.

## Safety Assumptions

The report module receives only counters and file-type metadata. It does not
read source documents and does not receive original source text.

Manual review is still required. A safe report confirms what the tool replaced,
but it does not prove the whole document is anonymized.

## How to Test

Run:

```bash
python -m unittest discover -s tests
```

The Stage 6 tests cover report text generation, report path naming, safe report
content, TXT integration, DOCX integration, PDF integration, and dispatcher
report safety.

## Known Limitations

- The report is a plain TXT file only.
- The report contains counters only, not a detailed audit trail.
- No replacement map is created.
- No source filename is written into the report body.
- The report does not guarantee complete anonymization.
