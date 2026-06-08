# Project Scope

## What the Application Does

The current MVP helps users anonymize supported text documents locally by
replacing selected high-confidence sensitive values with general uppercase
labels.

## Current MVP Scope

The current MVP supports:

- TXT files.
- DOCX files.
- Text-based PDF files.
- Simple label-based anonymization.
- A simple Tkinter GUI for one selected file.
- Separate `_ANON` output files.
- Reports without original source values.
- Manual review after output is generated.

## Data Types Implemented in the Current Engine

Implemented labels are:

- `PESEL`
- `DATA`
- `TELEFON`
- `EMAIL`

## Data Types Planned for Later Consideration

Potential future labels include:

- `IMIE NAZWISKO`
- `MIEJSCOWOSC`
- `ULICA`
- `NUMER`
- `NAZWA PODMIOTU`
- `ADRES`
- `INNE DANE`

## Why Manual Review Is Required

Automated anonymization can miss sensitive values or replace non-sensitive text. The user must manually review the result before sharing or storing it.

## Outside MVP Scope

The MVP will not include:

- OCR.
- Scanned PDF support.
- Excel support.
- Batch processing.
- Local AI models.
- Cloud services.
- APIs.
- Databases.
- Automatic deletion of original files.

## What the Application Does Not Guarantee

The application will not guarantee perfect anonymization. It is a support tool, not a legal or compliance guarantee.
