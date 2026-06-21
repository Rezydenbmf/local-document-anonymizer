# Lessons Learned

## 1. Repo is the source of truth, not the chat.

Project decisions, current status, and module details must live in repository files. Chat context can disappear or become outdated.

## 2. Keep the first MVP narrow.

A small working flow is easier to review, test, and secure than a broad unfinished system.

## 3. Do not store replacement maps with original sensitive data.

Replacement maps can become a second copy of private data. Reports should describe labels and counts, not original values.

## 4. Never commit real documents or personal data.

The repository is for code, documentation, tests, and synthetic examples only.

## 5. Codex must report changes in a fixed format.

A consistent report makes review easier and helps catch risky files before commits.

## 6. Test on synthetic data first.

Synthetic examples reduce privacy risk and make automated tests safe to keep in the repository.

## 7. Every major module must be documented.

Module documentation helps future contributors understand boundaries, responsibilities, and safety rules.

## 8. User documentation and technical documentation serve different purposes.

User docs explain how to operate the app. Technical docs explain how the system is built and maintained.

## 9. A working narrow MVP is better than an unfinished advanced system.

Reliability, safety, and reviewability matter more than adding many features early.

## 10. Confirm the target directory before creating a project.

Before creating a new repository, project skeleton, or large file set, ask the user to confirm the exact local path. A correct structure in the wrong directory still creates cleanup work.

## 11. Portfolio documentation must be as honest as the limitations.

A portfolio README should explain the working flow, installation, safety model,
and limits with the same clarity as the implemented features.

## 12. Do not add OCR, PDF editing, or broad NLP before the core workflow is reviewed.

Large document-processing features increase safety and testing risk. They should
come after the narrow local workflow, reports, documentation, and review checks
are stable.

## 13. Manual GUI smoke tests are required for file-based workflows.

Automated tests are necessary, but GUI and pipeline features still need a
small manual smoke test when they depend on real file selection. Use small
synthetic TXT and private dictionary files before trying real documents. Save
those files as UTF-8, especially when creating them from PowerShell, because
incompatible encoding can create false negatives where the workflow appears to
fail even though the feature works with correctly encoded files.

## 14. README must move with user-facing behavior.

The README is the portfolio entry point. After meaningful feature changes,
review it for accuracy around supported formats, workflow, limitations,
installation, usage, privacy assumptions, and current stage before presenting
the work for commit.

## 15. GUI convenience must preserve the privacy boundary.

Usability shortcuts such as clearing selections, removing selected files from a
GUI list, or opening generated outputs should never delete source files,
inspect document contents, expose private paths, or imply automatic approval.
Status messages should use safe filenames and plain language. Disabled primary
actions should explain what is missing before the user can continue.

## 16. Approved staging is not proof of anonymization.

An approved workspace can help organize manually reviewed `_ANON` files, but it
must stay described as a staging area. It should copy only manual approvals,
keep manifests to safe basenames and metadata, and avoid knowledge-base or
complete-anonymization claims.

## 17. End-to-end validation should test the whole safe metadata chain.

Module tests are useful, but the MVP workflow also needs synthetic tests that
cross module boundaries: batch output, reports, audit risk levels, manual
review, approved export, and approved index safety. These tests should verify
what is not stored just as carefully as they verify what is created.

## 18. OCR must be optional, local, and treated as imperfect extraction.

OCR support should start with controlled availability detection and mocked
synthetic tests. Missing Python packages, missing Tesseract, unsupported input,
or empty OCR text should become safe statuses, not crashes or tracebacks.
Reports and summaries may record OCR metadata, but they must not store raw OCR
text. Manual review remains required because OCR can miss or distort sensitive
data.

## 19. NER must be optional, local, and treated as imperfect detection.

NER support should start with controlled availability detection and mocked
synthetic tests. Missing spaCy, missing local models, disabled NER, or
processing errors should become safe statuses, not crashes or tracebacks.
Reports and summaries may record NER metadata and internal category counters,
but they must not store detected entity text. Manual review remains required
because NER can miss or misclassify sensitive data.
