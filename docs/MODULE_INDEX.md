# Module Index

| Module name | Related files | Responsibility | Current status | Documentation file | Known limitations |
| --- | --- | --- | --- | --- | --- |
| Repository Skeleton | `README.md`, `AGENTS.md`, `docs/`, `src/`, `tests/` | Provide the project foundation. | Complete for Stage 0 | `docs/modules/00_REPO_SKELETON.md` | Foundation only; later modules add behavior. |
| Application Entry Point | `src/main.py` | Start the application. | Placeholder | `docs/modules/00_REPO_SKELETON.md` | Prints status only. |
| GUI Placeholder | `src/gui.py` | Future desktop interface. | Placeholder | `docs/modules/00_REPO_SKELETON.md` | No GUI implemented. |
| File Readers | `src/file_readers.py` | Read supported Stage 2 TXT input as UTF-8 text. | Complete for Stage 2 | `docs/modules/02_TXT_IO.md` | TXT only; DOCX, PDF, and other extensions are rejected. |
| Plain Text Anonymizer Engine | `src/anonymizer.py` | Replace supported sensitive values in a plain Python string and return category counters. | Complete for Stage 1 | `docs/modules/01_ANONYMIZER_ENGINE.md` | Regex-only; no names, cities, organizations, context detection, or addresses. |
| TXT File Workflow | `src/anonymizer.py`, `src/file_readers.py`, `src/file_writers.py` | Read a TXT file, call `anonymize_text()`, and save a separate `_ANON.txt` copy. | Complete for Stage 2 | `docs/modules/02_TXT_IO.md` | No DOCX, PDF, GUI, OCR, batch processing, replacement map, or final report file. |
| File Writers | `src/file_writers.py` | Save anonymized TXT output without modifying the original file. | Complete for Stage 2 | `docs/modules/02_TXT_IO.md` | TXT only; writes content supplied by the caller and does not create reports. |
| Report Placeholder | `src/report.py` | Future safe report file generation. | Placeholder | `docs/modules/00_REPO_SKELETON.md` | Placeholder metadata only; Stage 1 engine returns counters directly. |
| Anonymizer Tests | `tests/test_anonymizer.py`, `tests/test_txt_io.py`, `tests/sample_data/` | Verify Stage 1 engine behavior and Stage 2 TXT workflow with synthetic data. | Complete for Stage 2 | `docs/modules/01_ANONYMIZER_ENGINE.md`, `docs/modules/02_TXT_IO.md` | Tests do not cover DOCX, PDF, GUI, OCR, AI, APIs, or real documents. |
