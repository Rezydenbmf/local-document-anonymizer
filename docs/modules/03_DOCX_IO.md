# Module: DOCX File Input and Output

## Purpose

This module implements Stage 3: local DOCX reading, anonymization through the
existing plain text engine, and saving a separate anonymized DOCX copy. Stage 6
adds safe report file output after successful anonymization. Stage 8 lets the
workflow receive optional private sensitive terms. Stage 9 audits the saved
anonymized DOCX output text before saving the safe report. Stage 10.1 lets the
workflow receive a dictionary path and report safe dictionary status. Stage 12
lets the workflow write to a selected output folder with collision-safe names.

## Related files

- `src/file_readers.py`
- `src/file_writers.py`
- `src/anonymizer.py`
- `src/sensitive_terms.py`
- `tests/test_docx_io.py`
- `tests/test_sensitive_terms.py`

## Runtime dependency

Stage 3 adds one runtime dependency:

```text
python-docx
```

The dependency is used locally for DOCX reading and writing. It does not add
internet calls, APIs, cloud services, AI, OCR, local LLMs, databases, or batch
logic.

## Public API

```python
read_docx_file(file_path: str | Path) -> str
extract_text(file_path: str | Path) -> str
build_anonymized_docx_path(source_path: str | Path) -> Path
build_report_path(source_path: str | Path) -> Path
save_anonymized_docx_copy(
    source_path: str | Path,
    anonymize: Callable[[str], tuple[str, dict[str, int]]],
    anonymize_run: Callable[[str], tuple[str, dict[str, int]]] | None = None,
    output_dir=None,
) -> tuple[Path, dict[str, int]]
anonymize_docx_file(source_path: str | Path, sensitive_terms=None, sensitive_terms_path=None, output_dir=None) -> tuple[Path, dict[str, int]]
anonymize_docx_file_with_audit(source_path: str | Path, sensitive_terms=None, sensitive_terms_path=None, output_dir=None)
```

`anonymize_docx_file(...)` passes DOCX text through the existing
`anonymize_text(text: str, sensitive_terms=None)` engine. Stage 3 does not
create a separate DOCX anonymization engine.

## How it works

The DOCX workflow is:

1. `read_docx_file()` extracts basic paragraph text and simple table cell text.
2. `anonymize_docx_file()` loads an optional dictionary path, then calls
   `save_anonymized_docx_copy(...)` with the existing `anonymize_text(...)`
   function.
3. `save_anonymized_docx_copy(...)` opens the source DOCX locally, anonymizes
   supported paragraph and simple table text, and saves a separate copy.
4. The output file is saved with an `_ANON` suffix, in the selected output
   folder when one is provided.
5. `audit_text()` checks text extracted from the saved `_ANON.docx` copy using
   the same basic DOCX text scope.
6. A safe report file is saved with a `_RAPORT.txt` suffix. The report includes
   safe dictionary status and label counters only.

Example:

```text
output folder / document_ANON.docx
output folder / document_RAPORT.txt
```

The original DOCX file is not modified. Existing generated files are not
overwritten silently; numbered names are used when needed.

## Safety assumptions

- DOCX files are read and written locally.
- The original source file is left unchanged.
- The output file receives the `_ANON` suffix.
- The safe report file receives the `_RAPORT.txt` suffix.
- Generated files can be written to a selected output folder.
- Existing generated files are not overwritten silently.
- No replacement map is created.
- No source values are written to reports, metadata, or counters.
- The integration helper returns only the output path and category counters.
- Counters contain category names and counts only.
- Private dictionary terms are not written to reports, counters, or returned
  metadata.
- Dictionary workflow metadata contains only status names, labels, and
  counters.
- Audit results contain only status, category counters, and the manual review
  flag. They do not contain source values, snippets, dictionary terms, or a
  replacement map.
- Tests use only synthetic data and temporary files.

## Formatting behavior

Stage 3 preserves basic DOCX structure in a narrow MVP range:

- ordinary paragraphs,
- simple table cell paragraphs,
- paragraph placement,
- run formatting when replacements can be applied inside existing runs.

If a sensitive value is split across multiple runs, the module may simplify run
formatting in that paragraph to apply the anonymized text safely. Full DOCX
formatting fidelity is not promised.

## Unsupported DOCX elements

Stage 3 does not handle:

- headers,
- footers,
- comments,
- footnotes,
- form fields,
- text inside images,
- text boxes and advanced drawing elements,
- advanced DOCX fields or custom XML.

Manual review is still required before trusting or sharing anonymized DOCX
output.

## How to test

Run:

```bash
python -m unittest discover -s tests
```

The Stage 3 tests cover DOCX reading, `_ANON.docx` writing, original DOCX
preservation, DOCX anonymization integration, safe counters without source
values, TXT regression coverage, and unsupported extension errors. Stage 9
tests cover audit report safety and dispatcher audit metadata. Stage 10.1 tests
cover dictionary path replacement and report safety for DOCX. Stage 12 tests
cover DOCX processing through the batch workflow. Stage 24 tests cover the
malformed hyphenated person-name pattern in the DOCX workflow with synthetic
data, including Unicode dash variants and split runs.

## Known limitations

- Detection quality is still limited by the Stage 1 regex engine.
- Private dictionary matching is deterministic, case-insensitive, and
  whitespace-tolerant, but not fuzzy matching or automatic entity detection.
- DOCX formatting preservation is basic only.
- Advanced DOCX elements are not scanned or rewritten.
- There is no OCR, AI, API integration, cloud service, database, drag and drop,
  preview, editing, replacement map, or detailed audit report generation with
  source snippets.
- Text-based PDF input is handled by the separate Stage 4 PDF-to-TXT workflow.
- Stage 9 audit uses the existing basic DOCX text extraction scope and does not
  inspect unsupported DOCX elements.
