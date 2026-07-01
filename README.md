# local-document-anonymizer

Local Document Anonymizer is a local-first Python/Tkinter desktop MVP for
anonymizing supported text documents on the user's own computer. It replaces
high-confidence regex matches and optional user-maintained private dictionary
terms with general labels, writes a separate anonymized output file, generates
a safe report, and expects manual review before any result is trusted.

## Key Features

- Local desktop GUI built with Tkinter.
- Multiple selected input files per batch run.
- Scrollable GUI layout with a readable selected-file count.
- Clear/remove actions for the GUI selected-file list without deleting files.
- Readiness hint that explains missing files or output folder before
  anonymization can start.
- User-selected output folder for all generated files.
- TXT input and UTF-8 TXT output.
- Basic DOCX input and output for paragraphs and simple tables.
- Text-based PDF input with a true-redacted visual PDF output and anonymized
  TXT output. Reports distinguish what was detected, what TXT anonymized, what
  PDF redacted, and any detected categories that were not PDF-redacted.
- Optional local OCR foundation for image inputs and scanned PDFs when local
  OCR dependencies are installed.
- Optional local NER/NLP foundation through spaCy and a locally installed
  Polish model.
- Optional local Ollama LLM-assisted review for already-anonymized text when
  the user has installed Ollama and a local model manually.
- Local Knowledge Assistant MVP for manually approved anonymized `_ANON.txt`
  files, with a generated local index, keyword retrieval fallback, optional
  local Ollama answer generation, and source citations.
- PNG, JPG/JPEG, and TIFF image inputs with anonymized TXT output when OCR is
  available.
- Collision-safe `_ANON`, `_RAPORT`, and `_BATCH_SUMMARY` naming.
- Regex anonymization for `PESEL`, `EMAIL`, `TELEFON`, `DATA`, and a
  conservative `PERSON_NAME_TYPO` pattern.
- Optional local NER anonymization for people, organizations, locations, and
  safe miscellaneous entity labels when spaCy and a local model are available.
- Optional private dictionary with aliases, case-insensitive matching, and
  whitespace-tolerant term matching.
- Safe post-anonymization audit with category counters and a per-file risk
  level only.
- Safe local LLM review metadata with controlled status, risk level, and
  residual category names only.
- Safe `_RAPORT.txt` reports without source personal data.
- Safe `_BATCH_SUMMARY.txt` reports with batch counts, aggregate audit risk
  counts, aggregate audit category counters, and safe filenames only.
- Manual review workflow for existing output folders.
- Manual review risk display so higher-risk generated outputs can be checked
  first.
- Manual review actions to open a selected `_ANON` output or matching
  `_RAPORT` report with the operating system default application.
- Safe `_REVIEW_STATUS.json` and collision-safe `_REVIEW_SUMMARY.txt`
  review metadata files.
- Approved workspace export that copies only manually approved `_ANON` files,
  optionally copies matching `_RAPORT` files, and writes a safe
  `_APPROVED_INDEX.txt` manifest.
- Local `_KNOWLEDGE_INDEX.json` generation from approved anonymized TXT files
  for source-cited question answering.
- End-to-end synthetic MVP workflow validation for batch output, reports,
  audit risk, manual review metadata, and approved workspace export.
- Synthetic examples and tests only.

## Privacy And Local-First Assumptions

The application is designed to run locally. It does not use APIs, cloud
services, cloud LLMs, OpenAI API calls, online processing, or databases.
Optional OCR, optional NER, optional Ollama-assisted review, and optional
Knowledge Assistant answer generation run only through local system
dependencies when they are installed. The LLM review layer receives
already-anonymized output text only, never raw source text, raw OCR text before
anonymization, dictionary terms, dictionary aliases, replacement maps, or
source snippets. The Knowledge Assistant receives only retrieved chunks from
approved anonymized TXT files. No model is downloaded automatically.

The repository must not contain real documents, real personal data, private
dictionaries, generated `_ANON` files, generated `_RAPORT` files, logs, local
configuration files, API keys, or credentials. Private dictionaries must stay
outside git, either outside the repository or in an ignored local folder such as
`private/`.

This is not production-ready full anonymization. It is a portfolio MVP and a
review-support tool. Manual review is required for every anonymized output.

## Supported Inputs And Outputs

| Input | Output | Report |
| --- | --- | --- |
| `document.txt` | `document_ANON.txt` | `document_RAPORT.txt` |
| `document.docx` | `document_ANON.docx` | `document_RAPORT.txt` |
| `document.pdf` | `document_ANON.pdf` + `document_ANON.txt` | `document_RAPORT.txt` |
| `image.png` / `image.jpg` / `image.tiff` | `image_ANON.txt` | `image_RAPORT.txt` |

All generated files are saved in the output folder selected by the user.
Original files are not modified. Text-based PDF support uses the existing
extractable text layer first and creates both a true-redacted visual PDF copy
and an anonymized TXT copy. If a PDF has no extractable text, the app can
attempt local OCR when optional OCR dependencies and the local Tesseract engine
are available, but scanned-PDF visual redaction is not implemented. Image
inputs produce anonymized TXT output, not edited image output. If an output
name already exists, the app writes the next safe numbered name, such as
`document_ANON_2.txt`, `document_ANON_2.pdf`, or `document_RAPORT_2.txt`.

## How Anonymization Works

The core engine processes plain text deterministically:

1. Load an optional private dictionary from a UTF-8 text file.
2. Replace dictionary aliases with their configured labels.
3. Replace supported regex categories: `EMAIL`, `PESEL`, `TELEFON`, `DATA`,
   and conservative `PERSON_NAME_TYPO`.
4. If enabled and available, run local spaCy NER on the remaining text and
   replace supported named entities with internal NER labels.
5. Save an anonymized output copy in the selected output folder.
6. Optionally run local Ollama review on the already-anonymized output text.
7. Audit the anonymized output for suspicious remaining patterns and assign a
   safe review-prioritization risk level.
8. For text-based PDFs, save a true-redacted visual `_ANON.pdf` companion
   using deterministic matches and exact local NER spans where available.
9. Save a safe per-file report.
10. For batch runs, save a safe batch summary report.
11. Let the user manually mark generated outputs as `approved`,
   `needs_review`, or `rejected`.

Counters contain labels and counts only. The app does not create or store a
replacement map from original values to labels.

## Private Dictionary

The private dictionary is a user-maintained UTF-8 text file. It supports the
original simple format:

```text
Person One Example = [IMIE NAZWISKO]
```

It also supports multiple aliases for one label:

```text
Person One Example | P. One Example | PERSON ONE EXAMPLE = [IMIE NAZWISKO]
Example Institution | Example Inst. = [NAZWA PODMIOTU]
```

Dictionary matching is deterministic, case-insensitive, and tolerant of extra
spaces inside matched terms. Longer aliases are applied before shorter aliases.
Reports show only labels and counts, never aliases or source terms.

Synthetic examples are provided in:

- `examples/sensitive_terms.example.txt`
- `examples/sensitive_terms.seed.example.txt`
- `examples/dictionary_candidates.example.txt`

Real private dictionaries must not be committed.

## Local NER / NLP

NER is optional, local, and used only when explicitly enabled by the caller or
the GUI checkbox. It uses spaCy when installed locally and tries to load a
local Polish model such as `pl_core_news_sm`. The application never downloads a
model at runtime and the repository must not contain spaCy model files.

Supported internal NER labels are:

- `NER_PERSON`
- `NER_ORG`
- `NER_LOCATION`
- `NER_MISC`

NER runs after private dictionary and regex replacements, so existing
deterministic replacements stay first. Existing placeholders are skipped to
avoid double replacement. Stage 20.1 adds a conservative local PERSON
left-expansion heuristic to reduce partial person masking in simple cases. NER
can miss entities or misclassify text, especially with short, inflected,
noisy, OCR-derived, or domain-specific text. Manual review is still required.

## Local LLM Review / Ollama

The optional LLM review layer uses Ollama locally when the user explicitly
enables it and provides a model name already installed on the same computer.
It is an extra quality-control layer after anonymization, not the main
anonymizer and not an editor. The app does not download, pull, or require any
specific model. A Polish-language local model such as Bielik may be useful if
the user has installed it manually, but no model name is hardcoded.
On Windows, the Ollama subprocess path explicitly uses UTF-8 text handling and
strips any leading UTF-8 BOM from anonymized text before building the review
prompt so local review does not fail on BOM-marked or Polish Unicode text.

The LLM review asks for strict structured JSON and stores only safe metadata:

- review used yes/no,
- controlled status,
- safe model name,
- `ok`, `warning`, `high_risk`, or `unknown` risk level,
- allowed residual category names,
- manual-review requirement.

To improve local JSON reliability, the app sends the review request through
Ollama's local generate API with `stream=false`, `temperature=0`, and a strict
JSON schema in the request format. The parser still rejects non-JSON, unsafe
extra fields, invalid category names, and invalid types as controlled
`invalid_response`. If a local model returns the whole JSON object inside a
markdown code fence, the fence is stripped in memory before strict parsing.
Prose outside the fence remains `invalid_response`.

Reports and batch summaries do not store raw prompts, raw model responses,
document snippets, source text, detected entity values, raw OCR text,
dictionary terms, dictionary aliases, or replacement maps. If Ollama is
missing, the service is unavailable, no model is configured, the configured
model is missing, the call times out, or the model returns invalid JSON, the
workflow records a controlled status and continues without crashing. Encoding
or subprocess text-handling failures also fall back to a controlled safe
status instead of exposing prompt text or exception details. Manual review
remains required because local LLM output can be wrong, incomplete, or
invalid.

## Post-Anonymization Audit

After output is generated, the audit checks the anonymized text for conservative
remaining patterns:

- `EMAIL`
- `PESEL`
- `TELEFON`
- `DATA`
- `SENSITIVE_DICTIONARY_TERM`
- `CASE_REFERENCE`
- `POSTAL_CODE`
- `ADDRESS_LIKE`
- `STREET_LIKE`
- `INITIAL_SURNAME`
- `ID_LIKE_NUMBER`
- `LONG_NUMBER_SEQUENCE`

Audit results contain status and counters only. They do not contain original
values, text snippets, private dictionary terms, full document text, or a
replacement map. `ok` does not prove complete anonymization; it only means the
current audit checks did not find supported warning patterns.

The audit also assigns a risk level for manual-review prioritization:

- `ok`: no audit warning counters.
- `warning`: warning counters exist, but no high-risk condition is met.
- `high_risk`: at least one high-risk category is present or total audit
  warnings reach 3.

High-risk categories are `EMAIL`, `PESEL`, `TELEFON`,
`SENSITIVE_DICTIONARY_TERM`, `ADDRESS_LIKE`, `ID_LIKE_NUMBER`, and
`LONG_NUMBER_SEQUENCE`. The risk level is only a prioritization helper and is
not a safety guarantee. Manual review is still required.

## Reports

Each successful file workflow writes a safe `_RAPORT.txt` report containing:

- status,
- input and output type,
- anonymization category counters,
- dictionary used/status/matches-found metadata,
- dictionary label counters,
- OCR used/status/input-type metadata and page/image counts,
- NER enabled/used/status/model metadata and NER category counters,
- LLM review used/status/model/risk metadata and possible residual category
  names,
- PDF redaction used/status/output metadata, detected/TXT/PDF category
  coverage, detected-but-not-PDF-redacted categories, warnings when visual
  redaction is partial, and color legend for text-based PDFs,
- post-anonymization audit status, risk level, and counters,
- manual review requirement,
- confirmation that original sensitive values are not stored,
- confirmation that no replacement map was created.

Reports do not include document text, detected entity text, original sensitive
values, full input paths, dictionary aliases, text snippets, logs, or
replacement maps.

Batch runs also write `_BATCH_SUMMARY.txt` in the selected output folder. The
summary contains batch counts, aggregate category counters, audit status
counts, risk level counts, aggregate audit category counters, aggregate OCR
status counts, aggregate NER status counts, aggregate NER category counters,
aggregate LLM review status counts, LLM risk counts, LLM residual category
counters, PDF redaction status counts, safe input/output/report filenames, and
controlled safe error descriptions. If a generated PDF was only partially
covered, the summary records a safe warning by category/status only. It does
not include source text, raw OCR text, detected entity text, private dictionary
terms, aliases, full paths, exception messages, raw LLM prompts, raw LLM
responses, document snippets, or a replacement map.

Manual review runs can write `_REVIEW_STATUS.json` and
`_REVIEW_SUMMARY.txt` in the selected output folder. The status file tracks
safe generated output basenames, optional report basenames, and the user's
manual status: `approved`, `needs_review`, or `rejected`. The summary contains
safe counts, safe basenames, and a clear note that decisions are manual user
decisions. `approved` does not mean the application guaranteed complete
anonymization.

Review status and summary files do not include document contents, excerpts,
source personal data, private dictionary terms, dictionary aliases, full local
paths, tracebacks, or replacement maps. Review summary filenames are
collision-safe, for example `_REVIEW_SUMMARY_2.txt`.

When paired Stage 16 reports are present, the manual review list shows each
generated output's safe risk level and sorts `high_risk` items first. The GUI
still does not inspect or preview document contents.

After review metadata is saved, the manual review section can export an
`approved/` workspace. This copies only files marked `approved` in
`_REVIEW_STATUS.json`, never `needs_review` or `rejected` files, and never
original source documents. Matching `_RAPORT` files are copied when available.
The approved workspace writes a safe `_APPROVED_INDEX.txt` manifest containing
basenames and safe metadata only. If an exported file or index already exists,
the app uses numbered names such as `document_ANON_2.txt` or
`_APPROVED_INDEX_2.txt` instead of overwriting.

The approved workspace is a staging area for manually approved anonymized
files. It does not guarantee complete anonymization.

## Local Knowledge Assistant

Stage 22 adds a small local CLI assistant over approved anonymized TXT files.
It reads only approved `*_ANON.txt` files, chunks them deterministically, writes
a local `_KNOWLEDGE_INDEX.json`, retrieves relevant chunks with a keyword
fallback, and always prints source chunk IDs such as:

```text
procedure_ANON.txt#2
```

Build a local index:

```bash
python -m src.knowledge_cli build-index approved/
```

Ask a question against the index:

```bash
python -m src.knowledge_cli ask approved/_KNOWLEDGE_INDEX.json "What does the procedure require?"
```

Optionally use a local Ollama model for answer generation:

```bash
python -m src.knowledge_cli ask approved/_KNOWLEDGE_INDEX.json "What does the procedure require?" --use-ollama --model gemma3:4b
```

Check local Ollama/model status or warm up a local model before asking:

```bash
python -m src.knowledge_cli ollama-status --model gemma3:4b
python -m src.knowledge_cli warmup --model gemma3:4b
```

The first local model call can be slow because Ollama may need to load the
model into memory. If the first generated answer times out, run `warmup` first
or retry `ask` with a larger `--timeout` value.

If Ollama or the model is unavailable, the command returns retrieved sources
and a controlled message instead of crashing. Timeout fallback is expected and
safe: sources are still shown, and the answer does not pretend generation
succeeded. The assistant answers only from retrieved approved context. It can
be wrong or incomplete, and the user must verify answers against the cited
source documents.

Generated knowledge indexes contain approved anonymized text and are local
artifacts. They are ignored by git and must not be committed.

## Installation

Use a local Python environment:

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

OCR is optional and local. The Python packages in `requirements.txt` include
the OCR adapter libraries, but the Tesseract executable and language data must
be installed separately on the user's computer. The repository does not bundle
Tesseract binaries, OCR models, external installers, or real OCR outputs.

NER is optional and local. Install the Python package from `requirements.txt`
and install a Polish spaCy model separately in the same environment, for
example:

```bash
python -m spacy download pl_core_news_sm
python -c "import spacy; spacy.load('pl_core_news_sm'); print('NER model available')"
```

The application does not run those commands automatically.

LLM review is optional and local. Install Ollama and any local model manually,
outside this repository. Basic local checks:

```bash
ollama --version
ollama list
```

If needed, start or check the local Ollama service using the normal Ollama
instructions for your operating system. The application never runs
`ollama pull` and never downloads models automatically.

## How To Run

Run the GUI:

```bash
python src/main.py
```

The GUI can also be launched as a module:

```bash
python -m src.gui
```

Build and query a local knowledge index from an approved workspace:

```bash
python -m src.knowledge_cli build-index approved/
python -m src.knowledge_cli ask approved/_KNOWLEDGE_INDEX.json "What does the procedure require?"
python -m src.knowledge_cli ollama-status --model gemma3:4b
python -m src.knowledge_cli warmup --model gemma3:4b
```

Run the tests:

```bash
python -m unittest discover -s tests
```

## Basic Usage

1. Start the app with `python src/main.py` or `python -m src.gui`.
2. Add one or more `.txt`, `.docx`, `.pdf`, `.png`, `.jpg`, `.jpeg`, `.tif`,
   or `.tiff` files and check the selected-file count.
3. Select an output folder.
4. Optionally select a private dictionary file.
5. Optionally leave local NER enabled.
6. Optionally enable local LLM review and enter an installed Ollama model name.
7. If `Anonymize batch` is disabled, read the readiness hint beside the button.
8. Click `Anonymize batch`.
9. Check the GUI status, counters, audit/LLM summary, generated filenames, and
   batch summary filename.
10. Manually review every anonymized output before using or sharing it.
11. In the manual review section, select the output folder, load detected
    generated outputs, optionally open the selected `_ANON` output or matching
    `_RAPORT` report in the default system app, assign manual statuses, and
    save the review metadata.
12. Optionally click `Export approved` to create an `approved/` staging
    workspace from files marked `approved` in `_REVIEW_STATUS.json`.

For a practical non-developer validation sequence, use
`docs/MVP_MANUAL_TEST_CHECKLIST.md` with synthetic files only.

## Example Workflow

For a TXT file:

```text
output folder / document_ANON.txt
output folder / document_RAPORT.txt
```

For a DOCX file:

```text
output folder / document_ANON.docx
output folder / document_RAPORT.txt
```

For a text-based PDF file:

```text
output folder / document_ANON.pdf
output folder / document_ANON.txt
output folder / document_RAPORT.txt
```

For an OCR image file:

```text
output folder / scan_ANON.txt
output folder / scan_RAPORT.txt
```

For a batch run:

```text
output folder / _BATCH_SUMMARY.txt
```

If a generated filename already exists, the app adds `_2`, `_3`, and so on
before the extension instead of overwriting it.

## Project Structure

```text
src/
  anonymizer.py        Core engine and file workflow dispatchers
  audit.py             Safe post-anonymization audit
  file_readers.py      TXT, DOCX, and text-based PDF reading
  file_writers.py      _ANON output and _RAPORT path helpers
  gui.py               Tkinter GUI
  knowledge_assistant.py
                       Local index, retrieval, and answer helpers for approved TXT
  knowledge_cli.py     CLI for building and querying the local knowledge index
  main.py              GUI entry point
  ner.py               Optional local spaCy NER helpers
  ocr.py               Optional local OCR detection and extraction helpers
  pdf_redaction.py     True-redacted visual PDF output for text-based PDFs
  report.py            Safe report generation
  review.py            Safe manual review and approved workspace metadata
  sensitive_terms.py   Private dictionary parsing and matching
tests/                 Synthetic unit tests
examples/              Synthetic example inputs and dictionaries
  before/              Empty placeholder — drop input documents here to test
  after/               Empty placeholder — drop output documents here to compare
docs/                  Project and module documentation
docs/MVP_MANUAL_TEST_CHECKLIST.md
                       Manual synthetic MVP smoke-test checklist
AGENTS.md              AI assistant collaboration rules (Codex / Claude workflow)
```

## Example Document Folders

`examples/before/` and `examples/after/` are empty placeholder folders for
local testing. Drop a sample input document into `before/` and the resulting
`_ANON` output into `after/` to keep a before-and-after pair for manual
comparison. Both folders are tracked by git as empty placeholders (via
`.gitkeep`), but any documents placed inside are gitignored so real files are
never committed by accident.

## Tests

The test suite uses synthetic data only. It covers the regex engine,
TXT/DOCX/PDF workflows, GUI dispatcher layer, private dictionary parsing and
matching, safe reports, post-anonymization audit metadata, collision-safe
output naming, output workspace behavior, batch processing, manual review
metadata, approved workspace export, safe approved index generation, and
Stage 18 end-to-end MVP workflow validation, Stage 22 local knowledge
assistant behavior, and Stage 23 text-based PDF redaction behavior. Stage 20
tests use mocked NER model output, so they do not
require a real spaCy Polish model. Stage 21 tests mock Ollama behavior, so
they do not require real Ollama or a real local model. Stage 22/22.1 tests use
synthetic approved TXT files and mocked local generation/status/warm-up.
Stage 23 tests use generated synthetic PDFs only.

Run:

```bash
python -m unittest discover -s tests
```

## Current Limitations

- Manual review is always required.
- OCR is optional, local, dependency-dependent, and imperfect.
- NER is optional, local, dependency/model-dependent, and imperfect.
- LLM review is optional, local, post-anonymization only, and dependent on the
  user's local Ollama installation and manually installed model.
- NER can miss or misclassify names, organizations, locations, and other
  entities.
- LLM review can miss risks, misclassify context, time out, or return invalid
  structured output.
- Knowledge Assistant answers depend on approved anonymized TXT inputs,
  retrieval quality, and optional local model behavior. Answers can be wrong
  or incomplete and must be checked against cited source chunks.
- The first local Ollama answer can time out while a model cold-starts; use
  `ollama-status`, `warmup`, or a larger `--timeout` before retrying.
- Audit risk levels are review-prioritization hints only, not proof that a
  document is safe.
- This is not production-ready full anonymization.
- Regex detection is narrow and conservative.
- Private dictionary matching is not fuzzy matching, inflection handling, ML,
  or LLM-based detection.
- Text-based PDF redaction depends on PyMuPDF text search and can miss unusual
  encodings, fragmented glyphs, rotated text, form fields, annotations, or text
  in images.
- No scanned-PDF/OCR bounding-box redaction.
- Batch processing is sequential; one file's error is recorded safely and does
  not stop later files.
- No drag and drop.
- No full document preview or editing workflow.
- Manual review tracking is status metadata plus optional external file
  opening only; it does not inspect, preview, edit, or validate document
  contents inside the app.
- No automatic approval.
- Approved workspace export is a staging convenience and not a guarantee of
  complete anonymization.
- Knowledge index files are generated local artifacts and must not be
  committed.
- DOCX support is limited to basic paragraphs and simple tables.
- DOCX headers, footers, comments, footnotes, form fields, text in images, and
  advanced elements are not handled.
- Scanned PDF and image OCR require optional local OCR dependencies and the
  local Tesseract engine; if OCR is unavailable, the file fails with a
  controlled safe status instead of being silently treated as processed.
- Text-based `_ANON.pdf` output preserves the original page layout as a visual
  review aid, but fonts and unusual PDF structures are not guaranteed.
- Reports contain safe counters and metadata only, not a detailed audit trail.
- Reports and batch summaries do not include raw OCR text.
- Reports and batch summaries do not include detected NER entity text.
- Reports and batch summaries do not include raw LLM prompts, raw LLM
  responses, source text, snippets, or detected values.
- Batch summary reports use safe filenames and controlled error descriptions
  only; they do not include private paths or exception text.

## Roadmap

Completed MVP stages include repository setup, regex anonymization, TXT IO,
basic DOCX IO, text-based PDF input, Tkinter GUI, safe reports, private
dictionary support, post-anonymization audit, manual validation fixes, the
Stage 11 smart dictionary foundation, Stage 12 safe output workspace with
batch processing, the Stage 13 manual review workflow, the Stage 15 GUI
usability cleanup, Stage 16 stronger audit risk prioritization, Stage 17
approved workspace staging, and Stage 18 end-to-end synthetic validation with
a manual MVP smoke checklist. Stage 19 adds an optional local OCR foundation
for image inputs and scanned PDF fallback without adding cloud/API processing
or edited image/PDF output. Stage 20 adds an optional local spaCy NER
foundation without runtime model downloads, cloud/API processing, Ollama,
Bielik, OpenAI API calls, online NLP, or LLM-based review. Stage 21 adds an
optional local Ollama-assisted review foundation that analyzes
already-anonymized output text only and records safe metadata without prompts
or raw responses. Stage 22 adds a local Knowledge Assistant MVP that builds an
ignored `_KNOWLEDGE_INDEX.json` from approved anonymized TXT files, retrieves
chunks with a keyword fallback, optionally uses local Ollama answer generation,
and always shows source chunk IDs. Stage 22.1 adds CLI status and warm-up
commands plus clearer timeout guidance for local Ollama cold starts. Stage 23
adds a layout-preserving true-redacted `_ANON.pdf` companion for text-based PDF
inputs while keeping `_ANON.txt` for the Local Knowledge Assistant.

Potential future work requires explicit approval, especially OCR quality
improvements, installer packaging, release automation, stronger entity
detection, dictionary candidate export from NER findings, AI/API integration,
broader LLM workflows, databases, or broad NLP features.

## Portfolio Note

This project exists as a practical portfolio MVP: a small, offline document
anonymization tool with clear privacy boundaries, deterministic behavior,
synthetic tests, and honest documentation of limitations. The emphasis is on a
reviewable local workflow rather than pretending to solve complete document
anonymization automatically.
