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
- Optional private sensitive terms dictionary support.
- Private dictionary aliases, case-insensitive matching, and
  whitespace-tolerant term matching.
- Simple label-based anonymization.
- A simple Tkinter GUI for selected supported files.
- A selected output folder for generated files.
- Sequential batch processing.
- Collision-safe generated filenames.
- Separate `_ANON` output files.
- Safe `_BATCH_SUMMARY` batch reports.
- Safe post-anonymization audit status, risk level, and counters.
- Reports without original source values.
- Manual review after output is generated.

## Data Types Implemented in the Current Engine

Built-in regex labels are:

- `PESEL`
- `DATA`
- `TELEFON`
- `EMAIL`

The private dictionary also supports user-defined labels from a private local
dictionary, for example `IMIE NAZWISKO` or `NAZWA PODMIOTU`. These labels are
manually defined by the user and are not automatic entity detection.

Audit warning categories include:

- `EMAIL`
- `PESEL`
- `TELEFON`
- `DATA`
- `SENSITIVE_DICTIONARY_TERM`
- `CASE_REFERENCE`
- `POSTAL_CODE`
- `ADDRESS_LIKE`
- `STREET_LIKE`
- `INITIAL_SURNAME`
- `ID_LIKE_NUMBER`
- `LONG_NUMBER_SEQUENCE`

Audit categories and risk levels are review-prioritization metadata only. They
are not a guarantee that all sensitive values were found.

## Private Dictionary Safety

Real private dictionaries must not be committed to the repository. They should
live outside the repository or inside an ignored folder such as `private/`.

Reports may include only labels and counts from dictionary matches. They must
not include original dictionary aliases, source terms, or a replacement map.

Audit results and reports may include only categories, counters, status, risk
level, and manual review metadata. They must not include original values,
dictionary terms, text snippets, or a replacement map.

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

Automated anonymization and the audit can miss sensitive values or replace
non-sensitive text. The user must manually review the result before sharing or
storing it.

## Outside MVP Scope

The MVP will not include:

- OCR.
- Scanned PDF support.
- Excel support.
- Local AI models.
- Cloud services.
- APIs.
- Databases.
- Fuzzy matching, inflection handling, NER, or automatic entity extraction.
- Drag and drop, document preview, or document editing.
- Automatic deletion of original files.

## What the Application Does Not Guarantee

The application will not guarantee perfect anonymization. It is a support tool, not a legal or compliance guarantee.
