# local-document-anonymizer

Local Document Anonymizer is a planned local-first desktop application for anonymizing text documents on a user's own computer.

The project is currently in Stage 1. It contains the repository skeleton plus a narrow regex-based plain text anonymization engine for Python strings.

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
- Later DOCX support.
- Later text-based PDF support.
- Simple label-based anonymization.
- Preview and manual review.
- Reports without original sensitive values.

## Local-First and Offline

This project is designed to run locally. It must not use cloud services, external APIs, OpenAI API, network calls, OCR, local LLMs, or a database unless a future project decision explicitly approves that change.

## Test Data Policy

The repository must contain only synthetic test data. Do not add real documents, real personal data, logs, local configuration files, or generated output from real data.

## What Is Not Implemented Yet

The current project does not implement:

- File input and output workflows.
- DOCX or PDF parsing.
- GUI workflows.
- Report generation beyond placeholders.
- Names, cities, organizations, context-based detection, OCR, AI, APIs, cloud services, local LLMs, or databases.

## Manual Review Requirement

Anonymization can miss values or replace too much. Every anonymized result must be manually reviewed by the user before it is trusted or shared.

## Running the Skeleton

Run the placeholder entry point:

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
3. TXT file input and output.
4. DOCX support.
5. Text-based PDF support.
6. Simple Tkinter GUI.
7. Reports without source values.
8. Tests and portfolio polish.
