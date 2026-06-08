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
3. Click `Anonymize`.
4. Check the status, category counters, output path, and report path.
5. Manually review the anonymized output file before using or sharing it.

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
advanced document preview, PDF writing, and detailed audit reports are not
supported.

## 5. Report Files

For every successful TXT, DOCX, or text-based PDF anonymization, the
application writes a separate `_RAPORT.txt` file next to the anonymized output.

The report contains:

- status,
- input type,
- output type,
- category counters,
- manual review requirement,
- confirmation that original sensitive values are not stored,
- confirmation that no replacement map was created.

The report does not contain document text, original sensitive values, full
input paths, source filenames, or replacement maps.

## 6. Safety Rules for Users

- Do not place real documents in the repository.
- Keep original files outside the project folder.
- Review anonymized output manually.
- Do not share output until you have checked it.

## 7. How Anonymized Labels Work

The Stage 1 engine replaces supported values with labels such as `PESEL`, `EMAIL`, `TELEFON`, or `DATA`.

## 8. Why Manual Review Is Required

Automatic detection may miss data or replace text incorrectly. Manual review is required before using the result.

## 9. Where Output Files Are Saved

The application saves anonymized TXT and DOCX copies next to the source file with the
`_ANON` suffix. PDF input is saved next to the source as `_ANON.txt`. A safe
report is saved next to the anonymized output with the `_RAPORT.txt` suffix.
Original files must not be modified.

## 10. What Is Not Implemented Yet

The current MVP includes plain string anonymization, TXT file input/output, basic DOCX
file input/output, text-based PDF input with TXT output, and a simple Tkinter
GUI for one selected file. Safe reports are implemented, but names, addresses, cities,
organizations, OCR, AI, APIs, drag and drop, batch processing, advanced preview,
and anonymized PDF output are not implemented.
