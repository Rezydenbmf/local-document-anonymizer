# Project Scope

## What the Application Does

The planned application will help users anonymize text documents locally by replacing sensitive values with general uppercase labels.

## MVP Scope

The MVP is planned to support:

- TXT files.
- DOCX files.
- Text-based PDF files.
- Simple label-based anonymization.
- Preview of anonymized text.
- Manual review before saving.
- Reports without original source values.

## Data Types Planned for Anonymization

Planned labels include:

- `IMIE NAZWISKO`
- `PESEL`
- `DATA`
- `MIEJSCOWOSC`
- `ULICA`
- `NUMER`
- `TELEFON`
- `EMAIL`
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
