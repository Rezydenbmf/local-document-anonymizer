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

`file_readers.py` reads UTF-8 TXT files in Stage 2. DOCX and PDF are not supported yet and other extensions are rejected.

`anonymizer.py` contains the Stage 1 plain text anonymization engine. It accepts a Python string, replaces supported regex matches with placeholders, and returns category counters only. It also exposes the Stage 2 `anonymize_txt_file(...)` helper, which reads a TXT file, calls `anonymize_text(...)`, writes the anonymized copy, and returns only the output path plus category counters.

`file_writers.py` saves anonymized UTF-8 TXT copies without modifying original files. The output filename receives the `_ANON` suffix, for example `document.txt` becomes `document_ANON.txt`.

`report.py` will build safe reports without original sensitive source values. In Stage 0 it returns placeholder metadata only.

## Safety Design

The project is local-first and offline. It must not add cloud services, APIs, network calls, AI services, OCR, databases, or large dependencies without explicit approval.

Reports must not include original sensitive source values. The application must not store replacement maps containing original values.

Stage 2 does not create a replacement map, does not create report files, and does not include source values in returned counters.
