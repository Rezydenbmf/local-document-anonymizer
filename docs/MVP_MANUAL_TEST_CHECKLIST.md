# MVP Manual Test Checklist

Use this checklist to validate the complete local MVP workflow with synthetic
files only. Do not use real documents, real personal data, private
dictionaries, logs, screenshots, generated outputs from real data, `.env`
files, or local configuration files.

The application runs locally. It does not use cloud services, APIs, AI, OCR,
local LLMs, or a database. Manual review is required for every generated
output.

## 1. Prepare A Safe Local Workspace

1. Create a local ignored test folder, for example `_manual_test/stage18/`.
2. Inside it, create:
   - `source/`
   - `output/`
3. Confirm the folder is ignored before adding test files:

```bash
git check-ignore -v _manual_test/stage18
```

If the folder is not ignored, stop and fix `.gitignore` before continuing.

## 2. Prepare Synthetic Inputs

Create small synthetic files in `_manual_test/stage18/source/`.

Suggested TXT files:

```text
simple.txt
Synthetic contact safe@example.test.
```

```text
warning.txt
Synthetic case reference ABC/123/2026 remains for review.
```

```text
high.txt
Synthetic address ul. Testowa 12 remains for review.
```

Suggested private dictionary:

```text
synthetic_dictionary.txt
Example Person | E. Person = [PERSON_LABEL]
Private Alias Example | P. Alias Example = [PRIVATE_LABEL]
```

Suggested dictionary workflow input:

```text
dictionary.txt
E. Person contacted dictionary@example.test. P. Alias Example was copied.
```

DOCX and text-based PDF can be included when available, but do not create
complex fixtures for this smoke test. Scanned PDFs are out of scope because OCR
is not included.

## 3. Run Batch Anonymization

1. Start the GUI:

```bash
python src/main.py
```

2. Add the synthetic files from `_manual_test/stage18/source/`.
3. Select `_manual_test/stage18/output/` as the output folder.
4. Optionally select `synthetic_dictionary.txt`.
5. Confirm the readiness hint says the app is ready to anonymize the selected
   files.
6. Click `Anonymize batch`.

Expected result:

- `_ANON` files are created in `output/`.
- `_RAPORT.txt` files are created in `output/`.
- `_BATCH_SUMMARY.txt` is created in `output/`.
- Original source files are not modified.

## 4. Check Reports And Risk Levels

Open each `_RAPORT.txt` file and `_BATCH_SUMMARY.txt`.

Confirm:

- Reports show counters and safe metadata only.
- Reports include `Manual review required: yes`.
- Reports include `Original sensitive values stored: no`.
- Reports include `Replacement map created: no`.
- Risk levels are present as `ok`, `warning`, or `high_risk`.
- The mixed-risk batch gives higher priority to higher-risk items.
- Dictionary reports show labels such as `[PERSON_LABEL]` or
  `[PRIVATE_LABEL]`, not source dictionary aliases.

Confirm the reports and summaries do not contain:

- source document text,
- original sensitive values,
- private dictionary terms or aliases,
- full local paths,
- replacement maps,
- tracebacks,
- logs.

## 5. Save Manual Review Metadata

1. In the GUI manual review section, select the `output/` folder.
2. Load detected generated outputs.
3. Confirm generated `_ANON` files are listed.
4. Confirm paired `_RAPORT` files are shown when present.
5. Confirm `high_risk` items appear before lower-risk items when risk metadata
   is available.
6. Mark at least one file `approved`.
7. Mark at least one file `needs_review` or `rejected`.
8. Save review metadata.

Expected result:

- `_REVIEW_STATUS.json` is created in `output/`.
- `_REVIEW_SUMMARY.txt` is created in `output/`.
- The review summary states that decisions are manual user decisions.
- The review summary does not contain document contents, source values,
  private dictionary terms, aliases, full paths, or replacement maps.

## 6. Export Approved Files

1. Click `Export approved`.
2. Open `output/approved/`.
3. Open `_APPROVED_INDEX.txt`.

Expected result:

- Only files marked `approved` are copied into `approved/`.
- `needs_review` files are not copied.
- `rejected` files are not copied.
- Original source files are not copied.
- Matching `_RAPORT` files are copied when available.
- `_APPROVED_INDEX.txt` contains basenames and safe metadata only.
- The index states that approval is a manual user decision.
- The index states that the approved workspace is a staging area, not a
  guarantee of complete anonymization.

Confirm the approved index does not contain:

- source document text,
- original sensitive values,
- private dictionary terms or aliases,
- full local paths,
- replacement maps,
- tracebacks,
- automatic approval claims,
- knowledge-base claims.

## 7. Final Safety Check

Before considering the manual smoke test complete, run:

```bash
git status --short --ignored _manual_test _local_diary
git status --short
```

Expected result:

- `_manual_test/` is shown only as ignored.
- `_local_diary/` is shown only as ignored.
- Generated `_ANON`, `_RAPORT`, `_BATCH_SUMMARY`, `_REVIEW_STATUS`,
  `_REVIEW_SUMMARY`, and `approved/` files are not proposed for commit.
- No real documents, private dictionaries, logs, screenshots, generated
  outputs, `.env`, local configs, or temporary files are tracked.

## 8. Pass Criteria

The smoke test passes only if:

- batch anonymization completes for the synthetic inputs,
- safe reports are generated,
- risk levels are visible,
- manual review metadata can be saved,
- approved export copies only approved generated outputs,
- `_APPROVED_INDEX.txt` is safe,
- no source values or private dictionary aliases appear in reports,
  summaries, or indexes,
- generated and local-only files remain ignored.
