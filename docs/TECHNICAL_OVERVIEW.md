# Technical Overview

## Current Flow

```text
input file
-> text extraction
-> optional dictionary path loading
-> optional private sensitive terms replacement
-> anonymization
-> collision-safe output file in selected output folder
-> post-anonymization audit
-> safe report
-> optional batch summary
-> manual review status tracking without content preview
```

## Module Responsibilities

`main.py` is the application entry point. It starts the Stage 5 Tkinter GUI.

`gui.py` contains the Tkinter desktop interface. It lets the user select one or
more supported files, select an output folder, optionally select a private
sensitive terms file, run sequential batch anonymization, and view safe
filenames, safe dictionary status, aggregate category counters, aggregate audit
status counts, output/report filenames, the batch summary filename, and manual
review controls. It stores only the selected dictionary path and lets the
workflow load the file. It can load an existing output folder, list generated
anonymized output basenames, show matching report basenames when present, apply
manual review statuses, and save safe review metadata. It does not display
dictionary contents, original detected values, text snippets, dictionary terms,
or document contents.

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
workflows, dispatcher, and batch workflow can also accept
`sensitive_terms_path`; they load the dictionary centrally, build safe
dictionary metadata, and keep invalid dictionaries non-fatal while marking the
dictionary status as `invalid`. It also exposes the Stage 2
`anonymize_txt_file(...)` helper, the Stage 3 `anonymize_docx_file(...)`
helper, the Stage 4 `anonymize_pdf_file(...)` helper, the Stage 5
`anonymize_file(...)` dispatcher, and the Stage 12 `anonymize_batch(...)`
workflow. Stage 9 adds `_with_audit` variants for TXT, DOCX, PDF, and
dispatcher workflows. The existing helpers still return only the output path
plus category counters, but they also run the audit and save it into the safe
report.

`audit.py` contains the Stage 9 post-anonymization audit. It checks already
anonymized output text for conservative suspicious remaining patterns. When a
dictionary loaded successfully, the workflow passes those terms into the audit
so remaining dictionary aliases are counted as `SENSITIVE_DICTIONARY_TERM`
using the same Stage 11 case-insensitive and whitespace-tolerant matching
semantics as anonymization. The audit returns only status, category counters,
and a manual review flag. It never returns source values, text snippets,
private dictionary terms, document text, or replacement maps.

`file_writers.py` saves anonymized TXT, DOCX, and PDF-to-TXT copies without
modifying original files. The output filename receives the `_ANON` suffix. For
example, `document.txt` becomes `document_ANON.txt`, `document.docx` becomes
`document_ANON.docx`, and `document.pdf` becomes `document_ANON.txt`. Stage 12
allows these paths to target a selected output folder and uses numbered
collision-safe names when a generated file already exists. It also builds safe
report paths with the `_RAPORT.txt` suffix and the default
`_BATCH_SUMMARY.txt` path.

DOCX writing uses `python-docx` locally. It updates supported paragraph and simple table text in a copy of the original document. Basic paragraph and run formatting is preserved when possible, but full DOCX fidelity is not guaranteed.

PDF reading uses `pypdf` locally. Stage 4 extracts text and writes anonymized
TXT output only. It does not create anonymized PDF files, does not preserve PDF
layout, and does not modify the original PDF.

`report.py` builds and saves safe TXT reports without original sensitive source
values. It receives only status, input type, output type, anonymization
category counters, safe dictionary status metadata, dictionary label counters,
audit status, audit counters, and optional category ordering. Dictionary
counters are labels only, such as `IMIE NAZWISKO: 2`; original dictionary
terms are not passed to the report module. Stage 12 also adds safe batch
summary text generation with safe filenames, aggregate counters, audit status
counts, and controlled error descriptions only.

`review.py` contains the Stage 13 manual review workflow metadata. It detects
generated `_ANON` outputs in an output folder, pairs matching `_RAPORT` report
basenames when present, lists `_BATCH_SUMMARY` basenames when present, validates
manual statuses, and saves `_REVIEW_STATUS.json` plus collision-safe
`_REVIEW_SUMMARY.txt` files. It stores generated basenames, status counts, and
manual decision metadata only. It does not open generated documents, inspect
document contents, display excerpts, move files, or approve files
automatically.

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

Stage 13 review results are manual metadata only. `approved` means the user
manually approved the generated output; it is not inferred from the audit,
report, filename, or application logic. Review status and summary files contain
safe basenames and counts only, not source values, document contents, private
dictionary terms, aliases, full paths, tracebacks, or replacement maps.

Dictionary metadata is safe metadata only. It contains status names, booleans
implied by status, label names, and counters. It does not contain dictionary
source aliases, document fragments, source file paths, or replacement maps.

The project still does not use internet calls, APIs, cloud services, AI
services, OCR, local LLMs, databases, drag and drop, document preview, or an
editing workflow.

## GUI Limitations

The GUI is a simple workflow shell. It does not preview document content, edit
output, display dictionary contents, display audit snippets, write anonymized
PDF files, or generate detailed audit reports beyond safe counters and the
safe batch summary and safe manual review summary. It calls the batch workflow
and review workflow instead of parsing files inside the GUI layer.

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
guaranteed, and PDF input produces TXT output only.
