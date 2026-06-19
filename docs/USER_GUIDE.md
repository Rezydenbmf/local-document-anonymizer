# User Guide

## 1. What This Application Is For

Local Document Anonymizer is a local desktop tool for replacing supported
sensitive values in documents with general labels.

## 2. What This Application Is Not For

It is not a cloud service, compliance guarantee, OCR tool, document editor, or
automatic privacy solution.

## 3. Basic Workflow

The current MVP workflow is:

1. Run `python src/main.py` or `python -m src.gui`.
2. Add one or more supported files and check the selected-file count.
3. Select an output folder.
4. Optionally select a private sensitive terms file.
5. If `Anonymize batch` is disabled, read the readiness hint beside the button.
6. Click `Anonymize batch`.
7. Check the status, dictionary status, category counters, aggregate audit
   status, aggregate risk levels, generated filenames, and batch summary
   filename.
8. Manually review each anonymized output file before using or sharing it.
9. Use the manual review section to load the output folder, optionally open the
   selected generated output or matching report in the operating system
   default application, assign statuses, and save safe review metadata.
10. Optionally export approved files to an `approved/` staging workspace.

The application saves output files before manual review. It does not provide an
in-app document preview or editing screen.

The selected-file list is only a GUI selection. `Remove selected` and
`Clear files` remove files from that list only. They do not delete original
files from disk.

The readiness hint uses plain messages such as `Add at least one input file.`,
`Select an output folder.`, or `Ready to anonymize 3 file(s).` It does not show
document contents, source values, private dictionary terms, or full local paths.

## 4. Supported Files in Current Stage

The current MVP supports ordinary `.txt` files, basic `.docx` files, and text-based
`.pdf` files.

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

DOCX support is basic. It covers ordinary paragraphs and simple tables. It does
not cover headers, footers, comments, footnotes, form fields, text in images, or
advanced DOCX elements. Basic formatting is preserved only in a limited MVP
range.

PDF support requires an existing text layer. Scanned PDFs are not supported,
OCR is not included, and PDF layout preservation is not guaranteed.

OCR, AI, APIs, cloud services, databases, drag and drop, advanced document
preview, PDF writing, automatic entity detection, and detailed audit reports
with source snippets are not supported.

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
- post-anonymization audit status, risk level, and category counters,
- manual review requirement,
- confirmation that original sensitive values are not stored,
- confirmation that no replacement map was created.

The report does not contain document text, original sensitive values, full
input paths, source filenames, private dictionary terms, text snippets, or
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
- safe input, output, and report filenames,
- controlled safe error descriptions.

The batch summary does not contain source document text, original sensitive
values, private dictionary terms, aliases, replacement maps, full paths, or raw
exception messages.

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
handling, OCR, AI, automatic names or address detection, NER, a database, or
automatic deletion of originals.

## 11. Post-Anonymization Audit

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

## 12. Why Manual Review Is Required

Automatic detection and the audit may miss data or replace text incorrectly.
Manual review is required before using the result.

## 13. Where Output Files Are Saved

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

## 14. What Is Not Implemented Yet

The current MVP includes plain string anonymization, TXT file input/output, basic DOCX
file input/output, text-based PDF input with TXT output, a simple Tkinter GUI,
batch processing, an output folder workflow, collision-safe output names, safe
reports, optional private dictionary input, dictionary status reporting, a
safe post-anonymization audit with risk prioritization, and manual review
status tracking with approved workspace staging. Automatic names, broad
addresses, cities, organizations, OCR, AI, APIs, cloud services, local LLMs,
databases, drag and drop, advanced preview, editing workflow, automatic
approval, real knowledge-base creation, rejected/needs-review folder routing,
and anonymized PDF output are not implemented.
