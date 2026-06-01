# Project State

## Current Status

The project is in Stage 0: repository skeleton. It contains placeholder Python modules, synthetic sample data, basic tests, and project documentation.

The application is not usable for real anonymization yet.

## What Exists

- Repository structure.
- Placeholder Python modules in `src/`.
- Placeholder tests in `tests/`.
- Synthetic sample text files in `tests/sample_data/`.
- Project, user, security, roadmap, and module documentation.
- `.gitignore` rules for private data and local artifacts.

## What Does Not Exist Yet

- Real sensitive data detection.
- Real anonymization logic.
- TXT, DOCX, or PDF processing.
- GUI workflow.
- Output file writing.
- Final report generation.

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

- The anonymizer returns input text unchanged.
- File readers and writers are placeholders.
- The GUI is a placeholder.
- Reports contain only placeholder metadata and no source values.

## Last Completed Stage

Stage 0: repository skeleton, placeholder code, synthetic test data, and documentation.

## Next Logical Step

Stage 1: implement a narrow plain text anonymization engine using synthetic test data only.

## Warning

This repository currently contains only a skeleton and placeholders. Do not use it to anonymize real documents.
