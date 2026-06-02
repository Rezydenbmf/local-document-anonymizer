# Technical Overview

## Planned Flow

```text
input file
-> text extraction
-> anonymization
-> preview/manual review
-> output file
-> report
```

## Module Responsibilities

`main.py` is the application entry point. It currently prints a placeholder status message.

`gui.py` will contain the future Tkinter desktop interface. It is currently a placeholder.

`file_readers.py` reads UTF-8 TXT files and extracts basic text from local DOCX files in Stage 3. DOCX extraction covers normal paragraphs and simple table cells. PDF and other extensions are rejected.

`anonymizer.py` contains the Stage 1 plain text anonymization engine. It accepts a Python string, replaces supported regex matches with placeholders, and returns category counters only. It also exposes the Stage 2 `anonymize_txt_file(...)` helper and the Stage 3 `anonymize_docx_file(...)` helper. Both helpers call the existing `anonymize_text(...)` engine and return only the output path plus category counters.

`file_writers.py` saves anonymized TXT and DOCX copies without modifying original files. The output filename receives the `_ANON` suffix, for example `document.txt` becomes `document_ANON.txt` and `document.docx` becomes `document_ANON.docx`.

DOCX writing uses `python-docx` locally. It updates supported paragraph and simple table text in a copy of the original document. Basic paragraph and run formatting is preserved when possible, but full DOCX fidelity is not guaranteed.

`report.py` will build safe reports without original sensitive source values. In Stage 0 it returns placeholder metadata only.

## Safety Design

The project is local-first and offline. It must not add cloud services, APIs, network calls, AI services, OCR, databases, or large dependencies without explicit approval.

Reports must not include original sensitive source values. The application must not store replacement maps containing original values.

Stage 3 does not create a replacement map, does not create report files, and does not include source values in returned counters. The project still does not use internet calls, APIs, cloud services, AI services, OCR, local LLMs, databases, or batch processing.

## DOCX Limitations

Stage 3 does not handle headers, footers, comments, footnotes, form fields, text
inside images, or advanced DOCX elements. Manual review remains required before
using any anonymized DOCX output.
