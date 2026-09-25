"""Generate the benchmark corpus: per document the PDF, a JSON answer key
and a reference PDF (``*_WZORZEC.pdf``) redacted from the key, for
comparing by eye with DocShield's output.

Run: .venv\\Scripts\\python.exe -m benchmark.generate [--out DIR] [--only ID ...]
Output goes to benchmark/corpus/ (gitignored - never committed: the repo
is public and the files are reproducible from the fixed seed).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pymupdf as fitz

try:
    from . import keys
    from .corpus import CORPUS, SEED, doc_rng
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import keys
    from corpus import CORPUS, SEED, doc_rng

DEFAULT_OUT = keys.BENCHMARK_DIR / "corpus"
REFERENCE_SUFFIX = "_WZORZEC.pdf"
KEY_SUFFIX = ".key.json"

STYLE = {
    "must": {"fill": (0, 0, 0), "color": None, "fill_opacity": 1.0},
    "optional": {"fill": (0.55, 0.55, 0.55), "color": None, "fill_opacity": 0.55},
    "keep": {"fill": None, "color": (0.1, 0.6, 0.2), "fill_opacity": 1.0},
}


def line_rects(chars) -> list[tuple[float, float, float, float]]:
    """Merge character boxes into one rect per visual line."""
    rects: list[list[float]] = []
    for x0, y0, x1, y1 in sorted(chars, key=lambda b: ((b[1] + b[3]) / 2, b[0])):
        centre = (y0 + y1) / 2
        for rect in rects:
            if rect[1] <= centre <= rect[3]:
                rect[0], rect[1] = min(rect[0], x0), min(rect[1], y0)
                rect[2], rect[3] = max(rect[2], x1), max(rect[3], y1)
                break
        else:
            rects.append([x0, y0, x1, y1])
    return [tuple(r) for r in rects]


def build_key(spec, placed, pages: int, policy: dict) -> dict:
    spans = []
    for number, item in enumerate(placed, start=1):
        spans.append({
            "id": f"s{number:02d}",
            "text": "".join(item.span.text.split("\n")),
            "category": item.span.category,
            "page": item.page,
            "policy_tag": item.span.tag,
            "expect": keys.resolve_expect(item.span.tag, policy),
            "hint_layer": item.span.hint,
            "note": item.span.note,
            "chars": [list(box) for box in item.chars],
        })
    return {
        "schema": keys.KEY_SCHEMA,
        "doc_id": spec.doc_id,
        "file": spec.doc_id + ".pdf",
        "form": spec.form,
        "kind": spec.kind,
        "description": spec.description,
        "pages": pages,
        "seed": SEED,
        "generator": keys.generator_fingerprint(),
        "policy_version_at_generation": policy["policy_version"],
        "spans": spans,
    }


def write_reference_pdf(source: Path, key: dict, destination: Path) -> None:
    with fitz.open(source) as doc:
        for span in key["spans"]:
            page = doc[span["page"] - 1]
            style = STYLE[span["expect"]]
            for rect in line_rects(span["chars"]):
                r = fitz.Rect(rect)
                if span["expect"] == "keep":
                    r = r + (-1, -1, 1, 1)
                page.draw_rect(r, color=style["color"], fill=style["fill"],
                               fill_opacity=style["fill_opacity"], width=1)
        for page in doc:
            page.insert_text(
                (20, page.rect.height - 12),
                "WZORZEC z klucza: czarne = musi byc zamazane, szare = obojetne, "
                "zielona ramka = ma zostac widoczne",
                fontsize=7, color=(0.8, 0, 0),
            )
        doc.save(destination, garbage=3, deflate=True)


def generate(out_dir: Path = DEFAULT_OUT, only: set[str] | None = None) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    policy = keys.load_policy()
    written = []
    for index, spec in enumerate(CORPUS):
        if only and spec.doc_id not in only:
            continue
        pdf_path = out_dir / (spec.doc_id + ".pdf")
        placed = spec.build(doc_rng(index)).save(pdf_path)
        with fitz.open(pdf_path) as doc:
            pages = doc.page_count
        key = build_key(spec, placed, pages, policy)
        keys.validate_key(key, policy)
        key_path = out_dir / (spec.doc_id + KEY_SUFFIX)
        key_path.write_text(json.dumps(key, ensure_ascii=False, indent=1), encoding="utf-8")
        write_reference_pdf(pdf_path, key, out_dir / (spec.doc_id + REFERENCE_SUFFIX))
        counts = {e: sum(1 for s in key["spans"] if s["expect"] == e) for e in keys.EXPECT_VALUES}
        print(f"OK  {spec.doc_id:<34} {spec.form:<9} {pages} str.  "
              f"must {counts['must']:>3}  optional {counts['optional']:>3}  keep {counts['keep']:>2}")
        written.append(pdf_path)
    return written


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--only", nargs="*", help="doc_id(s) to generate")
    args = parser.parse_args(argv)
    generate(args.out, set(args.only) if args.only else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
