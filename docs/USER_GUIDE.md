# User Guide

## 1. What This Application Is For

Local Document Anonymizer is a local desktop tool for replacing supported
sensitive values in documents with general labels.

The workflow is local-first. It does not use cloud services, API calls, cloud
LLMs, online processing, or a database. Optional OCR, optional NER, and
optional Ollama-assisted review run only on the user's computer when local
dependencies and local models are installed.

## 2. What This Application Is Not For

It is not a cloud service, compliance guarantee, production OCR product,
document editor, or automatic privacy solution.

## 3. Basic Workflow

The current MVP workflow is:

1. Run `python src/main.py` or `python -m src.gui`.
2. Add one or more supported files and check the selected-file count.
3. Select an output folder.
4. Optionally select a private sensitive terms file.
5. Leave `Use local NER if available` checked when you want the optional local
   spaCy NER layer to run, or uncheck it for dictionary/regex-only processing.
6. Optionally enable `Use local LLM review if available` and enter the name of
   a local Ollama model that you installed manually.
7. If `Anonymize batch` is disabled, read the readiness hint beside the button.
8. Click `Anonymize batch`.
9. Check the status, dictionary status, category counters, aggregate audit
   status, aggregate risk levels, aggregate OCR/NER/LLM status, generated
   filenames, and batch summary filename.
10. Manually review each anonymized output file before using or sharing it.
11. Use the manual review section to load the output folder, optionally open the
   selected generated output or matching report in the operating system
   default application, assign statuses, and save safe review metadata.
12. Optionally export approved files to an `approved/` staging workspace.

The application saves output files before manual review. It does not provide an
in-app document preview or editing screen.

For a complete synthetic MVP smoke test, follow
`docs/MVP_MANUAL_TEST_CHECKLIST.md`.

The selected-file list is only a GUI selection. `Remove selected` and
`Clear files` remove files from that list only. They do not delete original
files from disk.

The readiness hint uses plain messages such as `Add at least one input file.`,
`Select an output folder.`, or `Ready to anonymize 3 file(s).` It does not show
document contents, source values, private dictionary terms, or full local paths.

## 4. Supported Files in Current Stage

The current MVP supports ordinary `.txt` files, basic `.docx` files,
text-based `.pdf` files, and optional OCR for `.png`, `.jpg`, `.jpeg`, `.tif`,
and `.tiff` image files when local OCR dependencies are available.

TXT files are read locally as UTF-8 text. The anonymized result is saved as a
separate copy with `_ANON` added to the filename:

```text
document.txt -> document_ANON.txt
document.txt -> document_RAPORT.txt
```

DOCX files are also read locally. The anonymized result is saved as a separate
copy with `_ANON` added to the filename:

```text
document.docx -> document_ANON.docx
document.docx -> document_RAPORT.txt
```

Original TXT and DOCX files are not modified.

Text-based PDF files are read locally and the extracted text is anonymized into
a TXT file:

```text
document.pdf -> document_ANON.txt
document.pdf -> document_RAPORT.txt
```

Original PDF files are not modified. The application does not create
`document_ANON.pdf` or any other anonymized PDF output.

If a PDF has no extractable text layer, the application can attempt local OCR
when optional OCR dependencies and the local Tesseract engine are installed.
If OCR is unavailable, the file is reported with a controlled safe error
instead of being silently treated as processed.

Image files are not edited. OCR-extracted image text is anonymized into a TXT
file:

```text
scan.png -> scan_ANON.txt
scan.png -> scan_RAPORT.txt
```

DOCX support is basic. It covers ordinary paragraphs and simple tables. It does
not cover headers, footers, comments, footnotes, form fields, text in images, or
advanced DOCX elements. Basic formatting is preserved only in a limited MVP
range.

PDF layout preservation is not guaranteed. OCR is optional, dependency
dependent, and can be imperfect. Manual review is still required for OCR
outputs.

Optional NER can detect and replace people, organizations, locations, and safe
miscellaneous entity labels when spaCy and a local Polish model are installed.
NER can miss or misclassify entities. Manual review is still required for NER
outputs.

Optional local LLM review can add a second review signal when Ollama and a
local model are installed manually. It runs after anonymization and analyzes
already-anonymized output text only. It does not receive raw source text, raw
OCR text before anonymization, private dictionary terms, private dictionary
aliases, replacement maps, or source snippets.

APIs, cloud services, databases, drag and drop, advanced document preview, PDF
writing, edited image output, cloud LLMs, online NLP, and detailed audit
reports with source snippets are not supported.

Optional OCR requires local Python OCR libraries and the Tesseract executable
with needed language data installed on the user's computer. The repository
does not include Tesseract binaries, OCR models, external installers, or real
OCR outputs.

Optional NER requires `spacy` plus a local Polish model such as
`pl_core_news_sm` installed in the user's Python environment. The application
does not download models automatically and the repository does not include
spaCy model files.

Optional local LLM review requires Ollama plus a local model installed outside
the repository. The application does not download or pull Ollama models. A
Polish-language local model such as Bielik may be useful if installed
manually, but no specific model is required by the app. Useful local checks:

```bash
ollama --version
ollama list
```

## 5. Report Files

For every successful TXT, DOCX, or text-based PDF anonymization, the
application writes a separate `_RAPORT.txt` file in the selected output folder.

The report contains:

- status,
- input type,
- output type,
- category counters,
- dictionary used/status/matches-found information,
- dictionary label counters,
- OCR used/status/input-type metadata and page/image counts,
- NER enabled/used/status/model metadata and NER category counters,
- LLM review used/status/model/risk metadata and possible residual category
  names,
- post-anonymization audit status, risk level, and category counters,
- manual review requirement,
- confirmation that original sensitive values are not stored,
- confirmation that no replacement map was created.

The report does not contain document text, raw OCR text, detected entity text,
raw LLM prompts, raw LLM responses, original sensitive values, full input
paths, source filenames, private dictionary terms, text snippets, or
replacement maps.

For each batch run, the application writes `_BATCH_SUMMARY.txt` in the selected
output folder. If that name already exists, it writes `_BATCH_SUMMARY_2.txt`,
`_BATCH_SUMMARY_3.txt`, and so on. The batch summary contains:

- number of input files,
- number of successful files,
- number of errors,
- aggregate category counters,
- audit status counts,
- risk level counts,
- aggregate audit warning category counters,
- aggregate OCR status counts,
- aggregate NER status counts and NER category counters,
- aggregate LLM review status counts, LLM risk counts, and LLM residual
  category counters,
- safe input, output, and report filenames,
- controlled safe error descriptions.

The batch summary does not contain source document text, raw OCR text,
detected entity text, raw LLM prompts, raw LLM responses, original sensitive
values, private dictionary terms, aliases, replacement maps, full paths,
document snippets, or raw exception messages.

## 6. Manual Review Workflow

Stage 13 adds a simple manual review tracking workflow for an existing output
folder. It is an organization aid only. It does not inspect document contents
and does not approve anything automatically.

The GUI can:

1. Select an output folder created by batch processing.
2. Detect generated `_ANON` files.
3. Pair matching `_RAPORT` files when present.
4. Read safe risk levels from paired Stage 16 `_RAPORT` files when present.
5. Sort higher-risk generated outputs first in the review list.
6. Show `_BATCH_SUMMARY` files when present.
7. Open the selected `_ANON` output in the operating system default
   application.
8. Open the matching `_RAPORT` report in the operating system default
   application when one is detected.
9. Let the user mark each generated output as `approved`, `needs_review`, or
   `rejected`.
10. Save `_REVIEW_STATUS.json`.
11. Save `_REVIEW_SUMMARY.txt`.
12. Export approved files into an `approved/` staging workspace.

`approved` means the user manually approved the file after review. It does not
mean the application guarantees complete anonymization. `needs_review` means
the file still needs further review or correction. `rejected` means the user
decided not to use that generated output.

The review status file and review summary may contain safe generated basenames,
report basenames, status counts, batch summary basenames, timestamps, and the
manual completion flag. They do not contain document contents, excerpts,
source personal data, private dictionary terms, dictionary aliases, full local
paths, tracebacks, or replacement maps.

The open actions are convenience shortcuts only. They do not inspect document
contents, validate anonymization, edit files, move files, or approve anything
automatically.

If `_REVIEW_SUMMARY.txt` already exists, the application writes a numbered
summary such as `_REVIEW_SUMMARY_2.txt`. `_REVIEW_STATUS.json` stores the
latest status manifest for the output folder.

## 7. Approved Workspace

After `_REVIEW_STATUS.json` has been saved, the GUI can create an approved
workspace by clicking `Export approved`.

The export creates or reuses this folder inside the selected output folder:

```text
approved/
```

It copies only generated `_ANON` files with manual status `approved`. It never
copies original source documents, `needs_review` files, or `rejected` files.
When a matching `_RAPORT` file is available, it is copied too. If a report is
missing, the export still copies the approved `_ANON` file and records the
missing report by output basename only.

The approved workspace also writes:

```text
_APPROVED_INDEX.txt
```

The index contains only safe metadata: export timestamp, copied counts,
basenames of copied `_ANON` files, copied report basenames, missing-report
basenames, safe risk levels when already available, and statements that
approval was a manual user decision. It does not contain document contents,
source values, private dictionary terms, dictionary aliases, full paths,
tracebacks, or replacement maps.

Existing approved workspace files are not silently overwritten. If a file or
index already exists, the application writes a numbered name such as:

```text
document_ANON_2.txt
_APPROVED_INDEX_2.txt
```

The approved workspace is a staging area only. It is not a knowledge base and
does not guarantee complete anonymization.

It also does not replace manual review. A file in `approved/` is only a copy of
an output that the user marked `approved` after review.

## 8. Safety Rules for Users

- Do not place real documents in the repository.
- Do not commit a real private sensitive terms dictionary.
- Keep original files outside the project folder.
- Keep real dictionary files outside the repository or inside an ignored
  `private/` folder.
- Review anonymized output manually.
- Do not share output until you have checked it.

## 9. How Anonymized Labels Work

The Stage 1 engine replaces supported values with labels such as `PESEL`, `EMAIL`, `TELEFON`, or `DATA`.

## 10. Private Sensitive Terms Dictionary

The app supports an optional private local dictionary for terms that the user
knows should be replaced. The file is a UTF-8 text file with one entry per line:

```text
Person One Example = [IMIE NAZWISKO]
Example Institution = [NAZWA PODMIOTU]
```

Stage 11 also supports aliases on one line:

```text
Person One Example | P. One Example | PERSON ONE EXAMPLE = [IMIE NAZWISKO]
Example Institution | Example Inst. = [NAZWA PODMIOTU]
```

Blank lines are ignored. Lines starting with `#` are comments. Malformed lines
make the dictionary invalid and the workflow reports a safe line-number status
without exposing the private line content.

The real dictionary must stay private and must not be committed. The repository
contains only synthetic examples:

```text
examples/sensitive_terms.example.txt
examples/sensitive_terms.seed.example.txt
examples/dictionary_candidates.example.txt
```

When a dictionary is selected, the app replaces matching terms with the
specified labels and reports only status names, safe label counters, and
whether dictionary matches were found. It does not display dictionary contents,
write original dictionary terms to reports, or create a replacement map. Longer
aliases are applied before shorter aliases, so a term like
`Person One Example` is handled before `Person`.

Dictionary status meanings:

- `not selected`: no dictionary path was provided.
- `loaded`: a dictionary path was provided and parsed successfully.
- `invalid`: a dictionary path was provided but could not be loaded or parsed.

If the dictionary is loaded but none of its terms appear in the document, the
GUI and report show that no dictionary matches were found.

Save private dictionary files as UTF-8 text. If a dictionary is selected but no
replacements appear, check file encoding first, then verify the dictionary
status in the GUI, dictionary counters in `_RAPORT`, and dictionary
replacements in `_ANON`. Use small synthetic files for the first check.

Private dictionary matching is deterministic, case-insensitive, and tolerant of
extra spaces inside matched terms. It is not fuzzy matching, inflection
handling, AI, automatic names or address detection, NER, a database, or
automatic deletion of originals.

## 11. Local NER / NLP

The optional NER layer uses spaCy locally. It is meant as a review-support
foundation, not a guarantee that every name, organization, or location is
found.

To enable it, install dependencies and a Polish spaCy model in your local
Python environment:

```bash
pip install -r requirements.txt
python -m spacy download pl_core_news_sm
python -c "import spacy; spacy.load('pl_core_news_sm'); print('NER model available')"
```

The app does not run model download commands automatically. If spaCy or the
model is missing, the workflow still processes supported files and records a
controlled NER status such as `dependency_missing` or `model_missing`.

Safe reports and batch summaries show NER status and category counters only.
They never include detected entity text.

## 12. Local LLM Review / Ollama

The optional LLM review layer is a local post-anonymization quality-control
signal. It is disabled unless the user enables it and enters a local Ollama
model name. The model must already be installed by the user; the app never
runs `ollama pull` and never downloads models automatically.

Controlled LLM statuses include `disabled`, `ollama_not_found`,
`service_unavailable`, `no_model_configured`, `model_missing`, `timeout`,
`invalid_response`, `processing_error`, and `completed`.

The model is asked for strict structured JSON only. If the model returns
invalid JSON or unexpected values, the workflow records `invalid_response` and
continues. Reports store only status, safe model name, risk level, allowed
residual category names, and manual-review metadata. They do not store raw
prompts or raw model responses.

LLM review can miss sensitive context, misclassify harmless context, or fail
because the local model or Ollama service is unavailable. It does not replace
regex replacements, private dictionary matching, NER, the deterministic audit,
or manual review.

## 13. Post-Anonymization Audit

Stage 9 adds a safe audit after the `_ANON` output is generated. The workflow
passes successfully loaded dictionary aliases into that audit. The audit checks
the anonymized output text for conservative suspicious remaining patterns such
as e-mail, PESEL, phone, date, private dictionary aliases, case/reference
numbers, postal codes, simple address/street-like text, initial plus surname
patterns, ID-like numbers, and long number sequences.

The GUI shows audit status, risk counts, and counters by category only. The
report includes a safe `Post-anonymization audit` section. If loaded dictionary
aliases remain, the audit may show only a safe counter such as
`SENSITIVE_DICTIONARY_TERM`. The audit does not show or store original
detected values, text snippets, dictionary aliases, full document text, or
replacement maps.

`Audit status: OK` means the simple audit did not find supported suspicious
patterns. It does not prove that the document is fully anonymized.

`Audit status: WARNING` means the output may still contain suspicious
sensitive-looking data and must be checked carefully.

Stage 16 adds a risk level for manual-review prioritization:

- `ok`: no audit warning counters.
- `warning`: warning counters exist, but no high-risk condition is met.
- `high_risk`: at least one high-risk category is present or total audit
  warnings reach 3.

High-risk categories are `EMAIL`, `PESEL`, `TELEFON`,
`SENSITIVE_DICTIONARY_TERM`, `ADDRESS_LIKE`, `ID_LIKE_NUMBER`, and
`LONG_NUMBER_SEQUENCE`. The risk level is not a guarantee that anonymization is
complete and it does not approve a file automatically.

## 14. Why Manual Review Is Required

Automatic detection and the audit may miss data or replace text incorrectly.
Manual review is required before using the result.

## 15. Where Output Files Are Saved

The application saves anonymized TXT and DOCX copies in the output folder
selected by the user with the `_ANON` suffix. PDF input is saved in the output
folder as `_ANON.txt`. A safe report is saved in the same output folder with
the `_RAPORT.txt` suffix. A batch summary is saved as `_BATCH_SUMMARY.txt`.
Original files must not be modified.

The application does not silently overwrite existing generated files. If a
target name already exists, the next numbered name is used:

```text
document_ANON.txt
document_ANON_2.txt
document_ANON_3.txt
```

The same rule applies to `_RAPORT.txt` reports and `_BATCH_SUMMARY.txt`.
Review summaries use the same collision-safe numbering style:

```text
_REVIEW_SUMMARY.txt
_REVIEW_SUMMARY_2.txt
_REVIEW_SUMMARY_3.txt
```

Approved workspace exports use the same collision-safe numbering style inside
`approved/` for copied files and `_APPROVED_INDEX.txt`.

## 16. What Is Not Implemented Yet

The current MVP includes plain string anonymization, TXT file input/output,
basic DOCX file input/output, text-based PDF input with TXT output, optional
local OCR foundation for image inputs and scanned-PDF fallback, optional local
spaCy NER, optional local Ollama review, a simple Tkinter GUI, batch
processing, an output folder workflow,
collision-safe output names, safe reports, optional private dictionary input,
dictionary status reporting, a safe post-anonymization audit with risk
prioritization, and manual review status tracking with approved workspace
staging. Production-grade entity detection, NER candidate export, AI, APIs,
cloud services, cloud LLMs, databases, drag and drop, advanced preview,
editing workflow, chat UI, document rewriting, automatic approval, real
knowledge-base creation,
rejected/needs-review folder routing, edited image output, and anonymized PDF
output are not implemented.
