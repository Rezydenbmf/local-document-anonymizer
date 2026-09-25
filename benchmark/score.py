"""Headless scorer: runs DocShield's real PDF pipeline on every corpus
document and grades the output against the answer key.

Run (AI review on by default - the tests are meant to measure it):
    .venv\\Scripts\\python.exe -m benchmark.score
    .venv\\Scripts\\python.exe -m benchmark.score --bez-ai        # fast, regex+NER only
    .venv\\Scripts\\python.exe -m benchmark.score --check         # exit 1 on regression
    .venv\\Scripts\\python.exe -m benchmark.score --update-baseline

Settings match the app's defaults: NER on, every category on, visual
output. The full report (with span texts) goes to benchmark/results/
(gitignored); only benchmark/baseline.json (ids and counts, no document
text) is committed.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import pymupdf as fitz

try:
    from . import keys, scoring
    from .generate import DEFAULT_OUT, KEY_SUFFIX
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import keys
    import scoring
    from generate import DEFAULT_OUT, KEY_SUFFIX

SRC_DIR = keys.BENCHMARK_DIR.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import anonymizer
from llm_review import (
    LLM_STATUS_AVAILABLE,
    normalize_review_text,
    split_into_review_sentences,
    validate_configured_model,
)
from llm_suggestions import build_ai_suggestions

BASELINE_PATH = keys.BENCHMARK_DIR / "baseline.json"
RESULTS_DIR = keys.BENCHMARK_DIR / "results"
BASELINE_SCHEMA = "docshield-benchmark-baseline/1"
DEFAULT_MODEL = "gemma3:4b"


class _Timer:
    """Wraps the two optional LLM passes to time them separately."""

    def __init__(self) -> None:
        self.seconds: dict[str, float] = {}

    def wrap(self, name: str, func):
        def timed(*args, **kwargs):
            started = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                self.seconds[name] = round(time.perf_counter() - started, 1)
        return timed


def run_pipeline(pdf_path: Path, out_dir: Path, model: str | None):
    timer = _Timer()
    originals = (anonymizer._run_optional_llm_comparison_review,
                 anonymizer._run_optional_llm_narrative_review)
    anonymizer._run_optional_llm_comparison_review = timer.wrap("llm_comparison", originals[0])
    anonymizer._run_optional_llm_narrative_review = timer.wrap("llm_narrative", originals[1])
    started = time.perf_counter()
    try:
        result = anonymizer._anonymize_pdf_file_result(
            pdf_path,
            output_dir=out_dir,
            use_ner=True,
            llm_model_name=model or "",
            use_llm_comparison_review=bool(model),
            use_llm_narrative_review=bool(model),
            active_categories=anonymizer.ALL_CATEGORIES,
        )
    finally:
        (anonymizer._run_optional_llm_comparison_review,
         anonymizer._run_optional_llm_narrative_review) = originals
    timer.seconds["total"] = round(time.perf_counter() - started, 1)
    return result, timer.seconds


def score_document(key: dict, pdf_path: Path, out_dir: Path, result, policy: dict) -> dict:
    for span in key["spans"]:
        span["expect"] = keys.resolve_expect(span["policy_tag"], policy)
    meta = result.pdf_redaction_result or {}
    visual_name = meta.get("visual_pdf_name")
    if not visual_name:
        raise RuntimeError(f"{key['doc_id']}: no visual PDF produced ({meta.get('status')})")
    visual_path = out_dir / visual_name
    applied_rects = meta.get("applied_rects") or []
    text_layer = key["form"] == "text"
    span_results, fills_by_page, words_by_page = [], {}, {}
    with fitz.open(pdf_path) as source, fitz.open(visual_path) as output:
        for number in range(1, key["pages"] + 1):
            fills_by_page[number] = scoring.redaction_fills(source[number - 1], output[number - 1])
            if text_layer:
                words_by_page[number] = source[number - 1].get_text("words")
        out_chars = {
            n: scoring.text_chars(output[n - 1]) for n in range(1, key["pages"] + 1)
        } if text_layer else {}
    for span in key["spans"]:
        span_results.append(scoring.score_span(
            span,
            fills_by_page[span["page"]],
            out_chars.get(span["page"]) if text_layer else None,
            applied_rects,
        ))
    over = scoring.over_redaction(key, fills_by_page, words_by_page)
    summary = scoring.summarize_doc(key, span_results, over)
    return {"summary": summary, "spans": span_results, "over": over,
            "visual_pdf": str(visual_path)}


def score_llm(key: dict, pdf_path: Path, result, span_results) -> dict | None:
    comparison, narrative = result.llm_comparison_result, result.llm_narrative_result
    if comparison is None and narrative is None:
        return None
    word_pages = anonymizer.word_pages_for_redaction_geometry(pdf_path)
    candidates = anonymizer.candidate_llm_review_texts(pdf_path, word_pages)
    text = candidates[0] if candidates else ""
    suggestions = build_ai_suggestions(
        text, comparison_result=comparison, narrative_result=narrative, word_pages=word_pages
    )
    sentences = split_into_review_sentences(normalize_review_text(text))
    graded = scoring.classify_suggestions(
        [asdict(s) for s in suggestions], sentences, key, span_results
    )
    graded["status"] = {
        "comparison": (comparison or {}).get("status"),
        "narrative": (narrative or {}).get("status"),
    }
    return graded


def _span_line(key: dict, result) -> str:
    span = next(s for s in key["spans"] if s["id"] == result.id)
    return (f"    {key['doc_id']} {span['id']} str.{span['page']} {span['category']:<9} "
            f"{span['text']!r} [{result.status}, {result.leaked_chars}/{result.total_chars} "
            f"znaków; oczekiwana warstwa: {span['hint_layer']}]"
            + (f" – {span['note']}" if span["note"] else ""))


def print_report(rows, keys_by_id, llm_on: bool) -> None:
    head = (f"{'dokument':<34}{'forma':<10}{'must':>5}{'ok':>5}{'częśc':>6}{'pełny':>6}"
            f"{'keep!':>6}{'nadm':>5}{'czas':>7}")
    if llm_on:
        head += f"{'AI':>4}{'traf':>5}{'zamaz':>6}{'fałsz':>6}{'dupl':>5}{'AI s':>7}"
    print(head)
    totals = dict.fromkeys(("must", "ok", "p", "f", "k", "o"), 0)
    total_time = 0.0
    for row in rows:
        s = row["summary"]
        line = (f"{row['doc_id']:<34}{row['form']:<10}{s['must']:>5}{s['covered']:>5}"
                f"{len(s['partial']):>6}{len(s['full']):>6}{len(s['keep_redacted']):>6}"
                f"{s['over_rects']:>5}{row['seconds']['total']:>6.0f}s")
        if llm_on:
            g = row.get("llm") or {}
            llm_s = row["seconds"].get("llm_comparison", 0) + row["seconds"].get("llm_narrative", 0)
            line += (f"{g.get('total', 0):>4}{g.get('hit', 0):>5}{g.get('already_redacted', 0):>6}"
                     f"{g.get('false_positive', 0):>6}{g.get('duplicates', 0):>5}{llm_s:>6.0f}s")
        print(line)
        for k, v in (("must", s["must"]), ("ok", s["covered"]), ("p", len(s["partial"])),
                     ("f", len(s["full"])), ("k", len(s["keep_redacted"])), ("o", s["over_rects"])):
            totals[k] += v
        total_time += row["seconds"]["total"]
    print(f"{'RAZEM':<44}{totals['must']:>5}{totals['ok']:>5}{totals['p']:>6}{totals['f']:>6}"
          f"{totals['k']:>6}{totals['o']:>5}{total_time:>6.0f}s")
    if totals["must"]:
        print(f"Skuteczność (dane 'must' w pełni zakryte): "
              f"{100 * totals['ok'] / totals['must']:.1f}%")

    layer_totals: dict[str, int] = {}
    for row in rows:
        for layer, count in row["summary"]["layers"].items():
            layer_totals[layer] = layer_totals.get(layer, 0) + count
    llm_caught = sum(len((row.get("llm") or {}).get("caught_span_ids", [])) for row in rows)
    print("Zasługa warstw (zakryte 'must'): "
          + ", ".join(f"{k} {v}" for k, v in sorted(layer_totals.items()))
          + (f", tylko-AI (sugestia trafiła w wyciek) {llm_caught}" if llm_on else ""))

    print("\nWycieki danych 'must':")
    for row in rows:
        key = keys_by_id[row["doc_id"]]
        for result in row["spans"]:
            if result.expect == "must" and result.status != scoring.COVERED:
                print(_span_line(key, result))
    print("\nZamazane, choć miały zostać widoczne (keep):")
    for row in rows:
        key = keys_by_id[row["doc_id"]]
        for sid in row["summary"]["keep_redacted"]:
            result = next(r for r in row["spans"] if r.id == sid)
            print(_span_line(key, result))
    print("\nNadmiarowa redakcja (zamazania poza danymi z klucza):")
    for row in rows:
        over = row["over"]
        if over["rects"]:
            words = ", ".join(over["words"]) if over["words"] else "(skan – brak warstwy tekstu)"
            print(f"    {row['doc_id']}: {len(over['rects'])} prostokąt(y): {words}")


def _baseline_payload(rows, llm_on: bool, model: str | None, policy: dict) -> dict:
    return {
        "schema": BASELINE_SCHEMA,
        "created": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M"),
        "generator": keys.generator_fingerprint(),
        "policy_version": policy["policy_version"],
        "docs": {row["doc_id"]: row["summary"] for row in rows},
        # Informational only - the model is not deterministic, so AI
        # numbers are recorded but never gate a change.
        "llm_info": {
            "model": model if llm_on else None,
            "docs": {
                row["doc_id"]: {k: v for k, v in (row.get("llm") or {}).items()
                                if k not in ("items",)}
                for row in rows if row.get("llm")
            },
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--only", nargs="*", help="doc_id(s) to score")
    parser.add_argument("--bez-ai", action="store_true", help="skip the local-LLM review")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model for the AI review")
    parser.add_argument("--check", action="store_true",
                        help="compare with baseline.json; exit 1 on regression")
    parser.add_argument("--update-baseline", action="store_true")
    args = parser.parse_args(argv)
    # The Windows console is cp1250; never crash the report on a glyph.
    sys.stdout.reconfigure(errors="replace")

    policy = keys.load_policy()
    key_paths = sorted(args.corpus.glob("*" + KEY_SUFFIX))
    if not key_paths:
        print("Brak korpusu. Najpierw: .venv\\Scripts\\python.exe -m benchmark.generate")
        return 2
    fingerprint = keys.generator_fingerprint()
    model = None if args.bez_ai else args.model
    if model:
        validation = validate_configured_model(model)
        if validation["status"] != LLM_STATUS_AVAILABLE:
            print(f"Model AI {model!r} niedostępny (status: {validation['status']}). "
                  f"Uruchom Ollamę albo użyj --bez-ai.")
            return 2

    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    run_dir = RESULTS_DIR / stamp
    rows, keys_by_id = [], {}
    for key_path in key_paths:
        key = keys.load_key(key_path)
        if args.only and key["doc_id"] not in args.only:
            continue
        if key["generator"] != fingerprint:
            print(f"UWAGA: {key['doc_id']} wygenerowany starszą wersją generatora – "
                  f"uruchom benchmark.generate.")
            return 2
        keys.validate_key(key, policy)
        keys_by_id[key["doc_id"]] = key
        pdf_path = args.corpus / key["file"]
        print(f"... {key['doc_id']}", flush=True)
        out_dir = run_dir / "out" / key["doc_id"]
        result, seconds = run_pipeline(pdf_path, out_dir, model)
        scored = score_document(key, pdf_path, out_dir, result, policy)
        llm = score_llm(key, pdf_path, result, scored["spans"]) if model else None
        rows.append({"doc_id": key["doc_id"], "form": key["form"], "seconds": seconds,
                     "llm": llm, **scored})
    print()
    print_report(rows, keys_by_id, bool(model))

    run_dir.mkdir(parents=True, exist_ok=True)
    full = {
        "run": stamp, "model": model, "policy_version": policy["policy_version"],
        "docs": [
            {"doc_id": row["doc_id"], "form": row["form"], "seconds": row["seconds"],
             "summary": row["summary"], "over": row["over"], "llm": row["llm"],
             "visual_pdf": row["visual_pdf"],
             "spans": [dict(asdict(r), layers=sorted(r.layers)) for r in row["spans"]]}
            for row in rows
        ],
    }
    (run_dir / "report.json").write_text(json.dumps(full, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
    print(f"\nPełny raport: {run_dir / 'report.json'}")

    payload = _baseline_payload(rows, bool(model), model, policy)
    exit_code = 0
    if args.check or not args.update_baseline:
        if BASELINE_PATH.exists():
            baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
            if baseline.get("generator") != fingerprint:
                print("Baseline z innej wersji korpusu – porównanie pominięte "
                      "(zaktualizuj: --update-baseline).")
            else:
                regressions, improvements = scoring.compare_to_baseline(
                    payload["docs"], baseline["docs"])
                print("\nPorównanie z baseline:")
                for line in regressions:
                    print(f"  REGRESJA  {line}")
                for line in improvements:
                    print(f"  poprawa   {line}")
                if not regressions and not improvements:
                    print("  bez zmian")
                if regressions and args.check:
                    exit_code = 1
                elif improvements and not regressions:
                    print("  -> wynik lepszy; zapisz go: --update-baseline")
        elif args.check:
            print("Brak baseline.json – najpierw --update-baseline.")
            exit_code = 2
    if args.update_baseline:
        if args.only:
            print("--update-baseline wymaga pełnego przebiegu (bez --only).")
            return 2
        BASELINE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                                 encoding="utf-8")
        print(f"Zapisano {BASELINE_PATH}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
