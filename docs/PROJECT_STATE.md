# Project State

## Current Status

The project is in Stage 23: Layout-preserving PDF redaction MVP, with final
synthetic text-based PDF smoke verification completed and ready for final
commit review.

The Stage 0-13 MVP implementation contains a narrow regex-based engine that
accepts a Python string and returns anonymized text plus category counters. It
also contains optional private dictionary support with aliases,
case-insensitive matching, and whitespace-tolerant term matching, TXT file
readers and writers, basic DOCX readers and writers, text-based PDF text
extraction, small integration helpers for saving separate anonymized TXT, DOCX,
and PDF-to-TXT outputs, a simple Tkinter GUI for anonymizing selected
supported files into a chosen output folder, safe TXT report generation without
source values, a safe post-anonymization audit with category counters only,
batch processing, and manual review status tracking for generated output
folders.

Stage 10.1 fixes manual validation findings around the private dictionary flow.
The GUI stores the selected dictionary path, the workflow loads it centrally,
reports include safe dictionary status and label counters, and the audit checks
remaining dictionary terms when a dictionary loaded successfully. It did not
add OCR, AI, cloud services, APIs, local LLMs, databases, batch processing,
automatic replacement-map generation, source-value logging, or automatic
deletion of originals.

Stage 10.2 manually confirmed the Stage 10.1 dictionary fix with a GUI smoke
test using small synthetic UTF-8 files.

Stage 11 kept the existing local workflow and improved the private dictionary
foundation. Dictionary lines can contain multiple aliases separated by `|`,
matching is case-insensitive, excessive internal whitespace is tolerated, and
longer aliases are still applied before shorter aliases. Reports, GUI status,
audit metadata, and counters continue to expose labels and counts only.

Stage 12 adds a safe output workspace and batch processing. The GUI now lets
the user select multiple supported files and an output folder. `_ANON`,
`_RAPORT`, and `_BATCH_SUMMARY` files are written to that output folder with
collision-safe numbered names. Batch processing is sequential; an error for one
file is recorded in a safe form and does not stop later files. The batch
summary stores safe filenames, aggregate counters, audit status counts, and
controlled error descriptions only.

Stage 13 adds a manual review workflow for existing output folders. The app
detects generated `_ANON` files, pairs matching `_RAPORT` files when present,
lists `_BATCH_SUMMARY` files when present, lets the user mark outputs as
`approved`, `needs_review`, or `rejected`, and saves safe
`_REVIEW_STATUS.json` and collision-safe `_REVIEW_SUMMARY.txt` metadata.
`approved` is a manual user decision, not an automatic application decision,
and the workflow does not show, inspect, or store document contents.

Stage 15 improves the existing Tkinter GUI usability without changing the core
anonymization engine. The window is resizable with a smaller minimum size and a
scrollable main layout, the input selection is shown as a removable list with a
readable selected-file count, selected inputs can be cleared from the GUI
without deleting files, the anonymization button has a visible readiness hint
that explains missing input files or output folder, review statuses can be
applied to multiple selected review rows, and the manual review section can
open the selected generated `_ANON` output or matching `_RAPORT` report with
the operating system default application. The GUI still does not preview,
inspect, edit, or validate document contents inside the app.

Stage 16 strengthens the deterministic post-anonymization audit and adds safe
per-file risk levels for manual-review prioritization. The audit now returns
status, risk level, category counters, and manual review metadata only.
`_RAPORT.txt` includes audit status, risk level, warning counters, and manual
review requirement. `_BATCH_SUMMARY.txt` includes aggregate risk level counts
and aggregate audit category counters. The manual review workflow reads risk
levels from safe paired reports and the GUI shows a risk column with
`high_risk` items sorted first. The risk level is not an automatic approval or
safety guarantee; manual review remains required.

Stage 17 adds an approved workspace export for output folders with saved manual
review metadata. The export reads `_REVIEW_STATUS.json`, copies only `_ANON`
files marked `approved` into an `approved/` staging folder, optionally copies
matching `_RAPORT` files when present, and writes a safe
`_APPROVED_INDEX.txt` manifest using basenames and metadata only. Existing
approved workspace files are not overwritten; numbered suffixes such as `_2`
and `_3` are used. `approved` remains a manual user decision and the approved
workspace is a staging area, not a knowledge base or guarantee of complete
anonymization.

Stage 18 validates the complete local MVP workflow end to end with synthetic
tests and manual smoke-test documentation. It exercises source files, batch
anonymization, reports, post-anonymization audit risk levels, manual review
metadata, approved workspace export, and the safe approved index. It does not
add OCR, AI/API integration, local LLMs, databases, installer work, drag and
drop, document preview, split-screen review, highlighting, automatic approval,
or a knowledge base.

Stage 18 also includes a small dictionary stabilization fix: a leading UTF-8
BOM at the start of a dictionary file is ignored so the first alias on the
first line matches consistently with later aliases.

Stage 19 adds an optional local OCR foundation. It introduces controlled OCR
availability detection, image input OCR for PNG/JPG/JPEG/TIFF when local OCR
dependencies and Tesseract are installed, and scanned-PDF fallback only when a
PDF has no extractable text layer. OCR text feeds into the existing
anonymization, report, audit, batch, GUI, manual review, and approved export
workflow as anonymized TXT output. Reports and batch summaries include safe OCR
metadata only. Stage 19 does not add cloud OCR, API OCR, OpenAI API calls,
online processing, NER, local LLMs, split-screen review, preview,
highlighting, drag and drop, installer work, packaging, edited image output,
or scanned-PDF visual redaction.

Stage 20 adds an optional local NER/NLP foundation. It introduces controlled
spaCy availability detection, local Polish model loading without runtime
downloads, internal NER labels for people, organizations, locations, and safe
miscellaneous entities, and safe NER metadata in reports, batch summaries, and
the GUI status area. NER runs only when enabled and available, after private
dictionary and regex replacements, and skips existing placeholders to avoid
double replacement. Missing spaCy, missing local models, disabled NER, and
processing errors are controlled statuses and do not crash the application.
Stage 20.1 adds a conservative local PERSON left-expansion heuristic to reduce
partial person masking in simple adjacent-token cases. Stage 20 does not add
Ollama, Bielik, OpenAI API calls, cloud/API processing, online NLP, local LLMs,
candidate export files, document preview, highlighting, drag and drop,
databases, or model downloads at runtime.

Stage 21 adds an optional local Ollama LLM-assisted review foundation. It
introduces controlled Ollama availability detection, safe installed-model
listing where possible, configured model validation, strict JSON response
parsing, timeout/error handling, safe LLM metadata in reports and batch
summaries, and a minimal GUI checkbox plus model-name field. LLM review runs
after anonymization and receives already-anonymized output text only. It is an
extra quality-control layer, not the primary anonymizer, not an editor, not a
replacement for dictionary/regex/NER/audit/manual review, and not automatic
approval. Stage 21 does not add OpenAI API calls, cloud LLMs, external APIs,
online processing, RAG, vector databases, a chat UI, document rewriting,
runtime model downloads, or a required Ollama model.
Stage 21.1 hardens the local Ollama subprocess path for Windows UTF-8/BOM
handling by stripping BOM characters from already-anonymized review input,
forcing UTF-8 subprocess text handling, and converting encoding/subprocess
failures into controlled safe LLM statuses without exposing prompt text, raw
responses, snippets, or traceback details.
Stage 21.2 improves local Ollama JSON reliability by sending the review call
through the local Ollama generate API with a strict JSON schema request,
keeping strict parser rejection for invalid/unsafe output, and correcting
batch LLM counters so `timeout`, `invalid_response`, and `processing_error`
count as attempted safe failures instead of skipped/unavailable runs. The
parser also tolerates the narrow local-model behavior where the entire JSON
object is wrapped in a markdown code fence, while still rejecting prose outside
the fence and never storing the raw response.

Stage 22 adds a local Knowledge Assistant MVP for approved anonymized TXT
documents. It loads only approved `*_ANON.txt` files, preserves safe source
basenames only, chunks documents deterministically, writes a local generated
`_KNOWLEDGE_INDEX.json`, retrieves relevant chunks with a keyword fallback,
optionally uses local Ollama answer generation with a user-installed model such
as `gemma3:4b`, and always returns source chunk IDs. If Ollama is unavailable,
the model is missing, generation fails, or no relevant context is found, the
assistant returns controlled messages instead of crashing. Stage 22 does not
add embeddings, `bge-m3`, a vector database, a GUI, a web app, cloud APIs,
OpenAI API calls, online processing, document editing, authentication,
installer work, or automatic business-procedure generation.

Stage 22.1 improves the Local Knowledge Assistant CLI UX for local Ollama cold
starts. It adds `ollama-status` and `warmup` commands, lets `ask` accept a
local generation `--timeout`, and returns clearer timeout messages that tell
the user to warm up the model or retry with a longer timeout. Timeout fallback
still shows retrieved sources and does not pretend generation succeeded. Stage
22.1 remains CLI-only and does not add a GUI redesign.

Stage 23 adds a layout-preserving true-redacted visual PDF companion for
text-based PDF inputs. A text-based PDF now produces `_ANON.pdf`,
`_ANON.txt`, and `_RAPORT.txt`. The PDF redaction helper uses PyMuPDF
redaction annotations plus `apply_redactions()` so matched source text is
removed from the generated PDF content rather than hidden under overlays.
Stage 23.1 expands the text-based PDF redaction MVP with deterministic
`POSTAL_CODE` and simple labeled-address candidates plus exact local NER spans
when the NER model is available and the text span can be matched back to the
PDF. The TXT output remains the source for approved-workspace indexing and the
Local Knowledge Assistant. Reports and batch summaries include safe PDF
redaction status/count metadata, a color legend, detected category counts, TXT
anonymized category counts, PDF-redacted category counts, and
detected-but-not-PDF-redacted category counts. When detected categories are not
PDF-redacted, the PDF redaction status is `completed_with_warnings` instead of
plain `completed`. The manual review open action prefers the companion
`_ANON.pdf` when it exists, while review metadata still tracks the `_ANON.txt`
output. Stage 23 also adds a conservative `PERSON_NAME_TYPO` pattern for cases
such as `Firstname-Lastname Lastname`. Stage 23 does not add scanned-PDF/OCR
bounding-box redaction, a PDF editor, split-screen review, drag and drop,
vector databases, or broader LLM features.

## What Exists

- Repository structure.
- Regex-based plain text anonymization in `src/anonymizer.py`.
- Supported Stage 1 categories: `PESEL`, `EMAIL`, `TELEFON`, and `DATA`.
- UTF-8 TXT reading in `src/file_readers.py`.
- UTF-8 TXT anonymized copy writing in `src/file_writers.py`.
- TXT integration helper `anonymize_txt_file(...)`.
- Basic local DOCX paragraph and simple table text reading in
  `src/file_readers.py`.
- Basic DOCX anonymized copy writing in `src/file_writers.py`.
- DOCX integration helper `anonymize_docx_file(...)`.
- Text-based PDF extraction in `src/file_readers.py`.
- PDF integration helper `anonymize_pdf_file(...)`, which saves anonymized PDF
  text as `_ANON.txt`.
- Optional local OCR support in `src/ocr.py` with controlled statuses:
  `available`, `unavailable`, `dependency_missing`, `engine_not_found`, and
  `unsupported_input`.
- Optional local NER support in `src/ner.py` with controlled statuses:
  `available`, `unavailable`, `dependency_missing`, `model_missing`,
  `disabled`, and `processing_error`.
- Optional local Ollama LLM review support in `src/llm_review.py` with
  controlled statuses: `disabled`, `available`, `unavailable`,
  `ollama_not_found`, `service_unavailable`, `no_model_configured`,
  `model_missing`, `timeout`, `invalid_response`, `processing_error`, and
  `completed`.
- Windows-safe UTF-8 local Ollama subprocess handling with BOM stripping for
  already-anonymized review text before prompt construction.
- Local Ollama review requests sent through the local generate API with
  `stream=false`, `temperature=0`, and a strict JSON schema request format.
- Strict local LLM response parsing that accepts a whole-response markdown
  JSON fence but rejects prose-wrapped or unsafe output as `invalid_response`.
- Local Knowledge Assistant support in `src/knowledge_assistant.py` for
  loading approved anonymized TXT files, chunking them, writing/loading
  `_KNOWLEDGE_INDEX.json`, keyword retrieval fallback, source-cited answers,
  controlled optional local Ollama answer generation, local Ollama/model
  status checks, and local model warm-up.
- CLI support in `src/knowledge_cli.py` for building a local knowledge index
  asking questions against it, checking Ollama/model status, warming up a
  local model, and setting an answer generation timeout.
- Optional spaCy NER model loading with no automatic model download and no
  committed model files.
- True-redacted visual PDF companion output in `src/pdf_redaction.py` for
  text-based PDFs using PyMuPDF redaction annotations and
  `apply_redactions()`.
- PDF redaction coverage metadata that separates detected categories, TXT
  anonymized categories, PDF-redacted categories, and detected-but-not-PDF-
  redacted categories.
- Conservative `PERSON_NAME_TYPO` replacement/audit category for typo-shaped
  person names such as `Firstname-Lastname Lastname`.
- Internal NER labels: `NER_PERSON`, `NER_ORG`, `NER_LOCATION`, and
  `NER_MISC`.
- Optional image OCR workflow for `.png`, `.jpg`, `.jpeg`, `.tif`, and `.tiff`
  inputs, saving anonymized OCR text as `_ANON.txt`.
- Optional scanned PDF OCR fallback when a PDF has no extractable text and
  local OCR dependencies are available.
- Safe OCR metadata in per-file `_RAPORT.txt` reports and aggregate
  `_BATCH_SUMMARY.txt` reports.
- Safe NER metadata in per-file `_RAPORT.txt` reports and aggregate
  `_BATCH_SUMMARY.txt` reports.
- Safe LLM review metadata in per-file `_RAPORT.txt` reports and aggregate
  `_BATCH_SUMMARY.txt` reports. Metadata is limited to review used/status,
  safe model name, LLM risk level, possible residual category names, and
  manual-review requirement.
- Single-file application dispatcher `anonymize_file(...)`, with optional
  output directory support.
- Batch workflow `anonymize_batch(...)`.
- Simple Tkinter GUI in `src/gui.py` for selecting multiple input files, an
  output folder, an optional private dictionary, and an output folder for
  manual review status tracking.
- Scrollable Tkinter GUI layout with a readable selected-file count.
- GUI actions to remove selected inputs or clear the input list without
  deleting files from disk.
- GUI readiness hint that explains whether input files or an output folder are
  still needed before anonymization can start.
- GUI file selection for implemented OCR-capable image inputs and safe
  aggregate OCR status display in the existing audit/status area.
- GUI checkbox for optional local LLM review and a simple model-name field.
  The GUI shows aggregate LLM review status metadata only.
- Manual review GUI actions to open a selected `_ANON` output or matching
  `_RAPORT` report with the operating system default application.
- Default GUI entry point in `src/main.py`.
- Safe report text generation in `src/report.py`.
- Report path helper `build_report_path(...)`, which can target the selected
  output folder.
- Collision-safe path helper for `_ANON`, `_RAPORT`, and `_BATCH_SUMMARY`
  outputs.
- Private sensitive terms parsing and replacement in `src/sensitive_terms.py`.
- Dictionary alias parsing with `alias | alias = [LABEL]` support.
- Case-insensitive and whitespace-tolerant private dictionary matching.
- Post-anonymization audit in `src/audit.py`.
- Optional `sensitive_terms_path` arguments in the TXT, DOCX, PDF, and
single-file dispatcher and batch workflows, while the plain text engine still
accepts preloaded `sensitive_terms`.
- `_with_audit` TXT, DOCX, PDF, and dispatcher helpers that return safe audit
  metadata while existing helpers keep their Stage 2-5 return shape.
- Optional GUI selection of a private sensitive terms file path without
  displaying dictionary contents.
- GUI display of post-anonymization audit status, risk counts, and category
  counters only.
- GUI display of safe dictionary status: not selected, loaded, invalid, or
  loaded with no dictionary matches.
- Safe report counters for dictionary labels only.
- Safe report dictionary section with used/status/matches-found metadata.
- Safe report section for post-anonymization audit status, risk level, and
  counters only.
- Safe report section for local LLM review metadata only. Reports do not store
  raw prompts, raw LLM responses, source text, document snippets, detected
  values, raw OCR text, dictionary terms, dictionary aliases, or replacement
  maps.
- Shared dictionary matching semantics for anonymization and audit dictionary
  checks.
- TXT, DOCX, PDF, and dispatcher flows that create safe reports after
  successful anonymization.
- Batch summary report generation with safe filenames, aggregate risk counts,
  aggregate audit category counters, aggregate LLM review status/risk/category
  counters, aggregate PDF redaction status counts, and no private paths.
- Manual review workflow in `src/review.py` for detecting generated `_ANON`
  outputs, pairing safe report basenames, reading safe report risk levels,
  applying manual statuses, and saving safe review metadata.
- GUI support for assigning `approved`, `needs_review`, or `rejected` statuses
  without previewing or editing document contents.
- GUI support for showing safe manual-review risk levels and sorting
  `high_risk` outputs first.
- GUI manual-review open action preference for companion `_ANON.pdf` files
  when a PDF-derived `_ANON.txt` item has a visual redacted PDF next to it.
- Safe `_REVIEW_STATUS.json` review manifest output.
- Collision-safe `_REVIEW_SUMMARY.txt` review summary output.
- Approved workspace export in `src/review.py` that reads
  `_REVIEW_STATUS.json`, copies only approved `_ANON` basenames into
  `approved/`, optionally copies matching `_RAPORT` files, and writes a safe
  `_APPROVED_INDEX.txt` manifest.
- GUI `Export approved` action in the manual review section.
- Runtime dependency on `python-docx`.
- Runtime dependency on `pypdf`.
- Unit tests for the Stage 1 anonymizer using synthetic values only.
- Unit tests for Stage 2 TXT input/output using synthetic temporary files only.
- Unit tests for Stage 3 DOCX input/output using synthetic temporary files only.
- Unit tests for Stage 4 text-based PDF input/output using generated
  synthetic temporary PDFs only.
- Unit tests for the Stage 5 single-file dispatcher using synthetic temporary
  TXT files only.
- Unit tests for Stage 6 safe report generation and TXT/DOCX/PDF report
  integration using synthetic temporary files only.
- Unit tests for Stage 8 private dictionary parsing, replacement order,
  integration, and report safety using synthetic values only.
- Unit tests for Stage 9 post-anonymization audit detection, report safety,
  workflow integration, and GUI/dispatcher audit metadata safety using
  synthetic values only.
- Unit tests for Stage 10.1 dictionary path flow, dictionary report status,
  invalid dictionary handling, loaded-without-matches status, and TXT/DOCX/PDF
  dictionary-path compatibility using synthetic values only.
- Unit tests for Stage 11 dictionary aliases, backward compatibility,
  case-insensitive matching, whitespace normalization, longer aliases before
  shorter aliases, label-only counters, safe alias reports, and audit
  dictionary matching using synthetic values only.
- Unit tests for Stage 12 collision-safe naming, output workspace behavior,
  batch TXT/DOCX/PDF processing, safe error continuation, and safe batch
  summary content using synthetic values only.
- Unit tests for Stage 13 generated output detection, report pairing, missing
  report handling, manual statuses, safe review status JSON, safe review
  summary text, collision-safe review summary naming, Stage 12 regression, and
  report/audit regression using synthetic values only.
- Unit tests for Stage 17 approved workspace export, missing review status,
  no-approved handling, optional report copying, missing reports,
  collision-safe export naming, and safe approved index contents using
  synthetic values only.
- Unit tests for Stage 18 end-to-end MVP workflow validation, including simple
  low-risk TXT approval/export, mixed-risk review prioritization, dictionary
  aliases, DOCX and text-based PDF participation, safe metadata, and generated
  output ignore coverage using synthetic values only.
- Unit tests for Stage 19 OCR availability detection, missing-dependency and
  missing-engine behavior, mocked image OCR, text-based PDF non-OCR
  regression, scanned PDF OCR fallback, safe OCR report metadata, and safe OCR
  batch summary errors using synthetic inputs only.
- Unit tests for Stage 20 NER availability detection, missing spaCy behavior,
  missing local model behavior, mocked entity detection, PERSON/ORG/location
  anonymization, NER counters, safe report metadata, safe batch summary
  metadata, DOCX workflow integration, and no-crash fallback using synthetic
  inputs only.
- Unit tests for Stage 21 Ollama availability detection, missing command,
  service unavailable, no model configured, missing model, mocked successful
  LLM review, timeout handling, invalid response handling, structured response
  parsing including fenced JSON, risk-level mapping, residual category
  aggregation, safe report and batch summary metadata, no-crash unavailable
  fallback, and review input policy using synthetic/mocked data only.
- Unit tests for Stage 22 approved document loading, ignoring non-ANON files,
  deterministic chunk metadata, index creation, keyword retrieval fallback,
  source references, controlled no-context behavior, controlled
  Ollama-unavailable behavior, mocked local generation, CLI behavior, and
  generated knowledge index ignore coverage using synthetic data only.
- Unit tests for Stage 22.1 local Ollama status checks, installed-but-not-loaded
  model status, warm-up unavailable/timeout handling, ask-timeout behavior, and
  CLI status/warm-up commands using mocked local behavior only.
- Unit tests for Stage 23 text-based PDF redaction output, hidden-text removal
  checks on generated synthetic PDFs, safe report/batch redaction metadata,
  manual-review PDF open preference, and the `PERSON_NAME_TYPO` pattern.
- Manual MVP smoke-test checklist in `docs/MVP_MANUAL_TEST_CHECKLIST.md`.
- Synthetic sample text files in `tests/sample_data/`.
- Synthetic example dictionary in `examples/sensitive_terms.example.txt`.
- Synthetic seed dictionary example in `examples/sensitive_terms.seed.example.txt`.
- Synthetic manual-review candidate file in
  `examples/dictionary_candidates.example.txt`.
- Project, user, security, roadmap, and module documentation.
- `.gitignore` rules for private data and local artifacts.
- Stage 7 portfolio/release review documentation updates for README quality,
  user guidance, technical flow clarity, roadmap status, security assumptions,
  and honest portfolio text.

## What Does Not Exist Yet

- Advanced GUI preview or editing workflow.
- Drag and drop.
- AI/API calls, cloud services, cloud LLMs, online processing, databases, RAG,
  vector databases, or local LLM use beyond the optional post-anonymization
  Ollama review metadata layer.
- Edited image output or scanned-PDF/OCR visual redaction.
- Bundled Tesseract binaries, OCR language models, or OCR installers.
- Detailed report generation beyond safe counters, safe audit metadata, and
  manual review notes.
- Automatic approval based on audit results or report contents.
- Moving rejected or needs-review files into separate folders.
- Embedding-based retrieval, `bge-m3` embeddings, or a vector database.
- Knowledge Assistant GUI or chat history.
- Scanned-PDF/OCR bounding-box visual redaction.
- NER span coordinate mapping back into PDF pages.
- Production-grade names, surnames, cities, organizations, or context-based
  detection.
- Production-grade OCR quality handling.
- LLM-based primary anonymization, document rewriting, chat UI, prompt logging,
  raw response logging, or automatic approval.

## How to Run

Run the GUI entry point:

```bash
python src/main.py
```

The GUI module launch is also supported:

```bash
python -m src.gui
```

Run tests:

```bash
python -m unittest discover -s tests
```

## Current Limitations

- The core engine processes only a plain Python string.
- File input/output supports `.txt` files, basic `.docx` files, `.pdf` files
  with extractable text or optional OCR fallback, and OCR-capable image inputs.
- TXT outputs are written to the selected output folder with an `_ANON` suffix.
- DOCX outputs are written to the selected output folder with an `_ANON` suffix.
- PDF input is extracted as text and saved as `_ANON.txt`; no anonymized PDF is
  created for scanned/OCR-only PDFs.
- Text-based PDF input also creates `_ANON.pdf` as a true-redacted visual
  companion when PyMuPDF can locate supported matches.
- Image input is OCR-extracted and saved as `_ANON.txt`; no edited image is
  created.
- Existing output files are not overwritten silently; numbered suffixes such as
  `_2` and `_3` are used when needed.
- Batch processing is sequential and records per-file errors in the safe batch
  summary.
- Per-file reports contain only safe metadata, category counters, and manual
  review notices. They do not contain source values, full input paths,
  filenames, dictionary source aliases or terms, or replacement maps.
- Date detection is limited to high-confidence numeric formats.
- Phone detection is intentionally conservative.
- Broader address and identifier detection remains conservative and
  audit-only; it is not full entity detection.
- DOCX formatting preservation is basic only.
- DOCX headers, footers, comments, footnotes, form fields, text in images, and
  advanced elements are not handled.
- OCR is optional, local, and dependency-dependent. Scanned PDF fallback and
  image OCR require local Python OCR libraries plus the Tesseract executable
  and language data installed outside the repository.
- NER is optional, local, and dependency/model-dependent. It requires spaCy and
  a local Polish model installed outside the repository.
- NER can miss or misclassify people, organizations, locations, and other
  entities.
- OCR can be inaccurate. OCR output still goes through deterministic
  anonymization and must be manually reviewed.
- Text-based PDF redaction preserves the source pages as a visual review aid,
  but unusual encodings, fragmented glyphs, rotated text, form fields,
  annotations, or text in images can be missed.
- The GUI processes selected files sequentially and does not include document
  preview, editing, or drag and drop.
- The manual review workflow tracks statuses only. It does not inspect,
  validate, preview, edit, or automatically approve anonymized document
  contents. Opening a selected output or report delegates to the operating
  system default application and does not add an in-app viewer.
- Review status and summary files contain safe generated basenames and status
  counts only, not full paths, source data, document excerpts, private
  dictionary terms, aliases, tracebacks, or replacement maps.
- Approved workspace indexes contain safe basenames, copied report counts,
  missing-report basenames, safe risk levels when already available, and
  manual-decision disclaimers only. They do not contain document text, source
  values, private dictionary terms, aliases, full paths, tracebacks, or
  replacement maps.
- Report files are plain TXT only and do not include a detailed audit trail.
- Reports and batch summaries include safe OCR metadata only; they do not
  include raw OCR text.
- Reports and batch summaries include safe NER metadata only; they do not
  include detected entity text.
- Reports and batch summaries include safe LLM review metadata only; they do
  not include raw prompts, raw LLM responses, source text, document snippets,
  detected entity values, dictionary terms, dictionary aliases, raw OCR text,
  or replacement maps.
- Private dictionary matching is deterministic, case-insensitive, and tolerant
  of extra internal spaces, but it is not fuzzy matching, inflection handling,
  automatic entity recognition, AI, or NER.
- The real private dictionary must stay outside git, either outside the
  repository or inside an ignored folder such as `private/`.
- Post-anonymization audit matching is conservative and regex-based. It can
  miss sensitive data and can warn on harmless text.
- Audit status `ok` and risk level `ok` do not prove complete anonymization.
  Manual review is still required.
- Audit risk levels are prioritization helpers only. They are not automatic
  approval decisions.
- Audit results and reports include only categories, counters, status, risk
  level, and manual review metadata, never source values, snippets,
  dictionary terms, full document text, or replacement maps.

## Last Completed Committed Stage

Stage 22: Local Knowledge Assistant MVP plus Stage 22.1 CLI warm-up/status UX.

```text
ddd1612 Implement Stage 22 local knowledge assistant
```

## Next Logical Step

Review the Stage 23 diff and prepare a small final commit if the scope,
synthetic smoke verification, tests, and public repository safety checks are
accepted. The final synthetic text-based PDF smoke verified that `_ANON.pdf`,
`_ANON.txt`, and `_RAPORT.txt` are created, that copied/searchable text from
the generated PDF no longer includes the synthetic source values, and that the
report separates detected, TXT-anonymized, PDF-redacted, and
detected-but-not-PDF-redacted categories.
Potential future work requires an explicit project decision, especially
embedding retrieval with `bge-m3`, OCR quality improvements, NER candidate
export, installer work, AI/API integration, broader LLM features, databases,
broad NLP/entity detection, packaging, release automation, or GUI/chat
knowledge-base work.

## Warning

This repository is still an early-stage portfolio MVP. Do not use it to
anonymize real documents without manual review and project-specific safety
checks.
