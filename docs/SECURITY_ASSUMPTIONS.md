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

Reports may include status, input type, output type, anonymization category
counters, safe dictionary status metadata, dictionary label counters,
post-anonymization audit status and counters, and manual review/security notes
only. They must not include document text, detected source values, full input
paths, full input filenames, text snippets, dictionary source aliases, or logs
containing document content.

Batch summary reports may include safe input filenames, safe generated output
filenames, safe generated report filenames, aggregate category counters, audit
status counts, and controlled error descriptions. They must not include full
paths, source document text, detected source values, dictionary aliases,
private dictionary terms, raw exception messages, or replacement maps.

## No Replacement Map

The application must not store a map from original sensitive values to replacement labels.

## Private Sensitive Terms Dictionary

The app supports an optional private local sensitive terms dictionary maintained
by the user. The real dictionary must not be committed to the repository. It
should live outside the repository or inside an ignored folder such as
`private/`.

The repository may contain only synthetic dictionary examples, such as
`examples/sensitive_terms.example.txt`,
`examples/sensitive_terms.seed.example.txt`, and
`examples/dictionary_candidates.example.txt`.

Dictionary contents must not be displayed in the GUI, written to reports, logged
as source values, or turned into a persisted replacement map. Reports may show
only dictionary status names, match yes/no metadata, labels, and counts, for
example `IMIE NAZWISKO: 2`.

Stage 11 dictionary aliases are source terms. Alias support, case-insensitive
matching, and whitespace-tolerant matching must not weaken the rule that
reports, audit metadata, GUI status, tests, and documentation expose labels and
counts only.

## Post-Anonymization Audit

Stage 9/10.1 audit results must contain only safe metadata: audit status,
categories, counters, safe workflow dictionary metadata, and the manual review
flag.

The audit must not return, save, display, or log original detected values, text
snippets, private dictionary terms, full document text, full source paths, or a
replacement map.

When a dictionary loads successfully, the workflow may pass its private aliases
into the audit so remaining dictionary matches can be counted as
`SENSITIVE_DICTIONARY_TERM`. The audit is a warning layer only. `ok` status
does not guarantee complete anonymization, and `warning` status does not
include the suspicious source values. Manual review remains required for every
output.

## Original Files Are Not Modified

Original user files must remain unchanged. Generated files are saved as
separate anonymized copies in the output folder selected by the user. Existing
generated files must not be silently overwritten; numbered suffixes are used
when a target name already exists.

## Synthetic Test Data Only

The repository may contain only synthetic examples and tests. Real documents and personal data must stay out of the repository.

Generated `_ANON` and `_RAPORT` files from real data must not be committed.
Generated `_BATCH_SUMMARY` files from real data must not be committed. Logs,
local configuration files, `.env` files, private folders, real private
dictionaries, and real input documents must also stay out of git.

## Manual Review Required

The user must review anonymized output before trusting or sharing it.

## No Perfect Anonymization Guarantee

The tool can support anonymization but cannot guarantee that all sensitive values are removed.

The post-anonymization audit also cannot guarantee that all remaining sensitive
values are detected.

## Repository Privacy Risk

Users must not manually place real documents inside the repository. Folders such as `private/`, `real_data/`, `output/`, `outputs/`, `exports/`, and `data/` are ignored as an extra guard, but ignored files can still exist locally.

Before a release or portfolio commit, run a repository check for ignored data
folders, generated outputs, logs, local config files, private paths, and
non-synthetic source values or dictionary terms.
