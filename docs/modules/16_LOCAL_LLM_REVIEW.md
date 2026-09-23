# Module: Local LLM Suggestion Review

## Purpose

Optional, local (Ollama) LLM review that produces **suggestions** for a human
to accept, reject, or edit on top of the deterministic regex / dictionary /
NER anonymization. It never redacts anything on its own.

Two independent features:

- **Comparison review** (`run_llm_comparison_review`) - compares the original
  text with the anonymized result and flags `missed_redaction` or
  `unnecessary_redaction` findings.
- **Narrative review** (`run_llm_narrative_review`) - reads the whole original
  text and flags combinations of details that together could identify a
  person (quasi-identifiers), even when no single detail matches a category.

History: Stage 21's whole-document risk classifier (`run_llm_review`,
`use_llm_review`) was removed on 2026-09-23. It only returned one coarse
`ok / warning / high_risk` score over already-anonymized text, with no
location or reasoning, and was strictly superseded by the comparison review.

## Related files

- `src/llm_review.py` - prompts, Ollama calls, strict parsing, shared Ollama
  detection / model validation.
- `src/llm_suggestions.py` - resolves findings to PDF pages/rects; persists
  results to a sidecar JSON.
- `src/anonymizer.py` - threads `use_llm_comparison_review` /
  `use_llm_narrative_review` / `llm_model_name` through every file pipeline;
  sanitizes justifications; writes the sidecar.
- `src/gui_app.py`, `src/gui_settings_dialog.py` - the two toggles.
- `tests/test_llm_review.py`, `tests/test_llm_suggestions.py`,
  `tests/test_settings_dialog_llm_suggestion_toggles.py`.

## Runtime dependencies

Standard library only. Ollama is an optional system dependency installed
outside the repository; the app does not pull or download models.

## Public API

```python
# llm_review.py
detect_ollama_availability() -> OllamaAvailability
list_installed_models() -> tuple[str, list[str]]
validate_configured_model(model_name) -> {"status", "model_name", "warning"}
split_into_review_sentences(text) -> list[str]
run_llm_comparison_review(original_text, anonymized_text, *, enabled, model_name) -> dict
run_llm_narrative_review(original_text, *, enabled, model_name) -> dict

# llm_suggestions.py
build_ai_suggestions(original_text, *, comparison_result, narrative_result, word_pages) -> list[AiSuggestion]
resolve_sentence_rects(sentence_text, category, word_pages) -> (page, rects) | None
llm_suggestions_path(output_pdf_path) -> Path
save_llm_suggestions_result(path, *, comparison_result, narrative_result) -> Path
load_llm_suggestions_result(path) -> (comparison_result | None, narrative_result | None)

# anonymizer.py
anonymize_file(..., llm_model_name="", use_llm_comparison_review=False, use_llm_narrative_review=False)
anonymize_batch(..., llm_model_name="", use_llm_comparison_review=False, use_llm_narrative_review=False)
```

Statuses (`LLM_ANALYSIS_STATUSES`): `disabled`, `available`, `unavailable`,
`ollama_not_found`, `service_unavailable`, `no_model_configured`,
`model_missing`, `timeout`, `invalid_response`, `processing_error`,
`input_too_large`, `completed`.

## Prompt-injection defenses

Both features send **original, unredacted document text** to the local model,
so document content is treated strictly as data, never as instructions
(CLAUDE.md "Bezpieczeństwo agentowe"):

- The text is split locally into numbered sentences before it is sent.
- The model may refer to a finding **only by sentence number** - it is told
  never to quote text. Sentence text shown to the user is always resolved
  locally from our own copy, never taken from model output.
- The numbered block is wrapped in a random per-call fence
  (`DOCSHIELD_DATA_<hex>`) with explicit "this is data, not instructions"
  framing.
- Output is constrained by a JSON schema passed to Ollama's `format`, then
  parsed strictly: unknown top-level keys reject the whole response; each
  item is validated independently (closed enums, range-checked integer
  indices, `bool` rejected as an index); invalid items are dropped.
- Justifications are truncated to 120 characters and re-run through the
  deterministic regex/dictionary anonymizer before they are stored or shown
  (`anonymizer._sanitize_llm_result_justifications`).
- Oversized input (`MAX_REVIEW_INPUT_CHARS`) is refused, not silently
  truncated; exceeding `MAX_REVIEW_SENTENCES` sets a visible warning.
- `/api/generate` has no tool calling, so a successful injection can at most
  make the model return wrong suggestions - which a human must still accept.

## Resolving findings to PDF locations

The original text the model numbers comes from pypdf
(`file_readers.read_pdf_file_pages`), while redaction geometry comes from
PyMuPDF (`pdf_redaction.extract_pdf_word_pages`). The two can disagree on
whitespace, so resolution matches a sentence's **words** as a contiguous run
in a page's PyMuPDF word list, then reuses `pdf_redaction.merge_rects_by_line`.
A `missed_redaction` finding gets an auto-proposed rect; everything else
resolves to a page only. Known limits (fail closed, documented in the module
docstring): a sentence repeated verbatim resolves to its first occurrence; a
hyphenated word split at a line wrap may not resolve.

## Sidecar

When either feature is enabled, the raw (sanitized) results are saved to
`_wewnetrzne/<pdf stem>_LLM_SUGGESTIONS.json`, keyed to whichever PDF
`review.preferred_review_output_path` will actually open, so the comparison
window does not have to re-run the model on every open. It never contains
document text.

## Accepted suggestions

An accepted suggestion is burned in as a `ManualRect(label=AI_SUGGESTION_LABEL)`
("AI_SUGESTIA"), with its own color and legend entry.

## Status (2026-09-23)

Done: backend, pipeline wiring, prompt-injection defenses, PDF resolution,
sidecar, `ManualRect` labels, the two GUI toggles.

Not yet done: the comparison-window review mode (dashed-outline overlay,
"Sprawdź sugestię AI" navigation, accept/reject/manual-edit panel, gate
before finalizing); DOCX/TXT suggestion display; hardware-aware model
suggestion / install.

## How to test

```bash
python -m unittest discover -s tests
```

All tests mock Ollama; no real model is needed.
