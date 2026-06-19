# Module: MVP Workflow Validation

## Purpose

This module documents Stage 18: end-to-end workflow validation and MVP
stabilization.

Stage 18 validates the complete local MVP path with synthetic data:

```text
source files
-> batch anonymization
-> safe reports
-> post-anonymization audit risk levels
-> manual review metadata
-> approved workspace export
-> safe approved index
```

It does not add runtime features. It is a stabilization and documentation
stage for the existing MVP workflow.

## Related files

- `tests/test_stage18_end_to_end.py`
- `docs/MVP_MANUAL_TEST_CHECKLIST.md`
- `src/anonymizer.py`
- `src/report.py`
- `src/review.py`
- `docs/modules/06_REPORTING.md`
- `docs/modules/10_BATCH_OUTPUT_WORKSPACE.md`
- `docs/modules/11_MANUAL_REVIEW_WORKFLOW.md`
- `docs/modules/12_APPROVED_WORKSPACE.md`

## Validation Coverage

The Stage 18 regression tests cover:

- simple low-risk TXT batch anonymization, manual approval, and approved
  export,
- mixed-risk batch processing with `ok`, `warning`, and `high_risk` review
  prioritization,
- dictionary alias replacement with safe label-only reporting,
- DOCX and text-based PDF participation in the batch/review/export workflow,
- safe report, batch summary, review summary, and approved index metadata,
- ignore coverage for generated outputs and local-only workspaces.

All test data is synthetic.

## Manual Checklist

`docs/MVP_MANUAL_TEST_CHECKLIST.md` gives a practical manual smoke-test
sequence for a non-developer. It covers:

- preparing synthetic inputs,
- running batch anonymization,
- checking generated reports and risk levels,
- saving manual review metadata,
- exporting approved files,
- checking `_APPROVED_INDEX.txt`,
- confirming generated/local artifacts remain ignored.

## Safety Assumptions

- The workflow stays local-first and offline.
- No OCR, AI, API, cloud service, local LLM, NER, database, installer,
  split-screen review, highlighting, drag and drop, preview, editor, or
  automatic approval is added.
- Manual review remains required.
- Approved workspace export is a user-approved staging step only.
- Reports, summaries, review metadata, and approved indexes must not contain
  source values, document text, private dictionary aliases, full paths,
  tracebacks, or replacement maps.

## How to Test

Run:

```bash
python -m unittest discover -s tests
```

For a narrower Stage 18 check, run:

```bash
python -m unittest tests.test_stage18_end_to_end
```

## Known Limitations

- Stage 18 does not prove complete anonymization.
- The manual checklist still requires a human to inspect generated outputs.
- DOCX support remains basic and PDF support remains text-layer-only.
- Generated files from manual smoke tests must stay local and ignored.
