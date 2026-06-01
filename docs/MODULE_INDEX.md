# Module Index

| Module name | Related files | Responsibility | Current status | Documentation file | Known limitations |
| --- | --- | --- | --- | --- | --- |
| Repository Skeleton | `README.md`, `AGENTS.md`, `docs/`, `src/`, `tests/` | Provide the project foundation. | Complete for Stage 0 | `docs/modules/00_REPO_SKELETON.md` | Foundation only; later modules add behavior. |
| Application Entry Point | `src/main.py` | Start the application. | Placeholder | `docs/modules/00_REPO_SKELETON.md` | Prints status only. |
| GUI Placeholder | `src/gui.py` | Future desktop interface. | Placeholder | `docs/modules/00_REPO_SKELETON.md` | No GUI implemented. |
| File Readers Placeholder | `src/file_readers.py` | Future text extraction. | Placeholder | `docs/modules/00_REPO_SKELETON.md` | No TXT, DOCX, or PDF support yet. |
| Plain Text Anonymizer Engine | `src/anonymizer.py` | Replace supported sensitive values in a plain Python string and return category counters. | Complete for Stage 1 | `docs/modules/01_ANONYMIZER_ENGINE.md` | Regex-only; no names, cities, organizations, context detection, addresses, or file handling. |
| File Writers Placeholder | `src/file_writers.py` | Future anonymized output writing. | Placeholder | `docs/modules/00_REPO_SKELETON.md` | Does not write files yet. |
| Report Placeholder | `src/report.py` | Future safe report file generation. | Placeholder | `docs/modules/00_REPO_SKELETON.md` | Placeholder metadata only; Stage 1 engine returns counters directly. |
| Anonymizer Tests | `tests/test_anonymizer.py`, `tests/sample_data/` | Verify Stage 1 engine behavior with synthetic data. | Complete for Stage 1 | `docs/modules/01_ANONYMIZER_ENGINE.md` | Tests cover the in-memory engine only. |
