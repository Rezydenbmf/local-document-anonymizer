# DocShield benchmark: measurable test system

A synthetic corpus with answer keys, plus a headless scorer that runs the
real anonymization pipeline and grades the output. Everything in the
corpus is invented (1800s PESELs, the 600 000 xxx phone block, `.test`
e-mails, fictional towns, random checksum-valid NIP/REGON/IBAN).

**Generated files are never committed.** `benchmark/corpus/` and
`benchmark/results/` are gitignored (user decision, 2026-09-25: the repo
is public, the files look like real PII, and they are reproducible from
the fixed seed). Only code, `policy.json` and `baseline.json` are
committed. `baseline.json` holds ids and counts, never document text,
and a unit test enforces that.

## Commands

```
.venv\Scripts\python.exe -m benchmark.generate                 # corpus -> benchmark/corpus/
.venv\Scripts\python.exe -m benchmark.score                    # full run, AI on (gemma3:4b)
.venv\Scripts\python.exe -m benchmark.score --bez-ai           # regex + NER only (~15 s)
.venv\Scripts\python.exe -m benchmark.score --check            # exit 1 on regression vs baseline
.venv\Scripts\python.exe -m benchmark.score --update-baseline  # accept the current result
.venv\Scripts\python.exe -m benchmark.score --only 02_faktura_vat_tabela --bez-ai
```

The AI review is on by default because the tests exist to measure it
(user decision). Budget minutes per document on the CPU-only laptop.

## Files

| file | role |
|---|---|
| `synth.py` | checksum-valid PESEL (1800s), NIP, REGON, IBAN, ID card |
| `layout.py` | `TextDoc` (fitz.Story text layer, table rows / columns) and `ScanDoc` (Pillow image, good/bad quality); both record a box for every character of every key span |
| `corpus.py` | the 13 documents: 3 traps (identical to the former `llm_test_*`) + 10 ordinary |
| `policy.json` | `policy_tag` -> `must` / `optional` / `keep` |
| `keys.py` | key schema, policy lookup, generator fingerprint |
| `generate.py` | writes `<doc>.pdf`, `<doc>.key.json`, `<doc>_WZORZEC.pdf` |
| `scoring.py` | coverage, leaks, over-redaction, LLM suggestion grading, baseline diff |
| `score.py` | runs the pipeline (app defaults: NER on, all categories, visual output) |

## Answer key (`<doc>.key.json`)

```json
{"schema": "docshield-answer-key/1", "doc_id": "...", "file": "...pdf",
 "form": "text|scan_good|scan_bad", "kind": "trap|ordinary", "pages": 2,
 "seed": 20260925, "generator": "<fingerprint>",
 "spans": [{"id": "s07", "text": "Stani-sławem", "category": "PERSON", "page": 1,
            "policy_tag": "person_private", "expect": "must", "hint_layer": "ner",
            "note": "...", "chars": [[x0, y0, x1, y1], ...]}]}
```

`expect` is informational. The scorer always re-reads it from
`policy.json` via `policy_tag`, so a policy change re-scores without
regenerating anything. `hint_layer` is the layer that *should* catch the
span (`regex`, `ner`, `llm`, `none`). `chars` holds one box per
non-blank character, in PDF points.

## How a document is graded

* **Leak.** On a text-layer PDF, a key character leaks when it is still
  in the output's text layer (that is what renders and what can be
  copied). On a scan it leaks when no redaction fill covers its centre.
  A span is `covered`, `partial_leak` or `full_leak`.
* **Residue.** Text still extractable *under* a fill.
* **keep_redacted.** Something that must stay visible was hidden.
* **Over-redaction.** Fill rectangles touching no key span, with the
  original words under them (text layer only).
* **Layer credit.** From the pipeline's `applied_rects` labels
  (`NER_*` = ner, else regex).
* **AI.** Every suggestion is classed as `hit` (points at a leaked must
  span), `already_redacted`, `optional_only`, `false_positive` (no key
  span there), `unresolved`, or `unnecessary_type` (asks to *un*-redact;
  `unnecessary_wrong` when that span is must). Suggestions repeating the
  same sentence set count as `duplicates`. Matching happens at sentence
  level (the model points at sentences, not words): a suggestion counts
  as a hit on every leaked must span in its sentence(s). "Caught only by
  AI" is therefore an upper bound, especially for narrative combinations
  that cite five sentences at once.
* **Time.** Total per document, plus both LLM passes separately.

## Regression gate

`--check` fails (exit 1) on any new leaked span, a partial leak turning
into a full one, a new keep_redacted or residue span, or more
over-redaction rectangles than the baseline. AI numbers are stored in
the baseline for information only, because the model is not
deterministic. The baseline carries the generator fingerprint. After a
corpus change, regenerate, then `--update-baseline`.
