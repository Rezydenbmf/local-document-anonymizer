# Module: Safe Report File Output

## Purpose

This module implements safe report file output without source values or
replacement maps. Stage 8 allows reports to include private dictionary labels
and counts, but never original dictionary terms or aliases. Stage 9 adds a safe
post-anonymization audit section with audit status and counters only. Stage
10.1 adds a safe dictionary section with used/status/matches-found metadata and
dictionary label counters only. Stage 12 adds safe batch summary reports.
Stage 13 adds safe manual review status and summary metadata in `src/review.py`
using the same no-source-data reporting conventions.

## Related files

- `src/report.py`
- `src/file_writers.py`
- `src/anonymizer.py`
- `src/gui.py`
- `src/review.py`
- `src/sensitive_terms.py`
- `tests/test_report.py`
- `tests/test_review_workflow.py`
- `tests/test_sensitive_terms.py`

## Public API

```python
build_report_text(...) -> str
save_report_file(...) -> Path
build_report_path(source_path: str | Path) -> Path
build_batch_summary_text(...) -> str
save_batch_summary_file(...) -> Path
build_review_summary_text(...) -> str
save_review_files(...) -> ReviewSaveResult
```

The existing anonymization helpers keep their Stage 2-5 return values:

```python
anonymize_txt_file(source_path, sensitive_terms=None, sensitive_terms_path=None, output_dir=None) -> tuple[Path, dict[str, int]]
anonymize_docx_file(source_path, sensitive_terms=None, sensitive_terms_path=None, output_dir=None) -> tuple[Path, dict[str, int]]
anonymize_pdf_file(source_path, sensitive_terms=None, sensitive_terms_path=None, output_dir=None) -> tuple[Path, dict[str, int]]
anonymize_file(source_path, sensitive_terms=None, sensitive_terms_path=None, output_dir=None) -> tuple[Path, dict[str, int]]
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

Stage 12 saves these generated files in the selected output folder. Original
files are not modified. Existing generated files are not overwritten silently;
numbered names such as `document_RAPORT_2.txt` are used when needed.

Batch summary reports are saved as:

```text
_BATCH_SUMMARY.txt
_BATCH_SUMMARY_2.txt
_BATCH_SUMMARY_3.txt
```

Manual review metadata files are saved as:

```text
_REVIEW_STATUS.json
_REVIEW_SUMMARY.txt
_REVIEW_SUMMARY_2.txt
```

`_REVIEW_STATUS.json` stores the latest safe status manifest for an output
folder. `_REVIEW_SUMMARY.txt` uses collision-safe numbering so older summaries
are not silently overwritten.

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

The batch summary contains only safe metadata:

- input file count,
- success count,
- error count,
- aggregate category counters,
- audit status counts,
- manual review requirement,
- safe input filenames,
- safe generated output filenames,
- safe generated report filenames,
- controlled safe error descriptions.

The manual review summary contains only safe metadata:

- number of generated outputs detected for review,
- count of `approved`, `needs_review`, and `rejected` statuses,
- manual review completed yes/no,
- statement that decisions are manual user decisions,
- safe generated output basenames,
- safe report basenames or a missing-report marker,
- safe batch summary basenames when present,
- confirmation that source data and replacement maps are not stored.

## Deliberately Excluded

The report must not contain:

- original document text,
- detected original sensitive values,
- original PESEL values,
- original e-mail addresses,
- original phone numbers,
- original dates in source form,
- original private dictionary aliases or terms,
- text snippets,
- audit source values,
- replacement maps,
- full input paths,
- full input filenames,
- logs containing document content.

Batch summary reports may contain safe filenames, but they must not contain
full paths, source document text, private dictionary terms, dictionary aliases,
raw exception messages, or replacement maps.

Manual review status and summary files may contain safe generated basenames,
but they must not contain full paths, source document text, anonymized document
text, document excerpts, original sensitive values, private dictionary terms,
dictionary aliases, tracebacks, automatic approval claims, or replacement maps.

Dictionary status meanings:

- `not selected`: no dictionary path was provided.
- `loaded`: a dictionary path was provided and parsed successfully.
- `invalid`: a dictionary path was provided but could not be loaded or parsed.

`Dictionary used: yes` means the dictionary loaded successfully. `Dictionary
matches found: yes` means at least one dictionary replacement occurred. Label
counters are grouped by dictionary label/category only.

## Safety Assumptions

The report module receives only counters, safe dictionary metadata, audit
metadata, file-type metadata, safe filenames, and controlled batch error
descriptions. It does not read source documents and does not receive original
source text, original private dictionary aliases or terms, text snippets, raw
exception text, or replacement maps.

Manual review is still required. A safe report confirms what the tool replaced
and what the audit warned about, but it does not prove the whole document is
anonymized.

Stage 13 review metadata records the user's manual decision. `approved` means
the user approved the file after review; it is not produced automatically from
audit status or report contents.

## How to Test

Run:

```bash
python -m unittest discover -s tests
```

The tests cover report text generation, report path naming, safe report
content, TXT integration, DOCX integration, PDF integration, dispatcher report
safety, private dictionary report safety, post-anonymization audit report
safety, Stage 12 batch summary safety, and Stage 13 manual review summary
safety.

## Known Limitations

- The report is a plain TXT file only.
- The report contains anonymization and audit counters only, not a detailed
  audit trail.
- No replacement map is created.
- No original private dictionary aliases or terms are written to reports.
- Per-file reports do not write source filenames into the report body.
- Batch summaries write safe filenames only, not full paths.
- Review summaries write generated basenames only, not document contents or
  full paths.
- The report does not guarantee complete anonymization.
