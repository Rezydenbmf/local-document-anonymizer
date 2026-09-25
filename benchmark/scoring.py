"""Scoring logic: compares DocShield's output PDF with an answer key.

Coverage is judged on the output file itself: a key character counts as
covered when its centre lies inside a filled redaction rectangle drawn
on the output page (apply_redactions draws the fills as vector paths, on
text pages and scans alike). On text-layer documents a covered character
that is still extractable from the output's text layer is reported
separately as *residue*.

No pipeline imports here - everything works on plain dicts and PyMuPDF
pages, so the unit tests can drive it with hand-made data.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

COVERED, PARTIAL, FULL = "covered", "partial_leak", "full_leak"
_TOL = 0.5


def _centre(box):
    return (box[0] + box[2]) / 2, (box[1] + box[3]) / 2


def point_in(point, rect, tol: float = _TOL) -> bool:
    x, y = point
    return rect[0] - tol <= x <= rect[2] + tol and rect[1] - tol <= y <= rect[3] + tol


def _is_whiteish(color) -> bool:
    return color is not None and all(c > 0.95 for c in color)


def fill_rects(page) -> list[tuple[float, float, float, float]]:
    rects = []
    for item in page.get_drawings():
        fill = item.get("fill")
        if fill is None or _is_whiteish(fill):
            continue
        r = item["rect"]
        rects.append((round(r.x0, 1), round(r.y0, 1), round(r.x1, 1), round(r.y1, 1)))
    return rects


def redaction_fills(source_page, output_page) -> list[tuple[float, float, float, float]]:
    """Filled rects present on the output page but not on the source."""
    before = Counter(fill_rects(source_page))
    fills = []
    for rect in fill_rects(output_page):
        if before[rect]:
            before[rect] -= 1
        else:
            fills.append(rect)
    return fills


def text_chars(page) -> list[tuple[str, tuple[float, float, float, float]]]:
    chars = []
    for block in page.get_text("rawdict").get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                for char in span.get("chars", []):
                    if char["c"].strip():
                        chars.append((char["c"], tuple(char["bbox"])))
    return chars


@dataclass
class SpanResult:
    id: str
    expect: str
    status: str
    leaked_chars: int
    total_chars: int
    residue_chars: int = 0
    layers: set[str] = field(default_factory=set)


def label_layer(label: str) -> str:
    if label.startswith("NER_"):
        return "ner"
    if label in ("RECZNE", "AI_SUGESTIA"):
        return "manual"
    return "regex"


def score_span(span: dict, fills, output_chars=None, applied_rects=()) -> SpanResult:
    """``output_chars`` given (text-layer document): a character leaks when
    it is still in the output's text layer - that is exactly what renders
    and what can be copied; one still there *under* a fill is also counted
    as residue. Without it (scan): a character leaks when no fill covers
    its centre. ``leaked_chars < total_chars`` therefore means "something
    of this span was hidden", which for a keep span is over-redaction."""
    chars = [tuple(box) for box in span["chars"]]
    glyphs = "".join(span["text"].split())
    covered = [any(point_in(_centre(box), r) for r in fills) for box in chars]
    if output_chars is not None:
        present = [
            any(c == glyph and point_in(_centre(b), box, 1.0) for c, b in output_chars)
            for glyph, box in zip(glyphs, chars)
        ]
        leaked = sum(present)
        residue = sum(c and p for c, p in zip(covered, present))
    else:
        leaked = covered.count(False)
        residue = 0
    if leaked == 0:
        status = COVERED
    elif leaked >= len(chars):
        status = FULL
    else:
        status = PARTIAL
    layers = {
        label_layer(str(rect["label"]))
        for rect in applied_rects
        if rect["page"] == span["page"]
        and any(point_in(_centre(box), (rect["x0"], rect["y0"], rect["x1"], rect["y1"]))
                for box in chars)
    }
    return SpanResult(span["id"], span["expect"], status, leaked, len(chars), residue, layers)


def over_redaction(key: dict, fills_by_page: dict[int, list], words_by_page=None) -> dict:
    """Fill rects that touch no key character at all, plus (text layer
    only) the original words under them. A rect over a keep span is
    already reported as keep_redacted, so it is not counted twice."""
    rects, words = [], []
    for page, fills in fills_by_page.items():
        centres = [_centre(b) for s in key["spans"] if s["page"] == page for b in s["chars"]]
        for rect in fills:
            if any(point_in(c, rect) for c in centres):
                continue
            rects.append({"page": page, "rect": list(rect)})
            if words_by_page and page in words_by_page:
                words.extend(
                    w[4] for w in words_by_page[page]
                    if point_in(_centre(w[:4]), rect)
                )
    return {"rects": rects, "words": words}


# -- LLM suggestions ---------------------------------------------------------

def _stripped(text: str) -> str:
    return "".join(text.split()).lower()


def classify_suggestions(suggestions, sentences, key: dict, span_results) -> dict:
    """``suggestions``: dicts with finding_type, source, page, rects,
    sentence_indices (llm_suggestions.AiSuggestion, asdict'ed).
    ``sentences``: the review sentences the model numbered."""
    status = {r.id: r.status for r in span_results}
    spans = {s["id"]: s for s in key["spans"]}
    out = {"total": len(suggestions), "hit": 0, "already_redacted": 0, "optional_only": 0,
           "false_positive": 0, "unresolved": 0, "unnecessary_type": 0,
           "unnecessary_wrong": 0, "duplicates": 0, "caught_span_ids": [], "items": []}
    seen_sentences: set[tuple] = set()
    caught: set[str] = set()
    for sug in suggestions:
        indices = tuple(sorted(sug.get("sentence_indices") or ()))
        duplicate = bool(indices) and indices in seen_sentences
        seen_sentences.add(indices)
        if duplicate:
            out["duplicates"] += 1
        targets = _suggestion_targets(sug, sentences, spans)
        if targets is not None:
            targets = [t for t in targets if spans[t]["expect"] != "keep"]
        if sug.get("finding_type") == "unnecessary_redaction":
            out["unnecessary_type"] += 1
            verdict = "unnecessary"
            if any(spans[t]["expect"] == "must" for t in targets or ()):
                out["unnecessary_wrong"] += 1
                verdict = "unnecessary_wrong"
        elif targets is None:
            out["unresolved"] += 1
            verdict = "unresolved"
        else:
            leaked_must = [t for t in targets
                           if spans[t]["expect"] == "must" and status.get(t) != COVERED]
            if leaked_must:
                out["hit"] += 1
                caught.update(leaked_must)
                verdict = "hit"
            elif any(spans[t]["expect"] == "must" for t in targets):
                out["already_redacted"] += 1
                verdict = "already_redacted"
            elif targets:
                out["optional_only"] += 1
                verdict = "optional_only"
            else:
                out["false_positive"] += 1
                verdict = "false_positive"
        out["items"].append({"id": sug.get("id"), "source": sug.get("source"),
                             "type": sug.get("finding_type"), "category": sug.get("category"),
                             "sentences": list(indices), "page": sug.get("page"),
                             "verdict": verdict, "targets": targets, "duplicate": duplicate})
    out["caught_span_ids"] = sorted(caught)
    return out


def _suggestion_targets(sug, sentences, spans) -> list[str] | None:
    """Key span ids a suggestion points at; None when it can't be tied to
    any place in the document."""
    rects = sug.get("rects") or ()
    if rects:
        return [
            sid for sid, s in spans.items()
            if any(r["page"] == s["page"]
                   and any(point_in(_centre(b), (r["x0"], r["y0"], r["x1"], r["y1"]))
                           for b in s["chars"])
                   for r in rects)
        ]
    texts = [sentences[i - 1] for i in sug.get("sentence_indices") or ()
             if isinstance(i, int) and 1 <= i <= len(sentences)]
    if not texts:
        return None
    joined = [_stripped(t) for t in texts]
    page = sug.get("page")
    return [
        sid for sid, s in spans.items()
        if (page is None or s["page"] == page)
        and any(_stripped(s["text"]) in t for t in joined)
    ]


# -- aggregation / baseline --------------------------------------------------

def summarize_doc(key: dict, span_results, over: dict) -> dict:
    must = [r for r in span_results if r.expect == "must"]
    keep = [r for r in span_results if r.expect == "keep"]
    layer_counts: Counter = Counter()
    for r in must:
        if r.status == COVERED:
            for layer in r.layers or {"?"}:
                layer_counts[layer] += 1
    return {
        "must": len(must),
        "covered": sum(r.status == COVERED for r in must),
        "partial": sorted(r.id for r in must if r.status == PARTIAL),
        "full": sorted(r.id for r in must if r.status == FULL),
        "keep_redacted": sorted(r.id for r in keep if r.leaked_chars < r.total_chars),
        "residue": sorted(r.id for r in span_results if r.residue_chars and r.expect != "keep"),
        "over_rects": len(over["rects"]),
        "layers": dict(sorted(layer_counts.items())),
    }


def compare_to_baseline(current: dict, baseline: dict) -> tuple[list[str], list[str]]:
    """Returns (regressions, improvements) as human-readable lines."""
    regressions, improvements = [], []
    for doc_id, now in current.items():
        before = baseline.get(doc_id)
        if before is None:
            improvements.append(f"{doc_id}: nowy dokument (brak w baseline)")
            continue
        was_leak = set(before["partial"]) | set(before["full"])
        for sid in sorted(set(now["partial"]) | set(now["full"])):
            if sid not in was_leak:
                regressions.append(f"{doc_id} {sid}: nowy wyciek")
            elif sid in now["full"] and sid in before["partial"]:
                regressions.append(f"{doc_id} {sid}: wyciek częściowy stał się pełny")
        for sid in sorted(was_leak - set(now["partial"]) - set(now["full"])):
            improvements.append(f"{doc_id} {sid}: już nie wycieka")
        for sid in sorted(set(now["keep_redacted"]) - set(before["keep_redacted"])):
            regressions.append(f"{doc_id} {sid}: zamazane coś, co ma zostać widoczne")
        for sid in sorted(set(now["residue"]) - set(before["residue"])):
            regressions.append(f"{doc_id} {sid}: tekst został w warstwie tekstowej")
        if now["over_rects"] > before["over_rects"]:
            regressions.append(f"{doc_id}: nadmiarowa redakcja {before['over_rects']} -> "
                               f"{now['over_rects']}")
        elif now["over_rects"] < before["over_rects"]:
            improvements.append(f"{doc_id}: nadmiarowa redakcja {before['over_rects']} -> "
                                f"{now['over_rects']}")
    return regressions, improvements
