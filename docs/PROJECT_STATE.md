# Project State

## Current Status

The project is in Stage 2: TXT file input/output.

The repository now contains a narrow regex-based engine that accepts a Python
string and returns anonymized text plus category counters. It also contains
TXT-only file readers, writers, and a small integration helper for saving an
anonymized TXT copy.

## What Exists

- Repository structure.
- Regex-based plain text anonymization in `src/anonymizer.py`.
- Supported Stage 1 categories: `PESEL`, `EMAIL`, `TELEFON`, and `DATA`.
- UTF-8 TXT reading in `src/file_readers.py`.
- UTF-8 TXT anonymized copy writing in `src/file_writers.py`.
- TXT integration helper `anonymize_txt_file(...)`.
- Unit tests for the Stage 1 anonymizer using synthetic values only.
- Unit tests for Stage 2 TXT input/output using synthetic temporary files only.
- Synthetic sample text files in `tests/sample_data/`.
- Project, user, security, roadmap, and module documentation.
- `.gitignore` rules for private data and local artifacts.

## What Does Not Exist Yet

- DOCX or PDF processing.
- GUI workflow.
- OCR, AI, API calls, cloud services, local LLMs, or databases.
- Final report file generation.
- Names, surnames, cities, organizations, or context-based detection.

## How to Run

Run the placeholder entry point:

```bash
python src/main.py
```

Run tests:

```bash
python -m unittest discover -s tests
```

## Current Limitations

- The core engine processes only a plain Python string.
- File input/output supports only `.txt` files.
- TXT outputs are written next to the source with an `_ANON` suffix.
- Reports contain only category counters and no source values.
- Date detection is limited to high-confidence numeric formats.
- Phone detection is intentionally conservative.
- Address and postal-code detection are not implemented in Stage 1.
- DOCX, PDF, report files, and GUI remain unimplemented.

## Last Completed Stage

Stage 2: TXT file input/output.

## Next Logical Step

Stage 3: add DOCX support after explicit dependency and safety review.

## Warning

This repository is still an early-stage tool. Do not use it to anonymize real
documents without manual review and without completing the later file workflow
and safety checks.
