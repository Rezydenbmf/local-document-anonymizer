# Module: Local NER / NLP Foundation

## Purpose

This module documents Stage 20: optional local NER/NLP detection through
spaCy.

The goal is a safe local foundation for named-entity detection, not a complete
anonymization guarantee. NER can help detect people, organizations, locations,
and miscellaneous entities, but manual review remains required.

## Related files

- `src/ner.py`
- `src/anonymizer.py`
- `src/report.py`
- `src/gui.py`
- `tests/test_ner.py`

## Runtime dependencies

NER is optional. The Python package is listed in `requirements.txt`:

```text
spacy
```

A Polish spaCy model such as `pl_core_news_sm` is a separate local dependency:

```bash
python -m spacy download pl_core_news_sm
python -c "import spacy; spacy.load('pl_core_news_sm'); print('NER model available')"
```

The application does not run model download commands automatically. The
repository must not include spaCy model files.

## Public API

```python
detect_ner_support(enabled=True, model_name="pl_core_news_sm") -> dict[str, object]
prepare_ner_context(enabled=False, model_name="pl_core_news_sm") -> NerContext
detect_entities(text, context) -> tuple[list[NerEntity], dict[str, int]]
anonymize_text_with_ner(text, context) -> tuple[str, dict[str, int], dict[str, object]]
anonymize_text(text, sensitive_terms=None, use_ner=False, ner_model_name="pl_core_news_sm")
anonymize_file(..., use_ner=False, ner_model_name="pl_core_news_sm")
anonymize_batch(..., use_ner=False, ner_model_name="pl_core_news_sm")
```

NER status values are controlled metadata:

- `available`
- `unavailable`
- `dependency_missing`
- `model_missing`
- `disabled`
- `processing_error`

## Entity labels

Model-specific labels are mapped into internal labels:

- `NER_PERSON`
- `NER_ORG`
- `NER_LOCATION`
- `NER_MISC`

Reports, batch summaries, GUI status, and counters use only these internal
labels. They do not contain detected entity text.

## Behavior

When NER is enabled, the workflow order is:

1. Apply the optional private dictionary.
2. Apply deterministic regex replacements.
3. Apply local NER to the remaining text if spaCy and the local model are
   available.
4. Use a conservative PERSON left-expansion heuristic for simple
   adjacent-token cases where the local model returns only the trailing token.
5. Skip existing placeholders such as `[EMAIL]`, `[DATA]`, or private
   dictionary labels to avoid double replacement.
6. Save anonymized output, audit it, and write safe reports as before.

If spaCy is missing, the model is missing, NER is disabled, or NER processing
fails, the file workflow continues without NER replacements and records a safe
status. Missing NER support does not crash TXT, DOCX, PDF, OCR image, batch,
report, manual review, or approved export workflows.

## Report and batch metadata

Per-file reports can include:

- NER enabled: yes/no
- NER used: yes/no
- NER status
- NER model name
- NER counters by internal category

Batch summaries can include:

- files processed with NER
- files where NER was unavailable or disabled
- aggregate NER status counts
- aggregate NER category counters
- per-file NER status

Reports and summaries must not include detected entity text, source snippets,
raw OCR text, private dictionary terms, aliases, full paths, tracebacks, or
replacement maps.

## GUI behavior

The GUI adds one minimal checkbox:

```text
Use local NER if available
```

When checked, batch anonymization passes `use_ner=True`. The existing status
area shows aggregate NER used/unavailable counts after a run. The GUI does not
display detected entity text and does not add document preview, highlighting,
split-screen review, drag and drop, or editing.

## Safety assumptions

- NER is local and optional.
- NER does not use cloud services, API calls, OpenAI API, online processing,
  Ollama, Bielik, local LLMs, prompt-based review, databases, or network calls.
- NER models are installed by the user outside the repository.
- NER can miss entities or misclassify harmless text.
- NER counters are safe metadata only.
- Detected entity values are never written to reports, summaries, review
  metadata, approved indexes, or documentation.
- Manual review remains required for every generated output.

## Candidate export

Stage 20 does not implement `_DICTIONARY_CANDIDATES.txt` or any other NER
candidate export. A future stage may add a local-only, gitignored candidate
workflow, but candidate values must never enter safe reports, batch summaries,
review summaries, approved indexes, or tracked repository files.

## How to test

Run:

```bash
python -m unittest discover -s tests
```

`tests/test_ner.py` uses fake spaCy/model objects and synthetic files. It does
not require a real Polish spaCy model. It covers availability detection,
missing dependency behavior, missing model behavior, mapped entity labels,
PERSON/ORG/location anonymization, placeholder skipping, safe report metadata,
safe batch summary metadata, no-crash unavailable fallback, and DOCX workflow
integration.

## Known limitations

- NER quality depends on the installed local spaCy model.
- No spaCy model files are bundled.
- No model download runs automatically at runtime.
- NER is not fuzzy matching, inflection-proof detection, or a guarantee of
  complete anonymization.
- No candidate export is implemented in Stage 20.
- No preview, highlighting, split-screen review, drag and drop, editor,
  database, LLM, API, or cloud workflow is added.
