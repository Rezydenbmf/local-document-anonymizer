# Technical Overview

## Current Flow

```text
input file
-> text extraction
-> optional dictionary path loading
-> optional private sensitive terms replacement
-> anonymization
-> optional local NER on remaining text when enabled and available
-> collision-safe output file in selected output folder
-> optional local LLM review of already-anonymized output text only
-> post-anonymization audit
-> safe risk-level assignment for review prioritization
-> safe report
-> optional batch summary
-> manual review status tracking without content preview
-> optional approved workspace staging from saved manual decisions
-> optional local knowledge index over approved *_ANON.txt files
-> optional source-cited question answering from retrieved approved chunks
```

Stage 18 validates this full chain with synthetic end-to-end tests and a
manual MVP smoke checklist. It does not change the architecture or add runtime
features.

Stage 19 adds an optional local OCR layer before anonymization for supported
image inputs and scanned PDFs without extractable text. OCR output is treated
as extracted text and then passes through the same deterministic
anonymization, audit, report, batch, manual review, and approved export
workflow.

Stage 20 adds an optional local spaCy NER layer after private dictionary and
regex replacements. It uses only a locally installed spaCy package and local
Polish model, never downloads models at runtime, and records controlled
statuses when the dependency or model is unavailable.

Stage 21 adds an optional local Ollama review layer after anonymized output
text exists. It analyzes only already-anonymized text and records safe
structured metadata. It never receives raw source text, raw OCR text before
anonymization, private dictionary terms, dictionary aliases, replacement maps,
or source snippets.

Stage 22 adds a separate local Knowledge Assistant path after manual approval.
It loads approved anonymized TXT files only, chunks them, writes a local
generated `_KNOWLEDGE_INDEX.json`, retrieves relevant chunks with a keyword
fallback, and optionally asks a local Ollama model to answer from retrieved
approved context only. The answer path always returns source chunk IDs.
Stage 22.1 adds CLI-only Ollama status and warm-up helpers so the user can see
whether local Ollama is reachable, whether a model is installed or loaded, and
warm up a cold local model before asking.

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

`ner.py` contains optional local NER detection and replacement helpers. It
checks for spaCy and a local Polish model such as `pl_core_news_sm`, maps
model labels into internal labels such as `NER_PERSON`, `NER_ORG`,
`NER_LOCATION`, and `NER_MISC`, skips existing anonymization placeholders, and
returns controlled statuses such as `available`, `dependency_missing`,
`model_missing`, `disabled`, and `processing_error`.

`llm_review.py` contains optional local Ollama review helpers. It checks for
the local `ollama` command/service, lists installed models where possible,
validates the configured model name, builds an in-memory prompt for
already-anonymized text only, calls the local Ollama generate API with a
timeout, and parses strict structured JSON into safe metadata. Controlled
statuses include
`disabled`, `ollama_not_found`, `service_unavailable`, `no_model_configured`,
`model_missing`, `timeout`, `invalid_response`, `processing_error`, and
`completed`.

`knowledge_assistant.py` contains the Stage 22 local knowledge assistant
helpers. It loads only approved `*_ANON.txt` files, keeps safe source basenames
only, chunks approved anonymized text, writes and loads `_KNOWLEDGE_INDEX.json`,
scores chunks with keyword retrieval, and returns answers with source chunk IDs.
When local Ollama generation is enabled, it sends only retrieved approved
chunks to the local generate API. Missing Ollama, missing models, timeouts, no
relevant chunks, and generation failures become controlled answer statuses.
Stage 22.1 also provides safe local status and warm-up helpers. Status checks
reuse local Ollama availability/model-list checks and optionally query
Ollama's local `/api/ps` endpoint for currently loaded models. Warm-up sends a
tiny local prompt through the same local generate API. These helpers do not
download models or call external services.

`knowledge_cli.py` is the Stage 22 CLI. It exposes `build-index` for approved
workspace indexing, `ask` for source-cited question answering against a local
index, `ollama-status` for local Ollama/model status, and `warmup` for a small
local model warm-up prompt. `ask --timeout` lets the user extend local
generation time when a first model load is slow.

`sensitive_terms.py` contains private dictionary support. It loads a UTF-8
local dictionary file, parses `term = [LABEL]` and
`alias | alias = [LABEL]` lines, ignores blank lines and comments, validates
malformed lines with safe line-number errors, applies longer aliases before
shorter aliases, and returns counters by label only. Stage 11 matching is
case-insensitive and tolerates extra internal whitespace inside matched
dictionary aliases.

`anonymizer.py` contains the plain text anonymization engine. It accepts a
Python string, optionally applies private sensitive terms, replaces supported
regex matches with placeholders, optionally applies local NER to the remaining
text when enabled, and returns category counters only. The file workflows,
dispatcher, and batch workflow can also accept
`sensitive_terms_path`; they load the dictionary centrally, build safe
dictionary metadata, and keep invalid dictionaries non-fatal while marking the
dictionary status as `invalid`. It also exposes the Stage 2
`anonymize_txt_file(...)` helper, the Stage 3 `anonymize_docx_file(...)`
helper, the Stage 4 `anonymize_pdf_file(...)` helper, the Stage 5
`anonymize_file(...)` dispatcher, and the Stage 12 `anonymize_batch(...)`
workflow. Stage 9 adds `_with_audit` variants for TXT, DOCX, PDF, and
dispatcher workflows. Stage 19 adds an OCR image helper and scanned-PDF
fallback inside the PDF workflow. Stage 20 adds keyword-only `use_ner` and
`ner_model_name` controls so existing callers keep their return shapes. The
existing helpers still return only the output path plus category counters.
Stage 21 adds keyword-only `use_llm_review` and `llm_model_name` controls. The
file helpers also run optional LLM review, audit, and safe report output.

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
safe OCR metadata, safe NER metadata, safe LLM review metadata, audit status,
audit risk level, audit counters, and optional category ordering.
Dictionary counters are labels only, such as `IMIE NAZWISKO: 2`; original
dictionary terms are not passed to the report module. Stage 12 also adds safe
batch summary text generation with safe filenames, aggregate counters, audit
status counts, risk level counts, aggregate audit category counters, aggregate
OCR status counts, aggregate NER status/category counts, aggregate LLM
review status/risk/category counts, and controlled error descriptions only.

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

The project is local-first and offline. Stage 19's OCR path, Stage 20's NER
path, and Stage 21's Ollama review path are optional and local only. Stage 21
does not add cloud services, APIs, network calls, cloud LLMs, RAG, vector
databases, chat UI, document rewriting, or large dependencies. Ollama and any
model must be installed by the user; the application does not download or pull
models automatically.

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

The project still does not use internet calls, APIs, cloud services, cloud
LLMs, databases, drag and drop, document preview, chat UI, document rewriting,
or an editing workflow. OCR, NER, LLM review, and Knowledge Assistant answer
generation, when available, use only local dependencies. The approved workspace
remains a manual staging area, not automatic approval and not a guarantee of
complete anonymization. The generated knowledge index is a local artifact that
may contain approved anonymized text and must not be committed.

LLM review results are metadata only. Reports and batch summaries must not
include raw prompts, raw LLM responses, source text, source snippets, raw OCR
text, dictionary terms, dictionary aliases, detected entity values, full paths,
tracebacks, or replacement maps. Invalid or unexpected model output becomes
`invalid_response` rather than a crash.

Knowledge Assistant answers are source-cited retrieval results over approved
anonymized text. The assistant must not receive original source documents,
private dictionaries, raw OCR text before anonymization, replacement maps, or
full local paths. It can be wrong or incomplete, so the user must verify every
answer against the cited source files. If a local model times out while
loading, the CLI keeps source citations visible and returns a controlled
timeout message instead of pretending generation succeeded.

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
inflection handling, AI, APIs, local LLMs, cloud services, databases, or a
replacement map. Stage 20 NER is a separate optional detection layer and does
not change dictionary semantics.

## NER Limitations

Stage 20 NER depends on spaCy and a local Polish model installed outside the
repository. It can miss or misclassify entities and does not prove complete
anonymization. Reports and summaries include only safe NER metadata and
counters, never detected entity text. The app does not download models at
runtime and does not bundle spaCy model files.

## LLM Review Limitations

Stage 21 LLM review depends on Ollama and a local model installed outside the
repository. It can miss sensitive context, misclassify harmless context, time
out, or return invalid structured output. It is a post-anonymization review
signal only and does not replace deterministic anonymization, private
dictionary matching, NER, audit, or manual review.

## DOCX Limitations

Stage 3 does not handle headers, footers, comments, footnotes, form fields, text
inside images, or advanced DOCX elements. Manual review remains required before
using any anonymized DOCX output.

## PDF Limitations

Stage 4 supports PDFs that already contain extractable text. Stage 19 can
attempt OCR for scanned PDFs when local OCR dependencies are available. OCR can
be inaccurate, PDF layout preservation is not guaranteed, and PDF input still
produces TXT output only.
