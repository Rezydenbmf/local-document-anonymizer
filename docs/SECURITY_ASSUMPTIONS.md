# Security Assumptions

## Local-Only Processing

The application is designed to process documents locally on the user's computer.

## No Cloud or Network

The project must not send documents, extracted text, reports, or metadata to cloud services or network endpoints.

## No API

The project must not use external APIs, including AI APIs.

No internet, API, cloud, AI, OCR, local LLM, or database dependency should be
added without an explicit project decision.

## No Original Sensitive Values in Reports

Reports must not include original source values. They may include safe metadata such as label names and counts.

Stage 6 reports may include status, input type, output type, category counters,
and manual review/security notes only. They must not include document text,
detected source values, full input paths, full input filenames, or logs
containing document content.

## No Replacement Map

The application must not store a map from original sensitive values to replacement labels.

## Original Files Are Not Modified

Original user files must remain unchanged. Future output should be saved as a separate anonymized copy.

## Synthetic Test Data Only

The repository may contain only synthetic examples and tests. Real documents and personal data must stay out of the repository.

Generated `_ANON` and `_RAPORT` files from real data must not be committed.
Logs, local configuration files, `.env` files, private folders, and real input
documents must also stay out of git.

## Manual Review Required

The user must review anonymized output before trusting or sharing it.

## No Perfect Anonymization Guarantee

The tool can support anonymization but cannot guarantee that all sensitive values are removed.

## Repository Privacy Risk

Users must not manually place real documents inside the repository. Folders such as `private/`, `real_data/`, `output/`, `outputs/`, `exports/`, and `data/` are ignored as an extra guard, but ignored files can still exist locally.

Before a release or portfolio commit, run a repository check for ignored data
folders, generated outputs, logs, local config files, private paths, and
non-synthetic source values.
