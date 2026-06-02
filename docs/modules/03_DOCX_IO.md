# Module: DOCX File Input and Output

## Purpose

This module implements Stage 3: local DOCX reading, anonymization through the
existing plain text engine, and saving a separate anonymized DOCX copy.

## Related files

- `src/file_readers.py`
- `src/file_writers.py`
- `src/anonymizer.py`
- `tests/test_docx_io.py`

## Runtime dependency

Stage 3 adds one runtime dependency:

```text
python-docx
```

The dependency is used locally for DOCX reading and writing. It does not add
internet calls, APIs, cloud services, AI, OCR, local LLMs, databases, or batch
processing.

## Public API

```python
read_docx_file(file_path: str | Path) -> str
extract_text(file_path: str | Path) -> str
build_anonymized_docx_path(source_path: str | Path) -> Path
save_anonymized_docx_copy(
    source_path: str | Path,
    anonymize: Callable[[str], tuple[str, dict[str, int]]],
) -> tuple[Path, dict[str, int]]
anonymize_docx_file(source_path: str | Path) -> tuple[Path, dict[str, int]]
```

`anonymize_docx_file(...)` passes DOCX text through the existing
`anonymize_text(text: str)` engine. Stage 3 does not create a separate DOCX
anonymization engine.

## How it works

The DOCX workflow is:

1. `read_docx_file()` extracts basic paragraph text and simple table cell text.
2. `anonymize_docx_file()` calls `save_anonymized_docx_copy(...)` with the
   existing `anonymize_text(...)` function.
3. `save_anonymized_docx_copy(...)` opens the source DOCX locally, anonymizes
   supported paragraph and simple table text, and saves a separate copy.
4. The output file is saved next to the source with an `_ANON` suffix.

Example:

```text
document.docx -> document_ANON.docx
```

The original DOCX file is not modified.

## Safety assumptions

- DOCX files are read and written locally.
- The original source file is left unchanged.
- The output file receives the `_ANON` suffix.
- No replacement map is created.
- No source values are written to reports, metadata, or counters.
- The integration helper returns only the output path and category counters.
- Counters contain category names and counts only.
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
values, TXT regression coverage, and unsupported extension errors.

## Known limitations

- Detection quality is still limited by the Stage 1 regex engine.
- DOCX formatting preservation is basic only.
- Advanced DOCX elements are not scanned or rewritten.
- There is no PDF, GUI, OCR, AI, API integration, cloud service, database,
  batch processing, replacement map, or final report file generation.
