# Module: Repository Skeleton

## Purpose

This stage creates the repository foundation: structure, placeholder code, documentation, synthetic sample data, and basic tests.

## Why it exists

The repository starts with structure and documentation before full implementation so that scope, safety rules, and module boundaries are clear.

## Related files

- `README.md`
- `AGENTS.md`
- `.gitignore`
- `requirements.txt`
- `src/main.py`
- `src/anonymizer.py`
- `src/file_readers.py`
- `src/file_writers.py`
- `src/report.py`
- `src/gui.py`
- `tests/test_anonymizer.py`
- `tests/sample_data/sample_01.txt`
- `tests/sample_data/sample_02.txt`
- `docs/`
- `examples/`

## How it works

This is a foundation stage. Later stage documents describe the implemented
anonymizer, file workflows, and GUI behavior.

## Inputs

No real user input is processed yet.

## Outputs

The stage outputs repository structure, placeholder code, documentation, and synthetic test files.

## Safety assumptions

- No real data is stored in the repository.
- No network calls are added.
- No APIs, AI services, OCR, local LLMs, databases, or large frameworks are added.
- No commits should include sensitive files.
- Reports must not contain original source values.

## How to test

Inspect the repository structure and run:

```bash
python -m unittest discover -s tests
```

Later stage tests verify the implemented anonymizer, file workflows, and GUI
workflow dispatcher.

## Known limitations

This Stage 0 document is historical. Later module documents describe the
implemented engine, TXT, DOCX, PDF, GUI, and safe report behavior.

## Future improvements

Later stages add the anonymizer engine, TXT input/output, DOCX support, PDF
support, GUI, and reports. Future work beyond the current MVP should be planned
as separate approved stages.
