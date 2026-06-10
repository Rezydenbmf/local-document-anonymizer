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
