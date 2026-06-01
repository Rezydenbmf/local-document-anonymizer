# User Guide

## 1. What This Application Is For

Local Document Anonymizer is planned as a local desktop tool for replacing sensitive values in documents with general labels.

## 2. What This Application Is Not For

It is not a cloud service, compliance guarantee, OCR tool, batch processor, or automatic privacy solution.

## 3. Basic Workflow

The planned workflow is:

1. Select a supported file.
2. Extract text locally.
3. Run anonymization.
4. Preview the result.
5. Manually review and correct the output.
6. Save an anonymized copy.
7. Save a report without source values.

## 4. Supported Files in MVP

The MVP plans to support TXT, DOCX, and text-based PDF files. The current Stage 0 skeleton does not process files yet.

## 5. Safety Rules for Users

- Do not place real documents in the repository.
- Keep original files outside the project folder.
- Review anonymized output manually.
- Do not share output until you have checked it.

## 6. How Anonymized Labels Work

Sensitive values will be replaced with labels such as `IMIE NAZWISKO`, `PESEL`, `EMAIL`, or `ADRES`.

## 7. Why Manual Review Is Required

Automatic detection may miss data or replace text incorrectly. Manual review is required before using the result.

## 8. Where Output Files Will Be Saved in Future Versions

Future versions will save anonymized copies separately from the original files. Original files must not be modified.

## 9. What Is Not Implemented Yet

Stage 0 does not include real anonymization, file processing, GUI screens, or final reports.
