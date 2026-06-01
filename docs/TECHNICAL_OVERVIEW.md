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

`main.py` is the application entry point. It currently prints a skeleton status message.

`gui.py` will contain the future Tkinter desktop interface. It is currently a placeholder.

`file_readers.py` will extract text from TXT, DOCX, and text-based PDF files. It is currently a placeholder.

`anonymizer.py` contains the Stage 1 plain text anonymization engine. It accepts a Python string, replaces supported regex matches with placeholders, and returns category counters only.

`file_writers.py` will save anonymized copies without modifying original files. It is currently a placeholder.

`report.py` will build safe reports without original sensitive source values. In Stage 0 it returns placeholder metadata only.

## Safety Design

The project is local-first and offline. It must not add cloud services, APIs, network calls, AI services, OCR, databases, or large dependencies without explicit approval.

Reports must not include original sensitive source values. The application must not store replacement maps containing original values.
