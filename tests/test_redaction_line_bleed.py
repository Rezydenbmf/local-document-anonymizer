"""A redaction rect must not delete text of a tightly-set neighbouring line.

Regression for the live finding on llm_test_2_opinia_lekarska_2str.pdf:
lines set closer than their own glyph height made the date redaction on
one line silently remove "nie do wniosku" from the line below.
"""

import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pdf_redaction import (
    _apply_page_redactions,
    save_redacted_pdf_copy,
    trim_rect_to_covered_lines,
)

# Two lines of glyph boxes, 0..14 and 10..24: 4pt vertical overlap.
LINE_1 = [(0.0, 0.0, 5.0, 14.0), (5.0, 0.0, 10.0, 14.0)]
LINE_2 = [(0.0, 10.0, 5.0, 24.0), (5.0, 10.0, 10.0, 24.0)]


class TrimRectTests(unittest.TestCase):
    def test_grazed_line_below_is_trimmed_off(self):
        self.assertEqual(
            trim_rect_to_covered_lines((0.0, 0.0, 10.0, 14.0), LINE_1 + LINE_2),
            (0.0, 0.0, 10.0, 10.0),
        )

    def test_grazed_line_above_is_trimmed_off(self):
        self.assertEqual(
            trim_rect_to_covered_lines((0.0, 10.0, 10.0, 24.0), LINE_1 + LINE_2),
            (0.0, 14.0, 10.0, 24.0),
        )

    def test_rect_covering_both_line_centres_is_kept(self):
        rect = (0.0, 0.0, 10.0, 24.0)
        self.assertEqual(trim_rect_to_covered_lines(rect, LINE_1 + LINE_2), rect)

    def test_no_neighbour_means_no_change(self):
        rect = (0.0, 0.0, 10.0, 14.0)
        self.assertEqual(trim_rect_to_covered_lines(rect, LINE_1), rect)

    def test_nothing_covered_means_no_change(self):
        rect = (20.0, 0.0, 30.0, 14.0)
        self.assertEqual(trim_rect_to_covered_lines(rect, LINE_1 + LINE_2), rect)

    def test_fails_closed_when_trim_would_expose_own_glyph(self):
        # Neighbour starts 3pt below the own line's top: trimming there
        # would leave the own glyph overlapped by only 3/14 of its height.
        own = [(0.0, 0.0, 5.0, 14.0)]
        neighbour = [(0.0, 3.0, 5.0, 17.0)]
        rect = (0.0, 0.0, 5.0, 7.5)
        self.assertEqual(trim_rect_to_covered_lines(rect, own + neighbour), rect)

    def test_neighbour_outside_rect_horizontally_is_ignored(self):
        rect = (0.0, 0.0, 10.0, 14.0)
        far = [(50.0, 10.0, 55.0, 24.0)]
        self.assertEqual(trim_rect_to_covered_lines(rect, LINE_1 + far), rect)


def _write_tight_pdf(path: Path, lines: tuple[str, ...], *, leading: float) -> None:
    import pymupdf as fitz

    document = fitz.open()
    page = document.new_page()
    y = 72.0
    for line in lines:
        page.insert_text((72, y), line, fontsize=12)
        y += leading
    document.save(path)
    document.close()


class TightLinesPdfTests(unittest.TestCase):
    LINES = (
        "Sygnatura ABC123XYZ tutaj",
        "Zwykly tekst ponizej musi zostac caly",
        "Trzecia linia tez musi zostac cala",
    )

    def _redact(self, leading: float) -> str:
        import pymupdf as fitz

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "tight.pdf"
            _write_tight_pdf(source, self.LINES, leading=leading)
            with fitz.open(source) as document:
                words = document[0].get_text("words")
            line_1_bottom = max(w[3] for w in words if w[4] == "ABC123XYZ")
            line_2_top = min(w[1] for w in words if w[4] == "Zwykly")
            if leading < 14:
                # Guard: the fixture really overlaps, or the test proves nothing.
                self.assertGreater(line_1_bottom, line_2_top)
            output = Path(temp_dir) / "out.pdf"
            save_redacted_pdf_copy(
                source,
                extra_redaction_terms=[("MANUAL", "ABC123XYZ")],
                output_path=output,
            )
            with fitz.open(output) as document:
                return document[0].get_text("text")

    def test_tight_lines_keep_neighbour_text(self):
        text = self._redact(leading=11.0)
        self.assertNotIn("ABC123XYZ", text)
        self.assertIn(self.LINES[1], text)
        self.assertIn(self.LINES[2], text)

    def test_normal_spacing_unchanged(self):
        text = self._redact(leading=18.0)
        self.assertNotIn("ABC123XYZ", text)
        self.assertIn(self.LINES[1], text)

    def test_middle_line_redaction_keeps_both_neighbours(self):
        import pymupdf as fitz

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "tight.pdf"
            _write_tight_pdf(source, self.LINES, leading=11.0)
            output = Path(temp_dir) / "out.pdf"
            save_redacted_pdf_copy(
                source,
                extra_redaction_terms=[("MANUAL", "ponizej")],
                output_path=output,
            )
            with fitz.open(output) as document:
                text = document[0].get_text("text")
        self.assertNotIn("ponizej", text)
        self.assertIn(self.LINES[0], text)
        self.assertIn(self.LINES[2], text)

    def test_safety_net_reapplies_untrimmed_rect_when_trim_misses(self):
        import pymupdf as fitz

        import pdf_redaction

        def trim_to_useless_sliver(rect, _boxes):
            # Simulates a trim that no longer touches the glyphs at all.
            return (rect[0], rect[1], rect[2], rect[1] + 0.1)

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "tight.pdf"
            _write_tight_pdf(source, self.LINES, leading=11.0)
            with fitz.open(source) as document:
                page = document[0]
                rect = page.search_for("ABC123XYZ")[0]
                page.add_redact_annot(rect)
                with unittest.mock.patch.object(
                    pdf_redaction,
                    "trim_rect_to_covered_lines",
                    trim_to_useless_sliver,
                ):
                    _apply_page_redactions(fitz, page)
                text = page.get_text("text")
        self.assertNotIn("ABC123XYZ", text)

    def test_manual_rect_across_two_lines_still_removes_both(self):
        import pymupdf as fitz

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "tight.pdf"
            _write_tight_pdf(source, self.LINES, leading=11.0)
            with fitz.open(source) as document:
                page = document[0]
                words = page.get_text("words")
                top = min(w[1] for w in words if w[4] == "Sygnatura")
                bottom = max(w[3] for w in words if w[4] == "Zwykly")
                page.add_redact_annot(fitz.Rect(72, top, 140, bottom))
                _apply_page_redactions(fitz, page)
                text = page.get_text("text")
        self.assertNotIn("Sygnatura", text)
        self.assertNotIn("Zwykly", text)


if __name__ == "__main__":
    unittest.main()
