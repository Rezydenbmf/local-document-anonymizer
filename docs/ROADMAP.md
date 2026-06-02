# Roadmap

| Stage | Goal | Description | Status | Main Limitations |
| --- | --- | --- | --- | --- |
| Stage 0 | Repository skeleton | Create structure, placeholder code, synthetic samples, and documentation. | Complete | Foundation only. |
| Stage 1 | Plain text anonymization engine | Add narrow rule-based detection and label replacement for plain text. | Complete | Plain Python strings only; no file workflow. |
| Stage 2 | TXT file input/output | Read TXT files and save anonymized TXT copies. | Complete | No DOCX or PDF yet. |
| Stage 3 | DOCX support | Extract text from DOCX and write anonymized DOCX or text output. | Planned | Requires careful dependency review. |
| Stage 4 | Text-based PDF support | Extract text from text-based PDFs. | Planned | No OCR or scanned PDFs. |
| Stage 5 | Simple Tkinter GUI | Add a small local desktop interface. | Planned | Basic workflow only. |
| Stage 6 | Reports without source data | Generate safe reports with labels and counts only. | Planned | No source values or replacement maps. |
| Stage 7 | Tests and portfolio polish | Expand tests and documentation for review. | Planned | Must stay synthetic-data only. |
| Later | OCR | Consider scanned document support. | Not planned for MVP | Requires explicit approval. |
| Later | Batch processing | Process multiple files. | Not planned for MVP | Higher safety and review risk. |
| Later | Installer | Package for easier desktop use. | Not planned for MVP | Platform-specific work. |
| Later | Better NLP | Improve detection quality. | Not planned for MVP | No AI dependency without approval. |
