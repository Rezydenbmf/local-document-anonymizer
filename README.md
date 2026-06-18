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
- Text-based PDF input with anonymized TXT output.
- Collision-safe `_ANON`, `_RAPORT`, and `_BATCH_SUMMARY` naming.
- Regex anonymization for `PESEL`, `EMAIL`, `TELEFON`, and `DATA`.
- Optional private dictionary with aliases, case-insensitive matching, and
  whitespace-tolerant term matching.
- Safe post-anonymization audit with category counters and a per-file risk
  level only.
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
- Synthetic examples and tests only.

## Privacy And Local-First Assumptions

The application is designed to run locally. It does not use AI, APIs, cloud
services, network calls, OCR, local LLMs, or databases.

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
| `document.pdf` | `document_ANON.txt` | `document_RAPORT.txt` |

All generated files are saved in the output folder selected by the user.
Original files are not modified. PDF support requires an existing extractable
text layer and does not create anonymized PDF files. If an output name already
exists, the app writes the next safe numbered name, such as
`document_ANON_2.txt` or `document_RAPORT_2.txt`.

## How Anonymization Works

The core engine processes plain text deterministically:

1. Load an optional private dictionary from a UTF-8 text file.
2. Replace dictionary aliases with their configured labels.
3. Replace supported regex categories: `EMAIL`, `PESEL`, `TELEFON`, `DATA`.
4. Save an anonymized output copy in the selected output folder.
5. Audit the anonymized output for suspicious remaining patterns and assign a
   safe review-prioritization risk level.
6. Save a safe per-file report.
7. For batch runs, save a safe batch summary report.
8. Let the user manually mark generated outputs as `approved`,
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
- post-anonymization audit status, risk level, and counters,
- manual review requirement,
- confirmation that original sensitive values are not stored,
- confirmation that no replacement map was created.

Reports do not include document text, original sensitive values, full input
paths, dictionary aliases, text snippets, logs, or replacement maps.

Batch runs also write `_BATCH_SUMMARY.txt` in the selected output folder. The
summary contains batch counts, aggregate category counters, audit status
counts, risk level counts, aggregate audit category counters, safe
input/output/report filenames, and controlled safe error descriptions. It does
not include source text, private dictionary terms, aliases, full paths,
exception messages, or a replacement map.

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

## Installation

Use a local Python environment:

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## How To Run

Run the GUI:

```bash
python src/main.py
```

The GUI can also be launched as a module:

```bash
python -m src.gui
```

Run the tests:

```bash
python -m unittest discover -s tests
```

## Basic Usage

1. Start the app with `python src/main.py` or `python -m src.gui`.
2. Add one or more `.txt`, `.docx`, or text-based `.pdf` files and check the
   selected-file count.
3. Select an output folder.
4. Optionally select a private dictionary file.
5. If `Anonymize batch` is disabled, read the readiness hint beside the button.
6. Click `Anonymize batch`.
7. Check the GUI status, counters, audit summary, generated filenames, and
   batch summary filename.
8. Manually review every anonymized output before using or sharing it.
9. In the manual review section, select the output folder, load detected
   generated outputs, optionally open the selected `_ANON` output or matching
   `_RAPORT` report in the default system app, assign manual statuses, and
   save the review metadata.

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
output folder / document_ANON.txt
output folder / document_RAPORT.txt
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
  main.py              GUI entry point
  report.py            Safe report generation
  review.py            Safe manual review status and summary metadata
  sensitive_terms.py   Private dictionary parsing and matching
tests/                 Synthetic unit tests
examples/              Synthetic example inputs and dictionaries
  before/              Empty placeholder — drop input documents here to test
  after/               Empty placeholder — drop output documents here to compare
docs/                  Project and module documentation
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
output naming, output workspace behavior, batch processing, and manual review
metadata.

Run:

```bash
python -m unittest discover -s tests
```

## Current Limitations

- Manual review is always required.
- Audit risk levels are review-prioritization hints only, not proof that a
  document is safe.
- This is not production-ready full anonymization.
- Regex detection is narrow and conservative.
- Private dictionary matching is not fuzzy matching, inflection handling, NER,
  ML, or LLM-based detection.
- No OCR or scanned PDF support.
- No anonymized PDF output.
- Batch processing is sequential; one file's error is recorded safely and does
  not stop later files.
- No drag and drop.
- No full document preview or editing workflow.
- Manual review tracking is status metadata plus optional external file
  opening only; it does not inspect, preview, edit, or validate document
  contents inside the app.
- No automatic approval.
- DOCX support is limited to basic paragraphs and simple tables.
- DOCX headers, footers, comments, footnotes, form fields, text in images, and
  advanced elements are not handled.
- PDF support requires an extractable text layer and does not preserve layout.
- Reports contain safe counters and metadata only, not a detailed audit trail.
- Batch summary reports use safe filenames and controlled error descriptions
  only; they do not include private paths or exception text.

## Roadmap

Completed MVP stages include repository setup, regex anonymization, TXT IO,
basic DOCX IO, text-based PDF input, Tkinter GUI, safe reports, private
dictionary support, post-anonymization audit, manual validation fixes, the
Stage 11 smart dictionary foundation, Stage 12 safe output workspace with
batch processing, the Stage 13 manual review workflow, the Stage 15 GUI
usability cleanup, and Stage 16 stronger audit risk prioritization.

Potential future work requires explicit approval, especially OCR, scanned PDF
support, stronger entity detection, installer packaging, release automation,
AI/API integration, local LLMs, databases, or broad NLP features.

## Portfolio Note

This project exists as a practical portfolio MVP: a small, offline document
anonymization tool with clear privacy boundaries, deterministic behavior,
synthetic tests, and honest documentation of limitations. The emphasis is on a
reviewable local workflow rather than pretending to solve complete document
anonymization automatically.
