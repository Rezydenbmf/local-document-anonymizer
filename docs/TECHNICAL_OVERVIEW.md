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

`main.py` is the application entry point. It starts the Stage 5 Tkinter GUI.

`gui.py` contains the Stage 5 Tkinter desktop interface. It lets the user
select one supported file, run anonymization, and view selected path, status,
category counters, output path, and the manual review warning.

`file_readers.py` reads UTF-8 TXT files, extracts basic text from local DOCX files, and extracts text from text-based PDFs. DOCX extraction covers normal paragraphs and simple table cells. PDF extraction requires an existing text layer and does not include OCR.

`anonymizer.py` contains the Stage 1 plain text anonymization engine. It accepts a Python string, replaces supported regex matches with placeholders, and returns category counters only. It also exposes the Stage 2 `anonymize_txt_file(...)` helper, the Stage 3 `anonymize_docx_file(...)` helper, the Stage 4 `anonymize_pdf_file(...)` helper, and the Stage 5 `anonymize_file(...)` dispatcher. These helpers call the existing `anonymize_text(...)` engine and return only the output path plus category counters.

`file_writers.py` saves anonymized TXT, DOCX, and PDF-to-TXT copies without modifying original files. The output filename receives the `_ANON` suffix. For example, `document.txt` becomes `document_ANON.txt`, `document.docx` becomes `document_ANON.docx`, and `document.pdf` becomes `document_ANON.txt`.

DOCX writing uses `python-docx` locally. It updates supported paragraph and simple table text in a copy of the original document. Basic paragraph and run formatting is preserved when possible, but full DOCX fidelity is not guaranteed.

PDF reading uses `pypdf` locally. Stage 4 extracts text and writes anonymized
TXT output only. It does not create anonymized PDF files, does not preserve PDF
layout, and does not modify the original PDF.

`report.py` will build safe reports without original sensitive source values. In Stage 0 it returns placeholder metadata only.

## Safety Design

The project is local-first and offline. It must not add cloud services, APIs, network calls, AI services, OCR, databases, or large dependencies without explicit approval.

Reports must not include original sensitive source values. The application must not store replacement maps containing original values.

Stage 5 does not create a replacement map, does not create report files, and
does not include source values in returned counters or GUI status. The project
still does not use internet calls, APIs, cloud services, AI services, OCR,
local LLMs, databases, drag and drop, or batch processing.

## GUI Limitations

Stage 5 is a simple workflow shell. It does not preview document content, edit
output, process multiple files, write anonymized PDF files, or generate final
reports. It calls the existing file workflow helpers instead of parsing files
inside the GUI layer.

## DOCX Limitations

Stage 3 does not handle headers, footers, comments, footnotes, form fields, text
inside images, or advanced DOCX elements. Manual review remains required before
using any anonymized DOCX output.

## PDF Limitations

Stage 4 supports only PDFs that already contain extractable text. Scanned PDFs
are not supported, OCR is not included, PDF layout preservation is not
guaranteed, and PDF input produces TXT output only.
