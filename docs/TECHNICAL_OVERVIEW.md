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
-> safe risk-level assignment for review prioritization
-> safe report
-> optional batch summary
-> manual review status tracking without content preview
-> optional approved workspace staging from saved manual decisions
```

Stage 18 validates this full chain with synthetic end-to-end tests and a
manual MVP smoke checklist. It does not change the architecture or add runtime
features.

Stage 19 adds an optional local OCR layer before anonymization for supported
image inputs and scanned PDFs without extractable text. OCR output is treated
as extracted text and then passes through the same deterministic
anonymization, audit, report, batch, manual review, and approved export
workflow.

## Module Responsibilities

`main.py` is the application entry point. It starts the Stage 5 Tkinter GUI.

`gui.py` contains the Tkinter desktop interface. It lets the user select one or
more supported files, select an output folder, optionally select a private
sensitive terms file, run sequential batch anonymization, and view safe
filenames, safe dictionary status, aggregate category counters, aggregate audit
status counts, aggregate risk counts, output/report filenames, the batch
summary filename, and manual review controls. Stage 15 keeps the same workflow
but makes the main layout scrollable, shows the selected-file count, lets the
user remove or clear files from the GUI selection without deleting them, and
improves plain-language status messages. It stores only the selected dictionary
path and lets the workflow load the file. It can load an existing output
folder, list generated anonymized output basenames, show matching report
basenames and safe risk levels when present, apply manual review statuses to
one or more selected rows, open the selected generated output or matching
report with the operating system default application, save safe review
metadata, and export manually approved outputs to an `approved/` staging
workspace. It does not display dictionary contents, original detected values,
text snippets, dictionary terms, or document contents.

`file_readers.py` reads UTF-8 TXT files, extracts basic text from local DOCX
files, and extracts text from text-based PDFs. DOCX extraction covers normal
paragraphs and simple table cells. PDF extraction uses an existing text layer
first.

`ocr.py` contains optional local OCR detection and extraction helpers. It
checks for Python OCR dependencies, the local Tesseract executable, and PDF
rendering support when needed. It returns controlled statuses such as
`available`, `dependency_missing`, `engine_not_found`, and `unsupported_input`
instead of exposing tracebacks or paths.

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
dispatcher workflows. Stage 19 adds an OCR image helper and scanned-PDF
fallback inside the PDF workflow. The existing helpers still return only the
output path plus category counters, but they also run the audit and save it
into the safe report.

`audit.py` contains the post-anonymization audit. It checks already anonymized
output text for conservative suspicious remaining patterns. When a dictionary
loaded successfully, the workflow passes those terms into the audit so
remaining dictionary aliases are counted as `SENSITIVE_DICTIONARY_TERM` using
the same Stage 11 case-insensitive and whitespace-tolerant matching semantics
as anonymization. Stage 16 adds deterministic risk levels: `ok` for no warning
counters, `warning` for warnings without a high-risk trigger, and `high_risk`
when a high-risk category appears or total warnings reach 3. The audit returns
only status, risk level, category counters, and a manual review flag. It never
returns source values, text snippets, private dictionary terms, document text,
or replacement maps.

`file_writers.py` saves anonymized TXT, DOCX, PDF-to-TXT, and image-to-TXT
copies without modifying original files. The output filename receives the
`_ANON` suffix. For example, `document.txt` becomes `document_ANON.txt`,
`document.docx` becomes `document_ANON.docx`, `document.pdf` becomes
`document_ANON.txt`, and `scan.png` becomes `scan_ANON.txt`. Stage 12 allows
these paths to target a selected output folder and uses numbered collision-safe
names when a generated file already exists. It also builds safe report paths
with the `_RAPORT.txt` suffix and the default `_BATCH_SUMMARY.txt` path.

DOCX writing uses `python-docx` locally. It updates supported paragraph and simple table text in a copy of the original document. Basic paragraph and run formatting is preserved when possible, but full DOCX fidelity is not guaranteed.

PDF reading uses `pypdf` locally. Stage 4 extracts text and writes anonymized
TXT output only. Stage 19 keeps that path first and attempts OCR only when a
PDF has no extractable text. It does not create anonymized PDF files, does not
preserve PDF layout, and does not modify the original PDF.

`report.py` builds and saves safe TXT reports without original sensitive source
values. It receives only status, input type, output type, anonymization
category counters, safe dictionary status metadata, dictionary label counters,
safe OCR metadata, audit status, audit risk level, audit counters, and optional
category ordering.
Dictionary counters are labels only, such as `IMIE NAZWISKO: 2`; original
dictionary terms are not passed to the report module. Stage 12 also adds safe
batch summary text generation with safe filenames, aggregate counters, audit
status counts, risk level counts, aggregate audit category counters, aggregate
OCR status counts, and controlled error descriptions only.

`review.py` contains the manual review workflow metadata. It detects generated
`_ANON` outputs in an output folder, pairs matching `_RAPORT` report basenames
when present, reads only the safe `Risk level:` line from paired reports, sorts
higher-risk items first, lists `_BATCH_SUMMARY` basenames when present,
validates manual statuses, and saves `_REVIEW_STATUS.json` plus collision-safe
`_REVIEW_SUMMARY.txt` files. It stores generated basenames, safe risk levels,
status counts, and manual decision metadata only. It does not open generated
documents, inspect document contents, display excerpts, move files, or approve
files automatically.

Stage 17 also keeps approved workspace export in `review.py`. The export reads
the saved `_REVIEW_STATUS.json`, finds entries with manual status `approved`,
copies only matching `_ANON` files into an `approved/` folder, optionally copies
matching `_RAPORT` files, and writes `_APPROVED_INDEX.txt`. It uses the same
collision-safe numbered naming helper as generated outputs, so existing
approved files and existing approved indexes are not silently overwritten. The
index contains basenames, copied counts, missing-report basenames, safe risk
levels when already available, and clear manual-decision/staging disclaimers.

`tests/test_stage18_end_to_end.py` validates the complete MVP workflow across
the existing modules. It covers TXT, dictionary, mixed-risk batch, DOCX, and
text-based PDF paths with synthetic fixtures only. It also checks that generated
outputs and local-only workspaces remain covered by `.gitignore`.

## Safety Design

The project is local-first and offline. Stage 19's OCR path is optional and
local only. It must not add cloud services, APIs, network calls, AI services,
databases, or large dependencies without explicit approval.

Reports must not include original sensitive source values. The application must not store replacement maps containing original values.

Private dictionary support does not create a replacement map and does not
include source values, aliases, or private dictionary terms in returned
counters, report files, or GUI status. The real private dictionary must not be
committed; it should live outside the repository or inside an ignored folder
such as `private/`.

Audit results are safe metadata only. They include warning categories, counts,
status, risk level, and manual review metadata, not original values, text
snippets, dictionary terms, full document text, or replacement maps. Audit
status `ok` and risk level `ok` do not prove complete anonymization; manual
review remains required. Risk levels are prioritization helpers only and do
not create automatic approval.

Stage 13 review results are manual metadata only. `approved` means the user
manually approved the generated output; it is not inferred from the audit,
report, filename, or application logic. Review status and summary files contain
safe basenames and counts only, not source values, document contents, private
dictionary terms, aliases, full paths, tracebacks, or replacement maps.

Stage 17 approved workspace export is also manual-decision metadata plus file
copying only. It never copies original source documents, `needs_review` files,
or `rejected` files. `_APPROVED_INDEX.txt` contains safe metadata and basenames
only. The approved workspace is a staging area, not a knowledge base and not a
guarantee of complete anonymization.

Dictionary metadata is safe metadata only. It contains status names, booleans
implied by status, label names, and counters. It does not contain dictionary
source aliases, document fragments, source file paths, or replacement maps.

The project still does not use internet calls, APIs, cloud services, AI
services, local LLMs, databases, drag and drop, document preview, or an editing
workflow. OCR, when available, uses only local dependencies.

Stage 19 keeps those exclusions unchanged apart from optional local OCR. The
approved workspace remains a manual staging area, not automatic approval, not
a knowledge base, and not a guarantee of complete anonymization.

## GUI Limitations

The GUI is a simple workflow shell. It does not preview document content, edit
output, display dictionary contents, display audit snippets, write anonymized
PDF files, or generate detailed audit reports beyond safe counters, risk
metadata, the safe batch summary, and the safe manual review summary. Stage 15
can ask the operating system to open a selected generated output or matching
report, but the GUI does not inspect those files or add an in-app viewer.
Stage 17 can export approved files, but it still delegates the file rules to
the review workflow and does not parse source files inside the GUI layer.

## Private Dictionary Limitations

Stage 11 private dictionary matching is deterministic, case-insensitive, and
whitespace-tolerant for user-specified aliases. It helps the user manually
specify known terms and variants, but it does not add fuzzy matching,
inflection handling, automatic names, cities, organizations, addresses,
context-based detection, AI, APIs, local LLMs, cloud services, databases,
or a replacement map.

## DOCX Limitations

Stage 3 does not handle headers, footers, comments, footnotes, form fields, text
inside images, or advanced DOCX elements. Manual review remains required before
using any anonymized DOCX output.

## PDF Limitations

Stage 4 supports PDFs that already contain extractable text. Stage 19 can
attempt OCR for scanned PDFs when local OCR dependencies are available. OCR can
be inaccurate, PDF layout preservation is not guaranteed, and PDF input still
produces TXT output only.
