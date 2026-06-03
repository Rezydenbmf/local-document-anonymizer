# local-document-anonymizer

Local Document Anonymizer is a local-first desktop application for anonymizing text documents on a user's own computer.

The project is currently in Stage 5. It contains the repository skeleton, a
narrow regex-based plain text anonymization engine for Python strings, TXT file
input/output helpers, basic local DOCX input/output support, and text-based PDF
input support that saves anonymized TXT output. It also includes a simple
Tkinter GUI for anonymizing one selected supported file.

## Project Goal

The goal is to build a simple, maintainable, offline tool that helps users replace sensitive values in documents with general uppercase labels, then manually review the result before saving an anonymized copy.

Planned document flow:

1. Select a TXT, DOCX, or text-based PDF file.
2. Extract text locally.
3. Detect sensitive data.
4. Replace detected values with labels such as `IMIE NAZWISKO`, `PESEL`, or `EMAIL`.
5. Review the result manually.
6. Save an anonymized copy.
7. Save a report that does not contain original source values.

## MVP Scope

The planned MVP includes:

- TXT input and output.
- Basic DOCX input and output.
- Text-based PDF input support with TXT output.
- Simple label-based anonymization.
- Simple GUI workflow for one selected file.
- Manual review.
- Reports without original sensitive values.

## Local-First and Offline

This project is designed to run locally. It must not use cloud services, external APIs, OpenAI API, network calls, OCR, local LLMs, or a database unless a future project decision explicitly approves that change.

## Test Data Policy

The repository must contain only synthetic test data. Do not add real documents, real personal data, logs, local configuration files, or generated output from real data.

## What Is Not Implemented Yet

The current project implements TXT file input/output, basic DOCX file
input/output, and text-based PDF input that writes anonymized TXT output. It
does not
implement:

- Anonymized PDF output.
- OCR or scanned PDF text extraction.
- Advanced document preview or editing.
- Batch processing.
- Drag and drop.
- Report generation beyond placeholders.
- Names, cities, organizations, context-based detection, OCR, AI, APIs, cloud services, local LLMs, or databases.

DOCX support is limited to basic paragraphs and simple tables. It does not
cover headers, footers, comments, footnotes, form fields, text in images, or
advanced DOCX elements.

PDF support is limited to files that already contain an extractable text layer.
Scanned PDFs are not supported, OCR is not included, layout preservation is not
guaranteed, and PDF input produces `document_ANON.txt` rather than an
anonymized PDF.

## Manual Review Requirement

Anonymization can miss values or replace too much. Every anonymized result must be manually reviewed by the user before it is trusted or shared.

## Running the Application

Run the GUI entry point:

```bash
python src/main.py
```

Run the tests:

```bash
python -m unittest discover -s tests
```

## Basic Development Plan

1. Repository skeleton and documentation.
2. Plain text anonymization engine. Complete for Stage 1.
3. TXT file input and output. Complete for Stage 2.
4. DOCX support. Complete for Stage 3.
5. Text-based PDF support. Complete for Stage 4.
6. Simple Tkinter GUI. Complete for Stage 5.
7. Reports without source values.
8. Tests and portfolio polish.
