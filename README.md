# local-document-anonymizer

Local Document Anonymizer is a local-first desktop application for
anonymizing text documents on a user's own computer.

The project is currently in Stage 9: post-anonymization audit.
The Stage 0-9 MVP includes a narrow regex-based plain text anonymization
engine, optional private exact-term dictionary support, TXT input/output, basic
local DOCX input/output, text-based PDF input that saves anonymized TXT output,
a simple Tkinter GUI for one selected file, safe TXT report output without
source values, and a safe post-anonymization audit with category counters only.

## Project Goal

The goal is to build a simple, maintainable, offline tool that helps users
replace supported sensitive values in documents with general uppercase labels,
then manually review the generated anonymized output before trusting or sharing
it.

Current MVP document flow:

1. Select a TXT, DOCX, or text-based PDF file.
2. Optionally select a private sensitive terms dictionary file.
3. Extract text locally.
4. Detect supported regex values and optional private exact terms.
5. Replace detected values with labels such as `PESEL`, `EMAIL`, `TELEFON`,
   `DATA`, or user-defined dictionary labels.
6. Save an anonymized copy with an `_ANON` suffix.
7. Audit the anonymized output for suspicious remaining patterns.
8. Save a safe report with a `_RAPORT.txt` suffix.
9. Manually review the anonymized output outside the application.

## MVP Scope

The current MVP includes:

- TXT input and output.
- Basic DOCX input and output.
- Text-based PDF input support with TXT output.
- Optional private sensitive terms dictionary support.
- Safe post-anonymization audit with category counters only.
- Simple label-based anonymization.
- Simple GUI workflow for one selected file.
- Reports without original sensitive values.
- Manual review as a required user step.

## Local-First and Offline

This project is designed to run locally. It must not use cloud services, external APIs, OpenAI API, network calls, OCR, local LLMs, or a database unless a future project decision explicitly approves that change.

## Test Data Policy

The repository must contain only synthetic test data. Do not add real documents, real personal data, logs, local configuration files, or generated output from real data.

## What Is Not Implemented Yet

The current project implements TXT file input/output, basic DOCX file
input/output, text-based PDF input that writes anonymized TXT output, optional
private exact-term dictionary input, a simple Tkinter GUI, and safe TXT reports
with category counters and post-anonymization audit metadata only. It does not
implement:

- Anonymized PDF output.
- OCR or scanned PDF text extraction.
- Advanced document preview or editing.
- Batch processing.
- Drag and drop.
- Automatic names, cities, organizations, context-based detection, OCR, AI,
  APIs, cloud services, local LLMs, or databases.

DOCX support is limited to basic paragraphs and simple tables. It does not
cover headers, footers, comments, footnotes, form fields, text in images, or
advanced DOCX elements.

PDF support is limited to files that already contain an extractable text layer.
Scanned PDFs are not supported, OCR is not included, layout preservation is not
guaranteed, and PDF input produces `document_ANON.txt` rather than an
anonymized PDF.

Report support is limited to safe TXT reports named `document_RAPORT.txt`.
Reports include status, input and output type, anonymization category counters,
post-anonymization audit status and counters, and manual review/security notes.
They do not include original source values, full input paths, source filenames,
replacement maps, dictionary terms, text snippets, or document content.

Private dictionary support is limited to a user-maintained local text file with
lines in this format:

```text
Person One Example = [IMIE NAZWISKO]
```

The real dictionary must stay private and must not be committed. It can live
outside the repository or inside an ignored `private/` folder. The repository
contains only a synthetic example at `examples/sensitive_terms.example.txt`.
Reports show only dictionary labels and counts, never original dictionary
terms.

Post-anonymization audit support is limited to conservative regex checks on the
already anonymized output text. It can warn about suspicious remaining e-mail,
PESEL, phone, date, private dictionary term, case/reference, postal-code, and
simple address-like patterns. It does not guarantee complete anonymization and
does not store original values, snippets, dictionary terms, or replacement
maps.

## Manual Review Requirement

Anonymization and the post-anonymization audit can miss values or replace too
much. Every anonymized result must be manually reviewed by the user before it
is trusted or shared.

## Installation

Use a local Python environment. The project dependencies are intentionally
small:

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Running the Application

Run the GUI entry point:

```bash
python src/main.py
```

Run the tests:

```bash
python -m unittest discover -s tests
```

## Basic Workflow Example

For a TXT file named `document.txt`, the current GUI workflow creates:

```text
document.txt -> document_ANON.txt
document.txt -> document_RAPORT.txt
```

For a DOCX file named `document.docx`, it creates:

```text
document.docx -> document_ANON.docx
document.docx -> document_RAPORT.txt
```

For a text-based PDF named `document.pdf`, it creates extracted TXT output:

```text
document.pdf -> document_ANON.txt
document.pdf -> document_RAPORT.txt
```

The original file is not modified. The `_RAPORT.txt` file contains
anonymization counters, audit counters, and safety notes only, not source
values.

## Portfolio Summary

GitHub repository description:

```text
Local-first Python/Tkinter document anonymizer for TXT, basic DOCX, and text-based PDF input, with safe reports and synthetic tests.
```

CV bullet:

```text
Built a local-first Python desktop MVP for document anonymization, covering TXT, basic DOCX, and text-based PDF workflows with safe report generation and synthetic unit tests.
```

LinkedIn/project summary:

```text
Local Document Anonymizer is a portfolio MVP for offline document anonymization. It uses deterministic regex rules, keeps processing on the user's computer, writes separate anonymized outputs and safe reports, and documents its limitations clearly: no OCR, AI, cloud services, batch processing, or guarantee of perfect anonymization.
```

## Basic Development Plan

1. Repository skeleton and documentation.
2. Plain text anonymization engine. Complete for Stage 1.
3. TXT file input and output. Complete for Stage 2.
4. DOCX support. Complete for Stage 3.
5. Text-based PDF support. Complete for Stage 4.
6. Simple Tkinter GUI. Complete for Stage 5.
7. Reports without source values. Complete for Stage 6.
8. Portfolio polish and release review. Complete for Stage 7.
9. Private sensitive terms dictionary. Complete for Stage 8.
10. Post-anonymization audit. Current Stage 9.
