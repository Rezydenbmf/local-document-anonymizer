# Roadmap

| Stage | Goal | Description | Status | Main Limitations |
| --- | --- | --- | --- | --- |
| Stage 0 | Repository skeleton | Create structure, placeholder code, synthetic samples, and documentation. | Complete | Foundation only. |
| Stage 1 | Plain text anonymization engine | Add narrow rule-based detection and label replacement for plain text. | Complete | Plain Python strings only; no file workflow. |
| Stage 2 | TXT file input/output | Read TXT files and save anonymized TXT copies. | Complete | TXT-only stage; DOCX is handled in Stage 3. |
| Stage 3 | DOCX support | Extract text from basic DOCX paragraphs and simple tables, then write an anonymized `_ANON.docx` copy. | Complete | Basic formatting only; no advanced DOCX elements. |
| Stage 4 | Text-based PDF support | Extract text from text-based PDFs and save anonymized TXT output. | Complete | No OCR, scanned PDFs, layout preservation, or anonymized PDF output. |
| Stage 5 | Simple Tkinter GUI | Add a small local desktop interface for one selected supported file. | Complete | No preview, editing, drag and drop, batch processing, OCR, or PDF writing. |
| Stage 6 | Reports without source data | Generate safe reports with labels and counts only. | Complete | No source values or replacement maps. |
| Stage 7 | Portfolio polish and release review | Review README, user docs, technical docs, existing tests, security assumptions, roadmap, and portfolio text. | Complete | Documentation and review only; no new features or scope expansion. |
| Stage 8 | Private sensitive terms dictionary | Let the user load a private local dictionary such as `term = [LABEL]`, apply longer terms first, and report only labels and counts. | Complete | Stage 8 started with literal matching only; real dictionaries must stay out of git; no replacement map or automatic entity detection. |
| Stage 9 | Post-anonymization audit | Check `_ANON` output text for conservative suspicious remaining patterns and add safe audit status and counters to the report and GUI. | Complete | Warning layer only; no guarantee of complete anonymization, source values, snippets, dictionary terms, replacement map, OCR, AI, or database. |
| Stage 10.1 | Manual validation fixes | Repair private dictionary GUI/dispatcher flow, add safe dictionary status to GUI and reports, and audit remaining loaded dictionary terms. | Complete | No OCR, AI, batch processing, database, replacement map, or output-folder workflow. |
| Stage 10.2 | Manual GUI smoke test | Confirm the dictionary path flow manually with small synthetic UTF-8 files. | Complete | Manual validation only; no new runtime features. |
| Stage 11 | Smart dictionary foundation and README polish | Add dictionary aliases, case-insensitive matching, whitespace-tolerant term matching, synthetic dictionary candidate/seed examples, focused tests, and a stronger portfolio README. | Complete | Deterministic dictionary matching only; no fuzzy matching, inflection handling, NER, OCR, AI, APIs, database, batch processing, or replacement map. |
| Stage 12 | Safe output workspace and batch processing | Let the user select multiple supported files and an output folder, save all generated files there, avoid silent overwrites with numbered names, continue after per-file errors, and write a safe batch summary report. | Current | Sequential batch only; no drag and drop, preview, editor, OCR, AI, APIs, NER, database, or automatic approval. |
| Later | OCR | Consider scanned document support. | Not planned for MVP | Requires explicit approval. |
| Later | Installer | Package for easier desktop use. | Not planned for MVP | Platform-specific work. |
| Later | Better NLP | Improve detection quality. | Not planned for MVP | No AI dependency without approval. |
| Later | Stronger entity detection | Add more reliable names, addresses, organizations, and context-aware categories. | Not planned for MVP | Requires careful tests and privacy review. |
| Later | Packaging/release | Prepare distributable releases and release notes. | Not planned for MVP | Must avoid bundling private data, logs, or generated outputs. |
