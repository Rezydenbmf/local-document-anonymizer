# Technical Overview

## Current Flow

```text
input file
-> text extraction
-> optional dictionary path loading
-> optional private sensitive terms replacement
-> anonymization
-> output file
-> post-anonymization audit
-> safe report
-> manual review outside the application
```

## Module Responsibilities

`main.py` is the application entry point. It starts the Stage 5 Tkinter GUI.

`gui.py` contains the Tkinter desktop interface. It lets the user select one
supported file, optionally select a private sensitive terms file, run
anonymization, and view selected path, safe dictionary status, category
counters, audit status, audit counters, output path, report path, and the
manual review warning. It stores only the selected dictionary path and lets the
workflow load the file. It does not display dictionary contents, original
detected values, text snippets, or dictionary terms.

`file_readers.py` reads UTF-8 TXT files, extracts basic text from local DOCX files, and extracts text from text-based PDFs. DOCX extraction covers normal paragraphs and simple table cells. PDF extraction requires an existing text layer and does not include OCR.

`sensitive_terms.py` contains private dictionary support. It loads a UTF-8
local dictionary file, parses `term = [LABEL]` and
`alias | alias = [LABEL]` lines, ignores blank lines and comments, validates
malformed lines with safe line-number errors, applies longer aliases before
shorter aliases, and returns counters by label only. Stage 11 matching is
case-insensitive and tolerates extra internal whitespace inside matched
dictionary aliases.

`anonymizer.py` contains the plain text anonymization engine. It accepts a
Python string, optionally applies private sensitive terms, replaces supported
regex matches with placeholders, and returns category counters only. The file
workflows and dispatcher can also accept `sensitive_terms_path`; they load the
dictionary centrally, build safe dictionary metadata, and keep invalid
dictionaries non-fatal while marking the dictionary status as `invalid`. It
also exposes the Stage 2 `anonymize_txt_file(...)` helper, the Stage 3
`anonymize_docx_file(...)` helper, the Stage 4 `anonymize_pdf_file(...)`
helper, and the Stage 5 `anonymize_file(...)` dispatcher. Stage 9 adds
`_with_audit` variants for TXT, DOCX, PDF, and dispatcher workflows. The
existing helpers still return only the output path plus category counters, but
they also run the audit and save it into the safe report.

`audit.py` contains the Stage 9 post-anonymization audit. It checks already
anonymized output text for conservative suspicious remaining patterns. When a
dictionary loaded successfully, the workflow passes those terms into the audit
so remaining dictionary aliases are counted as `SENSITIVE_DICTIONARY_TERM`
using the same Stage 11 case-insensitive and whitespace-tolerant matching
semantics as anonymization. The audit returns only status, category counters,
and a manual review flag. It never returns source values, text snippets,
private dictionary terms, document text, or replacement maps.

`file_writers.py` saves anonymized TXT, DOCX, and PDF-to-TXT copies without modifying original files. The output filename receives the `_ANON` suffix. For example, `document.txt` becomes `document_ANON.txt`, `document.docx` becomes `document_ANON.docx`, and `document.pdf` becomes `document_ANON.txt`. It also builds safe report paths with the `_RAPORT.txt` suffix.

DOCX writing uses `python-docx` locally. It updates supported paragraph and simple table text in a copy of the original document. Basic paragraph and run formatting is preserved when possible, but full DOCX fidelity is not guaranteed.

PDF reading uses `pypdf` locally. Stage 4 extracts text and writes anonymized
TXT output only. It does not create anonymized PDF files, does not preserve PDF
layout, and does not modify the original PDF.

`report.py` builds and saves safe TXT reports without original sensitive source
values. It receives only status, input type, output type, anonymization
category counters, safe dictionary status metadata, dictionary label counters,
audit status, audit counters, and optional category ordering. Dictionary
counters are labels only, such as `IMIE NAZWISKO: 2`; original dictionary
terms are not passed to the report module.

## Safety Design

The project is local-first and offline. It must not add cloud services, APIs, network calls, AI services, OCR, databases, or large dependencies without explicit approval.

Reports must not include original sensitive source values. The application must not store replacement maps containing original values.

Private dictionary support does not create a replacement map and does not
include source values, aliases, or private dictionary terms in returned
counters, report files, or GUI status. The real private dictionary must not be
committed; it should live outside the repository or inside an ignored folder
such as `private/`.

Stage 9 audit results are safe metadata only. They include warning categories
and counts, not original values, text snippets, dictionary terms, full document
text, or replacement maps. Audit status `ok` does not prove complete
anonymization; manual review remains required.

Dictionary metadata is safe metadata only. It contains status names, booleans
implied by status, label names, and counters. It does not contain dictionary
source aliases, document fragments, source file paths, or replacement maps.

The project still does not use internet calls, APIs, cloud services, AI
services, OCR, local LLMs, databases, drag and drop, or batch processing.

## GUI Limitations

The GUI is a simple workflow shell. It does not preview document content, edit
output, display dictionary contents, display audit snippets, process multiple
files, write anonymized PDF files, or generate detailed audit reports beyond
safe counters. It calls the existing file workflow helpers instead of parsing
files inside the GUI layer.

## Private Dictionary Limitations

Stage 11 private dictionary matching is deterministic, case-insensitive, and
whitespace-tolerant for user-specified aliases. It helps the user manually
specify known terms and variants, but it does not add fuzzy matching,
inflection handling, automatic names, cities, organizations, addresses,
context-based detection, OCR, AI, APIs, local LLMs, cloud services, databases,
or a replacement map.

## DOCX Limitations

Stage 3 does not handle headers, footers, comments, footnotes, form fields, text
inside images, or advanced DOCX elements. Manual review remains required before
using any anonymized DOCX output.

## PDF Limitations

Stage 4 supports only PDFs that already contain extractable text. Scanned PDFs
are not supported, OCR is not included, PDF layout preservation is not
guaranteed, and PDF input produces TXT output only. A TXT and PDF with the same
base name in the same folder can still produce confusing or colliding
`_ANON.txt` and `_RAPORT.txt` paths; Stage 10.1 documents this rather than
adding a new output-folder workflow.
