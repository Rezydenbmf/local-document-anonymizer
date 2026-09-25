"""Renders synthetic documents and records where every answer-key span
ended up: one box per non-blank character, in PDF points.

A document is written as a sequence of *segments*: plain ``str`` or an
``S`` (a span the answer key knows about). Text-layer PDFs are laid out
with fitz.Story; scans are drawn with Pillow into a JPEG and placed on an
image-only PDF page.
"""

from __future__ import annotations

import html
import io
import math
import random
import re
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf as fitz
from PIL import Image, ImageDraw, ImageFilter, ImageFont

PAGE_W, PAGE_H = 595, 842  # A4 in points
MARGIN_X = 55
TEXT_W = PAGE_W - 2 * MARGIN_X
FONT = r"C:\Windows\Fonts\arial.ttf"
FONT_B = r"C:\Windows\Fonts\arialbd.ttf"
FONT_I = r"C:\Windows\Fonts\ariali.ttf"


@dataclass(frozen=True)
class S:
    """One answer-key span. ``text`` is written exactly as rendered; a
    "\\n" inside it is a forced line break (e.g. a name hyphenated across
    two lines)."""

    text: str
    category: str
    tag: str
    hint: str = "regex"
    note: str = ""


Segment = str | S


@dataclass
class PlacedSpan:
    span: S
    page: int  # 1-based
    chars: list[tuple[float, float, float, float]] = field(default_factory=list)


def _segments_text(segments: tuple[Segment, ...] | list[Segment]) -> str:
    return "".join(seg.text if isinstance(seg, S) else seg for seg in segments)


# --------------------------------------------------------------------------
# Text-layer PDFs
# --------------------------------------------------------------------------


class TextDoc:
    """Lays pages out with fitz.Story and MuPDF's built-in sans-serif font.

    Deliberately NOT page.insert_font(arial.ttf): Arial/Tahoma/Times map
    U+002D and U+00AD (and U+0020/U+00A0) to one glyph, and PyMuPDF's
    ToUnicode then extracts every "-" as a soft hyphen and every space as
    NBSP - an unintended trap that silently broke the e-mail and postal-code
    regexes in the first generated llm_test version.
    """

    MEASURE = fitz.Font("helv")
    CSS = "* {font-family: sans-serif;}"
    # Table cells without the default 12pt body margin; flowing text keeps
    # it, so the llm_test_* pages lay out exactly as first generated.
    ROW_CSS = CSS + " body {margin:0}"

    def __init__(self) -> None:
        self.pages: list[dict] = []
        self.spans: list[PlacedSpan] = []
        self.new_page()

    def new_page(self) -> None:
        self.pages.append({"regions": [], "bottom": None})

    # -- building ---------------------------------------------------------

    def _html(self, segments) -> str:
        parts = []
        for seg in segments:
            text = seg.text if isinstance(seg, S) else seg
            if isinstance(seg, S):
                self.spans.append(PlacedSpan(seg, len(self.pages)))
            parts.append("<br>".join(html.escape(p) for p in text.split("\n")))
        return "".join(parts)

    def _check_forced_breaks(self, segments, size: float) -> None:
        # The part before a forced "\n" must fit on one line, so a trailing
        # hyphen really ends up at the line's end.
        for line in _segments_text(segments).split("\n")[:-1]:
            if self.MEASURE.text_length(line, fontsize=size) > TEXT_W - 8:
                raise ValueError(f"Line must fit on one line: {line!r}")

    def para(self, *segments: Segment, size: float = 11, bold: bool = False,
             gap: float = 7, italic: bool = False) -> None:
        self._check_forced_breaks(segments, size)
        weight = "bold" if bold else "normal"
        style = "italic" if italic else "normal"
        self.pages[-1]["regions"].append((
            "flow",
            (f'<p style="font-size:{size}pt;font-weight:{weight};font-style:{style};'
             f'line-height:1.35;margin:0 0 {gap}pt 0">{self._html(segments)}</p>'),
        ))

    def tight_block(self, lines: list[list[Segment]], *, size: float = 10) -> None:
        """Lines deliberately closer than their own glyph height: word boxes
        of neighbouring lines overlap vertically by a few points."""
        for line in lines:
            if self.MEASURE.text_length(_segments_text(line), fontsize=size) > TEXT_W - 8:
                raise ValueError(f"Line must fit on one line: {_segments_text(line)!r}")
        body = "<br>".join(self._html(line) for line in lines)
        self.pages[-1]["regions"].append((
            "flow",
            f'<p style="font-size:{size}pt;line-height:0.95;margin:0 0 10pt 0">{body}</p>',
        ))

    def row(self, cells: list[list[Segment]], widths: list[float], *,
            size: float = 10, bold: bool = False, gap: float = 4) -> None:
        """Side-by-side cells (a table row or two text columns). ``widths``
        are fractions of the text width."""
        weight = "bold" if bold else "normal"
        rendered = [
            f'<p style="font-size:{size}pt;font-weight:{weight};line-height:1.3;'
            f'margin:0">{self._html(cell)}</p>'
            for cell in cells
        ]
        self.pages[-1]["regions"].append(("row", rendered, widths, gap))

    def at_bottom(self, *segments: Segment, size: float = 11) -> None:
        self.pages[-1]["bottom"] = (
            f'<p style="font-size:{size}pt;margin:0">{self._html(segments)}</p>'
        )

    # -- rendering --------------------------------------------------------

    def _place(self, device, html_text: str, rect, css: str = CSS) -> float:
        story = fitz.Story(html_text, user_css=css)
        more, filled = story.place(rect)
        if more:
            raise ValueError("Region overflow")
        story.draw(device)
        return filled[3]

    def save(self, path: Path) -> list[PlacedSpan]:
        buffer = io.BytesIO()
        writer = fitz.DocumentWriter(buffer)
        mediabox = fitz.Rect(0, 0, PAGE_W, PAGE_H)
        bottom_limit = PAGE_H - 70
        for page in self.pages:
            device = writer.begin_page(mediabox)
            y = 55.0
            for region in _merge_flows(page["regions"]):
                if region[0] == "flow":
                    y = self._place(device, region[1],
                                    fitz.Rect(MARGIN_X, y, PAGE_W - MARGIN_X, bottom_limit))
                    y += region[2]
                else:
                    _, rendered, widths, gap = region
                    # Same 12pt inset as the flowing text's body margin.
                    x = MARGIN_X + 12
                    lowest = y
                    for cell_html, share in zip(rendered, widths):
                        width = (TEXT_W - 24) * share
                        lowest = max(lowest, self._place(
                            device, cell_html, fitz.Rect(x, y, x + width - 6, bottom_limit),
                            self.ROW_CSS))
                        x += width
                    y = lowest + gap
            if page["bottom"]:
                self._place(device, page["bottom"],
                            fitz.Rect(MARGIN_X, PAGE_H - 62, PAGE_W - MARGIN_X, PAGE_H - 30))
            writer.end_page()
        writer.close()
        doc = fitz.open("pdf", buffer.getvalue())
        doc.set_metadata({"title": path.stem, "author": "", "creator": "DocShield benchmark"})
        doc.save(path, garbage=3, deflate=True)
        doc.close()
        with fitz.open(path) as rendered_doc:
            _locate_spans_in_text_layer(rendered_doc, self.spans)
        return self.spans


_MARGIN_RE = re.compile(r"margin:0 0 ([\d.]+)pt 0")


def _merge_flows(regions):
    """Consecutive paragraphs go into one Story, as one flowing column
    (the layout the llm_test_* files were first generated with). Yields
    ("flow", html, trailing_gap) or the row region unchanged."""
    buffer: list[str] = []
    for region in regions:
        if region[0] == "flow":
            buffer.append(region[1])
            continue
        if buffer:
            yield ("flow", "".join(buffer), _trailing_gap(buffer[-1]))
            buffer = []
        yield region
    if buffer:
        yield ("flow", "".join(buffer), _trailing_gap(buffer[-1]))


def _trailing_gap(html_text: str) -> float:
    match = _MARGIN_RE.search(html_text)
    return float(match.group(1)) if match else 0.0


def _page_char_stream(page) -> list[tuple[str, tuple[float, float, float, float]]]:
    chars = []
    for block in page.get_text("rawdict").get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                for char in span.get("chars", []):
                    if char["c"].strip():
                        chars.append((char["c"], tuple(round(v, 2) for v in char["bbox"])))
    return chars


def _locate_spans_in_text_layer(doc, spans: list[PlacedSpan]) -> None:
    by_page: dict[int, list[PlacedSpan]] = {}
    for placed in spans:
        by_page.setdefault(placed.page, []).append(placed)
    for page_number, page_spans in by_page.items():
        chars = _page_char_stream(doc[page_number - 1])
        stream = "".join(c for c, _ in chars)
        used: list[tuple[int, int]] = []
        cursor = 0
        for placed in page_spans:
            needle = "".join(placed.span.text.split())
            start = _find_free(stream, needle, cursor, used)
            if start is None:
                start = _find_free(stream, needle, 0, used)
            if start is None:
                raise ValueError(f"Span not found on page {page_number}: {placed.span.text!r}")
            end = start + len(needle)
            used.append((start, end))
            cursor = end
            placed.chars = [box for _, box in chars[start:end]]


def _find_free(stream: str, needle: str, begin: int, used) -> int | None:
    index = stream.find(needle, begin)
    while index != -1:
        end = index + len(needle)
        if all(end <= a or index >= b for a, b in used):
            return index
        index = stream.find(needle, index + 1)
    return None


# --------------------------------------------------------------------------
# Image-only scans
# --------------------------------------------------------------------------

SCAN_QUALITY = {
    # dpi, rotation (deg), blur radius, speckles per page, JPEG quality, paper
    "good": (300, 0.12, 0.35, 6000, 85, 250),
    "bad": (150, 0.9, 0.7, 9000, 55, 236),
}


class ScanDoc:
    """items per page: (style, segments) with style in
    {"title", "body", "italic", "gap"}."""

    def __init__(self, quality: str = "good", seed: int = 0) -> None:
        self.quality = quality
        self.seed = seed
        self.pages: list[list[tuple[str, list[Segment]]]] = [[]]

    def new_page(self) -> None:
        self.pages.append([])

    def add(self, style: str, *segments: Segment) -> None:
        self.pages[-1].append((style, list(segments)))

    def gap(self) -> None:
        self.pages[-1].append(("gap", []))

    def save(self, path: Path) -> list[PlacedSpan]:
        placed: list[PlacedSpan] = []
        doc = fitz.open()
        for index, items in enumerate(self.pages, start=1):
            jpeg, page_spans = self._render_page(items, index, self.seed + index)
            placed.extend(page_spans)
            page = doc.new_page(width=PAGE_W, height=PAGE_H)
            page.insert_image(page.rect, stream=jpeg)
        doc.set_metadata({"title": path.stem, "author": "", "creator": "DocShield benchmark"})
        doc.save(path, garbage=3, deflate=True)
        doc.close()
        return placed

    def _render_page(self, items, page_number: int, seed: int):
        dpi, angle, blur, speckles, jpeg_quality, paper = SCAN_QUALITY[self.quality]
        px = dpi / 72
        width, height = int(PAGE_W * px), int(PAGE_H * px)
        image = Image.new("L", (width, height), paper)
        draw = ImageDraw.Draw(image)
        fonts = {
            "title": ImageFont.truetype(FONT_B, int(13 * px)),
            "body": ImageFont.truetype(FONT, int(11 * px)),
            "italic": ImageFont.truetype(FONT_I, int(11 * px)),
        }
        x0 = int(MARGIN_X * px)
        max_w = int(TEXT_W * px)
        y = int(70 * px)
        span_boxes: dict[int, PlacedSpan] = {}
        for style, segments in items:
            if style == "gap":
                y += int(10 * px)
                continue
            font = fonts[style]
            # Flatten to (char, owner) where owner is the S instance or None.
            flat: list[tuple[str, S | None]] = []
            for seg in segments:
                owner = seg if isinstance(seg, S) else None
                text = seg.text if isinstance(seg, S) else seg
                flat.extend((ch, owner) for ch in text)
            for paragraph in _split_on(flat, "\n"):
                for line in _wrap(paragraph, draw, font, max_w):
                    line_text = "".join(ch for ch, _ in line)
                    draw.text((x0, y), line_text, font=font, fill=25)
                    for i, (ch, owner) in enumerate(line):
                        if owner is None or not ch.strip():
                            continue
                        left, top, right, bottom = font.getbbox(ch)
                        cx = x0 + draw.textlength(line_text[:i], font=font)
                        box = (cx + left, y + top, cx + right, y + bottom)
                        key = id(owner)
                        if key not in span_boxes:
                            span_boxes[key] = PlacedSpan(owner, page_number)
                        span_boxes[key].chars.append(box)
                    y += int(font.size * 1.6)
            y += int(5 * px)
        if y > height - int(40 * px):
            raise ValueError("Scan page overflow")
        rng = random.Random(seed)
        image = image.rotate(angle, resample=Image.BICUBIC, fillcolor=paper, expand=False)
        image = image.filter(ImageFilter.GaussianBlur(blur))
        pixels = image.load()
        for _ in range(speckles):
            pixels[rng.randrange(width), rng.randrange(height)] = rng.choice((90, 140, 190))
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=jpeg_quality, dpi=(dpi, dpi))

        ordered = sorted(span_boxes.values(), key=lambda p: _first_seen(items, p.span))
        for placed in ordered:
            placed.chars = [
                _rotate_box(box, angle, width / 2, height / 2, px) for box in placed.chars
            ]
        return buffer.getvalue(), ordered


def _first_seen(items, span: S) -> int:
    position = 0
    for _, segments in items:
        for seg in segments:
            if seg is span:
                return position
            position += 1
    return position


def _split_on(flat, separator: str):
    current: list = []
    for ch, owner in flat:
        if ch == separator:
            yield current
            current = []
        else:
            current.append((ch, owner))
    yield current


def _wrap(chars, draw, font, max_w):
    words: list[list] = [[]]
    for item in chars:
        if item[0] == " ":
            words.append([])
        else:
            words[-1].append(item)
    lines: list[list] = []
    current: list = []
    for word in words:
        trial = current + ([(" ", None)] if current else []) + word
        if current and draw.textlength("".join(c for c, _ in trial), font=font) > max_w:
            lines.append(current)
            current = list(word)
        else:
            current = trial
    lines.append(current)
    return lines


def _rotate_box(box, angle_deg: float, cx: float, cy: float, px: float):
    """PIL's rotate(angle) turns the image counter-clockwise (y axis down):
    (dx, dy) -> (dx cos + dy sin, -dx sin + dy cos)."""
    theta = math.radians(angle_deg)
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    xs, ys = [], []
    for x, y in ((box[0], box[1]), (box[2], box[1]), (box[0], box[3]), (box[2], box[3])):
        dx, dy = x - cx, y - cy
        xs.append(cx + dx * cos_t + dy * sin_t)
        ys.append(cy - dx * sin_t + dy * cos_t)
    return (round(min(xs) / px, 2), round(min(ys) / px, 2),
            round(max(xs) / px, 2), round(max(ys) / px, 2))
