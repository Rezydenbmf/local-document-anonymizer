# Security and Quality Audit Report

**Date:** 2026-06-15
**Scope:** Pre-portfolio review — local-document-anonymizer
**Target:** GitHub public repo / CV code sample

---

## Summary

No secrets, credentials, API keys, or real personal data were found in the
tracked repo or git history. The repo is broadly safe to publish.

Three items need action before pushing. Two are minor `.gitignore` gaps. One
is a stale internal documentation section. Several low-priority quality notes
are included below.

---

## SECURITY / PRIVACY

### [ACTION REQUIRED] `_manual_test/` — private test data in working tree

- **Location:** `H:\firma\anonymizer\_manual_test\` (entire folder)
- **Status:** NOT committed to git — correctly covered by `_manual_test/` entry
  in `.gitignore`. Will not be pushed as-is.
- **What is there:** private dictionary files (`sensitive_terms.txt`,
  `sensitive_terms_full_example.txt`), raw DOCX / PDF / TXT test inputs
  (`stage10_simple.*`, `stage10_medium.*`, `stage10_complex.*`), generated
  `_ANON` and `_RAPORT` outputs, a batch summary. The folder-level README says
  "All files are fictional."
- **Why it still matters:** The content of `sensitive_terms.txt` was not read
  and its "fictional" status was not individually verified. Before pushing, you
  should confirm that no row in that file contains a real person's name,
  address, or case reference — especially if the dictionary was ever adapted
  from a real working dictionary.
- **Risk level:** Low if the content is genuinely fictional; potentially high
  if the dictionary was ever seeded from real data.
- **Suggested fix:** Open `_manual_test\knowledge_private\dictionary\sensitive_terms.txt`
  and manually confirm every entry is synthetic. If it is, the current setup is
  fine. For belt-and-suspenders safety, consider moving the entire
  `_manual_test\` folder to a location outside the repository tree (e.g.,
  `H:\firma\knowledge_private\`) so it cannot accidentally be staged.

---

### [ACTION REQUIRED] `examples/before/` and `examples/after/` — unguarded

- **Location:** `examples/before/.gitkeep`, `examples/after/.gitkeep`
- **Status:** Committed (as empty placeholder folders). NOT listed in
  `.gitignore`.
- **Risk:** If a user places real documents in these folders as "before/after"
  examples, they will be committed and pushed, since git tracks all new files
  there. The `*_ANON.*` and `*_RAPORT.*` patterns in `.gitignore` do not
  protect arbitrary filenames.
- **Suggested fix (pick one):**
  - Add to `.gitignore`:
    ```
    examples/before/*
    examples/after/*
    !examples/before/.gitkeep
    !examples/after/.gitkeep
    ```
  - Or remove the two folders entirely from git if they have no documented
    purpose (see Quality section below).

---

### [CLEAN] No secrets or credentials

- No API keys, passwords, tokens, or `.env` files found in working tree or
  git history.
- The full commit history (`git log --all --diff-filter=A`) was scanned. No
  `.env`, `.csv`, `.pdf`, `.docx`, `.pem`, or credential files were ever added.

### [CLEAN] No real personal data

- `tests/sample_data/sample_01.txt` and `sample_02.txt` — confirmed synthetic
  (`00000000000` as PESEL, `person.one@example.test`, `Person One Example`, etc.)
- `examples/sensitive_terms.example.txt`, `sensitive_terms.seed.example.txt`,
  `dictionary_candidates.example.txt` — confirmed synthetic only.
- No real names, PESELs, phone numbers, addresses, or case references found in
  any tracked file.

### [CLEAN] No absolute local paths

- All source-code paths use `Path(__file__).resolve().parent` anchors or are
  derived from user input. No `C:\Users\<username>\...` strings in any tracked
  file or error message.

### [CLEAN] `.gitignore` covers the main risk categories

The following are confirmed ignored:
- `.env` (and `*.log`, `*.tmp`, `*.bak`, `local_config.*`)
- `__pycache__/`, `*.py[cod]`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`
- `_manual_test/`, `private/`, `real_data/`, `data/`, `output/`, `outputs/`,
  `exports/`
- `*_ANON.*`, `*_RAPORT.*`, `*_BATCH_SUMMARY*.txt`
- `.DS_Store`, `Thumbs.db`

One gap: `examples/before/` and `examples/after/` (covered above).

---

## QUALITY / README ACCURACY

### [ACTION REQUIRED] `docs/PROJECT_STATE.md` — stale "Last Completed Committed Stage"

- **File:** `docs/PROJECT_STATE.md`, lines ~191–199
- **Issue:** The file says the last committed stage is Stage 9
  (`782eee1 Implement Stage 9 post-anonymization audit`) and labels Stage 12 as
  a "current working tree stage" that hasn't been committed yet. The git log
  shows all stages through Stage 12 are committed (latest commit:
  `e19d87c Implement Stage 12 batch output workspace`). A reviewer reading this
  file will think the repo is less complete than it is.
- **Suggested fix:** Update "Last Completed Committed Stage" to Stage 12 with
  hash `e19d87c`, and remove the now-obsolete "Current working tree stage"
  section.

---

### [LOW] `src/file_readers.py` line 15 — "Stage 4" leaked into error message

- **File:** `src/file_readers.py`, function `_unsupported_extension_error`, line 15
- **Issue:** The error message says `"Unsupported file extension for Stage 4: {suffix}."` 
  The internal stage number appears in what would be a user-facing or
  test-visible exception message. A portfolio reviewer reading tests or error
  output will see a development label.
- **Suggested fix:** Change to `"Unsupported file extension: {suffix}."` (see
  the same function in `file_writers.py` for the cleaner version).

---

### [LOW] `src/gui.py` line 341 — dead method `anonymize_selected_file`

- **File:** `src/gui.py`, line 341
- **Issue:** `anonymize_selected_file(self)` is a one-liner that calls
  `anonymize_selected_files(self)`. It is not wired to any button in `_build()`
  and appears to be a leftover from when the app was single-file only. No test
  file calls it by name.
- **Suggested fix:** Delete the method or confirm it is intentionally kept for
  external callers (if so, add a note).

---

### [LOW] `examples/before/` and `examples/after/` — not documented in README

- **File:** `README.md`, Project Structure section
- **Issue:** The README lists `examples/` as "Synthetic example inputs and
  dictionaries" and names three `.example.txt` files. The two placeholder
  subfolders (`before/`, `after/`) are not mentioned. A reviewer exploring the
  repo will find them and wonder what they're for.
- **Suggested fix:** Either add a line in the README explaining their purpose
  (e.g., "reserved placeholder folders for future before/after workflow
  examples"), or remove them from git if there is no near-term plan for them.

---

### [LOW] `AGENTS.md` is tracked and will be publicly visible

- **File:** `AGENTS.md`
- **Issue:** The file contains AI-assistant collaboration instructions and is
  committed. It is not sensitive, but a technical reviewer who opens the repo
  may not expect to find AI agent instructions in a portfolio project without
  any explanation.
- **Suggested fix (optional):** Add one line to the README Project Structure
  section: "`AGENTS.md` — AI assistant collaboration instructions (Codex/Claude
  workflow rules)." This turns a possible "why is this here?" moment into a
  deliberate portfolio choice.

---

### [LOW] `docs/PROJECT_STATE.md` is a detailed internal state log

- **File:** `docs/PROJECT_STATE.md`
- **Issue:** The file reads as an internal AI-assistant context document, with
  per-stage bullet lists and a "Last Committed Committed Stage" diff section.
  Once public, technical interviewers may find it either impressive (structured
  AI collaboration) or confusing (why is internal project management in the
  repo?).
- **Suggested fix (optional):** No action required unless you'd prefer not to
  expose it. It contains no sensitive data.

---

## What Is NOT a Problem

| Item | Status |
|------|--------|
| API keys / tokens | None present anywhere |
| Real personal data in tests | Confirmed synthetic only |
| Real personal data in examples | Confirmed synthetic only |
| Absolute machine paths | None found |
| `.env` files | Correctly gitignored |
| Private dictionary committed | Not committed — gitignored |
| Generated `_ANON` / `_RAPORT` outputs committed | Not committed — gitignored |
| `__pycache__` committed | Not committed — gitignored |
| Git history contains sensitive files | Confirmed clean |
| README describes features that don't exist | No — README is accurate |
| README omits major features | No — all 8 source modules described |
| Source modules listed in README match `src/` | Yes — 8/8 match |
| Test coverage claims in README | Plausible — 9 test files match described coverage |

---

---

## Round 2 — 2026-06-15 — Resolved

All actionable items (except `_manual_test/` which was confirmed synthetic and
left as-is) have been fixed. No commits or pushes were made.

| # | Item | File | Change |
|---|------|------|--------|
| 1 | `examples/before/` and `examples/after/` gitignore gap | `.gitignore` | Added `examples/before/*`, `examples/after/*` with negation rules for `.gitkeep` |
| 2 | Stale "Last Completed Committed Stage" (said Stage 9, should be Stage 12) | `docs/PROJECT_STATE.md` | Updated to Stage 12 / `e19d87c`; removed stale "Current working tree" distinction; updated "Next Logical Step" |
| 3 | "Stage 4" internal label in error message | `src/file_readers.py` line 15 | Changed `"Unsupported file extension for Stage 4: ..."` → `"Unsupported file extension: ..."` |
| 4 | Dead `anonymize_selected_file` wrapper method | `src/gui.py` line 341 | Removed the 3-line wrapper (confirmed unused in tests and not wired to any button) |
| 5 | `examples/before/` and `examples/after/` not explained in README | `README.md` | Added "Example Document Folders" section; added `before/` and `after/` entries to Project Structure block |
| 6 | `AGENTS.md` not mentioned in README | `README.md` | Added `AGENTS.md` entry in Project Structure block |

### Not actioned

- `_manual_test/` folder: confirmed by user to be synthetic test data; already
  gitignored; left as-is.

---

## Action Checklist

Before pushing:

- [x] Manually verify `_manual_test\knowledge_private\dictionary\sensitive_terms.txt`
      contains only fictional data — confirmed synthetic by user; left as-is
- [x] Fix `examples/before/` and `examples/after/` gitignore gap — done
- [x] Update `docs/PROJECT_STATE.md` "Last Completed Committed Stage" to Stage 12 — done

Optional (quality only):

- [x] Fix "Stage 4" string in `src/file_readers.py` error message — done
- [x] Remove dead `anonymize_selected_file` wrapper in `src/gui.py` — done
- [x] Document or remove `examples/before/` and `examples/after/` from README — documented
- [x] Add one-line note about `AGENTS.md` in README project structure — done
