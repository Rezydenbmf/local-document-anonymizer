# Module: Local LLM Review Foundation

## Purpose

This module documents Stage 21: optional local Ollama-assisted review of
already-anonymized output text.

The goal is a safe local quality-control layer after anonymization, not a
primary anonymizer, document editor, chat interface, automatic approval system,
or replacement for deterministic rules, private dictionary matching, NER,
post-anonymization audit, or manual review.

## Related files

- `src/llm_review.py`
- `src/anonymizer.py`
- `src/report.py`
- `src/gui.py`
- `tests/test_llm_review.py`

## Runtime dependencies

The Python implementation uses standard library modules. Ollama itself is an
optional local system dependency installed outside the repository.

The user may verify local Ollama manually:

```bash
ollama --version
ollama list
```

The application does not run `ollama pull`, does not download models
automatically, and does not require a specific model name. A Polish-language
local model such as Bielik may be useful if the user has installed it manually.

## Public API

```python
detect_ollama_availability() -> OllamaAvailability
list_installed_models() -> tuple[str, list[str]]
validate_configured_model(model_name) -> dict[str, object]
parse_llm_review_response(response_text, model_name="") -> dict[str, object]
run_llm_review(anonymized_text, enabled=False, model_name=None) -> dict[str, object]
anonymize_file(..., use_llm_review=False, llm_model_name="")
anonymize_batch(..., use_llm_review=False, llm_model_name="")
```

Controlled status values:

- `disabled`
- `available`
- `unavailable`
- `ollama_not_found`
- `service_unavailable`
- `no_model_configured`
- `model_missing`
- `timeout`
- `invalid_response`
- `processing_error`
- `completed`

## Input policy

Normal file workflow order is:

```text
extract text
-> dictionary / regex / optional NER anonymization
-> save anonymized output
-> optional LLM review of anonymized output text only
-> audit
-> safe report / batch summary metadata
```

The LLM review function must not receive:

- raw source text,
- raw OCR text before anonymization,
- private dictionary terms,
- dictionary aliases,
- replacement maps,
- source snippets,
- full source paths.

For the LLM review layer, review prompts, raw responses, source text, and
snippets must not be written to reports, summaries, review metadata, approved
indexes, logs, or tracked docs. Stage 22 knowledge indexes are a separate
generated local artifact built only from approved anonymized TXT files and must
remain ignored by git.
On Windows, the local Ollama subprocess path must force UTF-8 text handling
instead of relying on the default console code page. Already-anonymized review
text is normalized before prompt construction so a leading UTF-8 BOM does not
reach subprocess stdin.

## Structured output

The local model is asked to return JSON only. The parser accepts only safe
structured fields:

- `risk_level` or `llm_risk_level`: `ok`, `warning`, `high_risk`, or
  `unknown`,
- `possible_residual_categories`: allowed category names only,
- `manual_review_required`: boolean.

Allowed residual categories:

- `PERSON_LIKE`
- `ORGANIZATION_LIKE`
- `LOCATION_LIKE`
- `ADDRESS_CONTEXT`
- `CASE_REFERENCE_LIKE`
- `CONTACT_DATA_LIKE`
- `OTHER_SENSITIVE_CONTEXT`

Invalid JSON, unexpected fields, unknown category names, or invalid types
become `invalid_response`. The raw response is not stored.

Stage 21.2 improves the request path by sending the review call through the
local Ollama generate API with `stream=false`, `temperature=0`, and a strict
JSON schema in the request `format`. This improves the chance of getting one
strict JSON object back without relaxing the parser.

Some local models can still wrap an otherwise valid JSON object in a markdown
code fence. The parser accepts only the safe narrow form where the entire model
response is a fenced JSON block, with or without a `json` fence label. The
fence is stripped in memory before strict parsing. Any prose or other content
outside the fence remains `invalid_response`. The raw fenced response is not
stored.

## Report and batch metadata

Per-file reports can include:

- LLM review used: yes/no,
- LLM review status,
- safe model name,
- LLM risk level,
- possible residual category names,
- LLM manual-review requirement,
- controlled warning text when needed.

Batch summaries can include:

- number of LLM review attempts,
- number that completed,
- number that attempted but failed safely,
- number skipped because LLM was disabled, unavailable, or not configured,
- aggregate LLM status counts,
- aggregate LLM risk level counts,
- aggregate LLM residual category counters,
- per-file LLM review status and risk level.

Counter semantics for Stage 21.2:

- `disabled`, `unavailable`, `ollama_not_found`, `service_unavailable`,
  `no_model_configured`, and `model_missing` count as skipped/unavailable.
- `timeout`, `invalid_response`, and `processing_error` count as attempted but
  failed safely.
- `completed` counts as completed.

Reports and summaries must not include raw prompts, raw LLM responses, source
text, raw OCR text, detected entity text, document snippets, dictionary terms,
dictionary aliases, full paths, tracebacks, or replacement maps.

## GUI behavior

The GUI adds minimal controls:

```text
Use local LLM review if available
LLM model dropdown
Refresh models
```

The model dropdown is populated from local `ollama list` output when available,
so models such as `gemma3:4b` are selectable when already installed. If Ollama
is unavailable or no models are found, the GUI shows:
`No local Ollama models found. Install/pull a model first.`

When enabled, batch anonymization passes `use_llm_review=True` and the selected
model name. If no model is configured, Ollama is unavailable, the model is
missing, the call times out, or the response is invalid, the workflow records a
safe status and continues. The GUI shows aggregate LLM status counts in the
existing status area. It does not add chat, preview, editing, highlighting, or
document rewriting.
Encoding and subprocess text-handling failures must also become controlled safe
statuses such as `processing_error` instead of surfacing prompt text, raw
response text, snippets, or traceback details.

## Safety assumptions

- LLM review is optional and local.
- LLM review is post-anonymization only.
- No OpenAI API, cloud LLM, external API, online processing, RAG, vector
  database, or network dependency is added.
- No model is downloaded or pulled automatically.
- Local model discovery is limited to installed Ollama models reported by
  `ollama list`.
- Model names are sanitized before reports.
- Local model output can be wrong or invalid.
- Manual review remains required for every generated output.

## How to test

Run:

```bash
python -m unittest discover -s tests
```

`tests/test_llm_review.py` mocks Ollama behavior and does not require real
Ollama or a real local model. It covers availability detection, missing command
behavior, service unavailable, no model configured, model missing, successful
mocked review, timeout handling, invalid response handling, strict structured
parsing, LLM risk mapping, residual category aggregation, safe report/batch
metadata, no-crash unavailable fallback, the anonymized-output-only input
policy, Windows-safe UTF-8 subprocess settings, BOM normalization, strict JSON
schema request construction, installed model list parsing, and
attempted-vs-skipped batch counter handling. `tests/test_gui_workflow.py`
covers the GUI model selector state helper.

## Known limitations

- LLM review quality depends on the local model.
- The model can miss or misclassify sensitive context.
- The model can return invalid output.
- Per-file LLM calls are sequential in the current batch workflow.
- No chat UI, document preview, editor, highlighting, document rewriting,
  automatic approval, RAG, vector database, cloud/API processing, or runtime
  model downloads are implemented.
