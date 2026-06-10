# User Guide

## 1. What This Application Is For

Local Document Anonymizer is a local desktop tool for replacing supported
sensitive values in documents with general labels.

## 2. What This Application Is Not For

It is not a cloud service, compliance guarantee, OCR tool, batch processor, or automatic privacy solution.

## 3. Basic Workflow

The current MVP workflow is:

1. Run `python src/main.py`.
2. Select one supported file.
3. Optionally select a private sensitive terms file.
4. Click `Anonymize`.
5. Check the status, dictionary status, category counters, audit status, output
   path, and report path.
6. Manually review the anonymized output file before using or sharing it.

The application saves output files before manual review. It does not provide an
in-app document preview or editing screen.

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

OCR, AI, APIs, cloud services, databases, batch processing, drag and drop,
advanced document preview, PDF writing, automatic entity detection, and
detailed audit reports with source snippets are not supported.

## 5. Report Files

For every successful TXT, DOCX, or text-based PDF anonymization, the
application writes a separate `_RAPORT.txt` file next to the anonymized output.

The report contains:

- status,
- input type,
- output type,
- category counters,
- dictionary used/status/matches-found information,
- dictionary label counters,
- post-anonymization audit status and category counters,
- manual review requirement,
- confirmation that original sensitive values are not stored,
- confirmation that no replacement map was created.

The report does not contain document text, original sensitive values, full
input paths, source filenames, private dictionary terms, text snippets, or
replacement maps.

## 6. Safety Rules for Users

- Do not place real documents in the repository.
- Do not commit a real private sensitive terms dictionary.
- Keep original files outside the project folder.
- Keep real dictionary files outside the repository or inside an ignored
  `private/` folder.
- Review anonymized output manually.
- Do not share output until you have checked it.

## 7. How Anonymized Labels Work

The Stage 1 engine replaces supported values with labels such as `PESEL`, `EMAIL`, `TELEFON`, or `DATA`.

## 8. Private Sensitive Terms Dictionary

Stage 8 adds an optional private local dictionary for exact terms that the user
knows should be replaced. The file is a UTF-8 text file with one term per line:

```text
Person One Example = [IMIE NAZWISKO]
Example Institution = [NAZWA PODMIOTU]
```

Blank lines are ignored. Lines starting with `#` are comments. Malformed lines
stop the run with a safe line-number error.

The real dictionary must stay private and must not be committed. The repository
contains only a synthetic example:

```text
examples/sensitive_terms.example.txt
```

When a dictionary is selected, the app replaces matching terms with the
specified labels and reports only status names, safe label counters, and
whether dictionary matches were found. It does not display dictionary contents,
write original dictionary terms to reports, or create a replacement map. Longer
terms are applied before shorter terms, so a term like `Person One Example` is
handled before `Person`.

Dictionary status meanings:

- `not selected`: no dictionary path was provided.
- `loaded`: a dictionary path was provided and parsed successfully.
- `invalid`: a dictionary path was provided but could not be loaded or parsed.

If the dictionary is loaded but none of its terms appear in the document, the
GUI and report show that no dictionary matches were found.

Private dictionary matching is literal and case-sensitive. It is not OCR, AI,
automatic names or address detection, batch processing, a database, or automatic
deletion of originals.

## 9. Post-Anonymization Audit

Stage 9 adds a safe audit after the `_ANON` output is generated. Stage 10.1
passes successfully loaded dictionary terms into that audit. The audit checks
the anonymized output text for conservative suspicious remaining patterns such
as e-mail, PESEL, phone, date, private dictionary terms, case/reference
numbers, postal codes, and simple address-like text.

The GUI shows audit status and counters by category only. The report includes a
safe `Post-anonymization audit` section. If loaded dictionary terms remain, the
audit may show only a safe counter such as `SENSITIVE_DICTIONARY_TERM`. The
audit does not show or store original detected values, text snippets,
dictionary terms, full document text, or replacement maps.

`Audit status: OK` means the simple audit did not find supported suspicious
patterns. It does not prove that the document is fully anonymized.

`Audit status: WARNING` means the output may still contain suspicious
sensitive-looking data and must be checked carefully.

## 10. Why Manual Review Is Required

Automatic detection and the audit may miss data or replace text incorrectly.
Manual review is required before using the result.

## 11. Where Output Files Are Saved

The application saves anonymized TXT and DOCX copies next to the source file
with the `_ANON` suffix. PDF input is saved next to the source as `_ANON.txt`.
A safe report is saved next to the anonymized output with the `_RAPORT.txt`
suffix. Original files must not be modified.

If a TXT file and a PDF file have the same base name in the same folder, their
TXT output and report names can be confusing or collide. Use distinct test file
names or separate folders until a future approved output workflow changes this.

## 12. What Is Not Implemented Yet

The current MVP includes plain string anonymization, TXT file input/output, basic DOCX
file input/output, text-based PDF input with TXT output, and a simple Tkinter
GUI for one selected file. Safe reports, optional private dictionary input,
dictionary status reporting, and a safe post-anonymization audit are
implemented. Automatic names, broad addresses, cities, organizations, OCR, AI,
APIs, drag and drop, batch processing, advanced preview, and anonymized PDF
output are not implemented.
