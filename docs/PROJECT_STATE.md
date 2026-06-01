# Project State

## Current Status

The project is in Stage 1: plain text anonymization engine.

The repository now contains a narrow regex-based engine that accepts a Python
string and returns anonymized text plus category counters. The application is
not yet a complete document anonymization tool.

## What Exists

- Repository structure.
- Regex-based plain text anonymization in `src/anonymizer.py`.
- Supported Stage 1 categories: `PESEL`, `EMAIL`, `TELEFON`, and `DATA`.
- Unit tests for the Stage 1 anonymizer using synthetic values only.
- Synthetic sample text files in `tests/sample_data/`.
- Project, user, security, roadmap, and module documentation.
- `.gitignore` rules for private data and local artifacts.

## What Does Not Exist Yet

- TXT file input or output.
- DOCX or PDF processing.
- GUI workflow.
- OCR, AI, API calls, cloud services, local LLMs, or databases.
- Final output file writing.
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

- The engine processes only a plain Python string.
- Reports contain only category counters and no source values.
- Date detection is limited to high-confidence numeric formats.
- Phone detection is intentionally conservative.
- Address and postal-code detection are not implemented in Stage 1.
- File readers, file writers, report files, and GUI remain placeholders.

## Last Completed Stage

Stage 1: regex-based plain text anonymization engine.

## Next Logical Step

Stage 2: add TXT file input and output around the existing plain text engine.

## Warning

This repository is still an early-stage tool. Do not use it to anonymize real
documents without manual review and without completing the later file workflow
and safety checks.
