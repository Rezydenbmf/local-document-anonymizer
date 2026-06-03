# User Guide

## 1. What This Application Is For

Local Document Anonymizer is a local desktop tool for replacing supported
sensitive values in documents with general labels.

## 2. What This Application Is Not For

It is not a cloud service, compliance guarantee, OCR tool, batch processor, or automatic privacy solution.

## 3. Basic Workflow

The current Stage 5 workflow is:

1. Run `python src/main.py`.
2. Select one supported file.
3. Click `Anonymize`.
4. Check the status, category counters, and output path.
5. Manually review the anonymized output file before using or sharing it.

## 4. Supported Files in Current Stage

Stage 5 supports ordinary `.txt` files, basic `.docx` files, and text-based
`.pdf` files.

TXT files are read locally as UTF-8 text. The anonymized result is saved as a
separate copy with `_ANON` added to the filename:

```text
document.txt -> document_ANON.txt
```

DOCX files are also read locally. The anonymized result is saved as a separate
copy with `_ANON` added to the filename:

```text
document.docx -> document_ANON.docx
```

Original TXT and DOCX files are not modified.

Text-based PDF files are read locally and the extracted text is anonymized into
a TXT file:

```text
document.pdf -> document_ANON.txt
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
advanced document preview, PDF writing, and final report files are not
supported.

## 5. Safety Rules for Users

- Do not place real documents in the repository.
- Keep original files outside the project folder.
- Review anonymized output manually.
- Do not share output until you have checked it.

## 6. How Anonymized Labels Work

The Stage 1 engine replaces supported values with labels such as `PESEL`, `EMAIL`, `TELEFON`, or `DATA`.

## 7. Why Manual Review Is Required

Automatic detection may miss data or replace text incorrectly. Manual review is required before using the result.

## 8. Where Output Files Are Saved

Stage 5 saves anonymized TXT and DOCX copies next to the source file with the
`_ANON` suffix. PDF input is saved next to the source as `_ANON.txt`. Original
files must not be modified.

## 9. What Is Not Implemented Yet

Stage 5 includes plain string anonymization, TXT file input/output, basic DOCX
file input/output, text-based PDF input with TXT output, and a simple Tkinter
GUI for one selected file. Final reports, names, addresses, cities,
organizations, OCR, AI, APIs, drag and drop, batch processing, advanced preview,
and anonymized PDF output are not implemented.
