"""Tests for true colored visual redaction on OCR'd (scanned PDF / plain
image) input - the positional counterpart to the existing text-layer PDF
visual redaction, added directly in response to a user report: a scanned
document came out as placeholder text ([NER_PERSON], [DATA], ...) instead
of the same colored-box style already used for real-text-layer PDFs.
"""

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from anonymizer import anonymize_image_file, anonymize_pdf_file_with_audit
from ocr import detect_ocr_support, extract_pdf_word_boxes, list_installed_languages
from pdf_redaction import PdfWordPage, word_pages_from_ocr_boxes


def workspace_temp_dir():
    return tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "tests")


def _ocr_available_with_polish() -> bool:
    """These tests need a real, working Tesseract with the Polish
    language pack to render meaningful assertions about redacted text -
    skip gracefully (not fail) on a machine without it, the same way the
    rest of this project treats OCR as a genuinely optional dependency.
    """
    status = detect_ocr_support("image")
    return status.get("status") == "available" and "pol" in list_installed_languages()


def _render_lines_to_image(path: Path, lines: list[str], size: tuple[int, int]) -> None:
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except OSError:
        font = ImageFont.load_default()
    y = 80
    for line in lines:
        draw.text((80, y), line, fill="black", font=font)
        y += 80
    image.save(path)


def _build_image_only_pdf(pdf_path: Path, source_image: Path, size: tuple[int, int]) -> None:
    """A PDF page that is nothing but a picture - no real text layer at
    all, forcing the OCR fallback path exactly like a real scan does."""
    import pymupdf as fitz

    document = fitz.open()
    page = document.new_page(width=size[0], height=size[1])
    page.insert_image(fitz.Rect(0, 0, size[0], size[1]), filename=str(source_image))
    document.save(pdf_path)
    document.close()


class WordPagesFromOcrBoxesTests(unittest.TestCase):
    """Pure data-shape conversion - no real OCR needed to test this part."""

    def test_builds_pdf_word_page_with_line_breaks_between_ocr_lines(self) -> None:
        ocr_pages = [
            {
                "page_number": 1,
                "words": [
                    {
                        "text": "Hello",
                        "rect": (0, 0, 10, 10),
                        "block_no": 0,
                        "line_no": 0,
                        "word_no": 0,
                    },
                    {
                        "text": "world",
                        "rect": (12, 0, 22, 10),
                        "block_no": 0,
                        "line_no": 0,
                        "word_no": 1,
                    },
                    {
                        "text": "Second",
                        "rect": (0, 15, 10, 25),
                        "block_no": 0,
                        "line_no": 1,
                        "word_no": 0,
                    },
                ],
            }
        ]

        pages = word_pages_from_ocr_boxes(ocr_pages)

        self.assertEqual(len(pages), 1)
        page = pages[0]
        self.assertIsInstance(page, PdfWordPage)
        self.assertEqual(page.page_number, 1)
        self.assertEqual(page.text, "Hello world\nSecond")
        self.assertEqual(len(page.words), 3)
        self.assertEqual(page.words[0].text, "Hello")
        self.assertEqual(page.words[0].start_offset, 0)
        self.assertEqual(page.words[0].end_offset, 5)
        self.assertEqual(page.words[2].start_offset, 12)

    def test_empty_pages_produce_no_words(self) -> None:
        pages = word_pages_from_ocr_boxes([{"page_number": 1, "words": []}])
        self.assertEqual(pages[0].text, "")
        self.assertEqual(pages[0].words, ())

    def test_multiple_pages_are_each_converted_independently(self) -> None:
        ocr_pages = [
            {
                "page_number": 1,
                "words": [
                    {
                        "text": "One",
                        "rect": (0, 0, 5, 5),
                        "block_no": 0,
                        "line_no": 0,
                        "word_no": 0,
                    }
                ],
            },
            {
                "page_number": 2,
                "words": [
                    {
                        "text": "Two",
                        "rect": (0, 0, 5, 5),
                        "block_no": 0,
                        "line_no": 0,
                        "word_no": 0,
                    }
                ],
            },
        ]
        pages = word_pages_from_ocr_boxes(ocr_pages)
        self.assertEqual([p.page_number for p in pages], [1, 2])
        self.assertEqual(pages[0].text, "One")
        self.assertEqual(pages[1].text, "Two")


@unittest.skipUnless(
    _ocr_available_with_polish(),
    "requires a real local Tesseract with the Polish language pack",
)
class ScannedPdfVisualRedactionIntegrationTests(unittest.TestCase):
    """Real, no-mocks verification through anonymizer.py's actual public
    API (what the GUI calls) - renders real text into an image-only PDF
    (no text layer, forcing OCR), anonymizes it for real, and confirms
    the resulting _ANON_VISUAL.pdf genuinely has the sensitive value
    removed (re-OCR'd, not just "some rectangle got drawn somewhere")
    while unrelated text stays legible.
    """

    def test_scanned_pdf_gets_a_true_colored_visual_redaction_pdf(self) -> None:
        with workspace_temp_dir() as temp_dir:
            temp_path = Path(temp_dir)
            source_image = temp_path / "src.png"
            size = (1700, 900)
            _render_lines_to_image(
                source_image,
                [
                    "UMOWA O PRACE",
                    "Pracownik: Piotr Zielinski",
                    "PESEL: 90020212345",
                ],
                size,
            )
            scanned_pdf = temp_path / "umowa.pdf"
            _build_image_only_pdf(scanned_pdf, source_image, size)

            output_path, counters, _audit = anonymize_pdf_file_with_audit(
                scanned_pdf, output_dir=temp_path, use_ner=False
            )

            self.assertTrue(output_path.exists())
            self.assertGreaterEqual(counters.get("PESEL", 0), 1)

            visual_pdf = temp_path / "umowa_ANON_VISUAL.pdf"
            self.assertTrue(
                visual_pdf.exists(),
                f"expected a true visual redaction PDF, found: "
                f"{sorted(p.name for p in temp_path.iterdir())}",
            )

            reextraction = extract_pdf_word_boxes(visual_pdf)
            reread_text = word_pages_from_ocr_boxes(reextraction.pages)[0].text
            self.assertNotIn(
                "90020212345",
                reread_text,
                "PESEL is still readable in the 'redacted' visual PDF",
            )
            self.assertTrue(
                "Zielinski" in reread_text or "zielinski" in reread_text.lower(),
                "unrelated text should remain legible - redaction must be "
                "targeted, not blanket",
            )


@unittest.skipUnless(
    _ocr_available_with_polish(),
    "requires a real local Tesseract with the Polish language pack",
)
class StandaloneImageVisualRedactionIntegrationTests(unittest.TestCase):
    """Same real, no-mocks verification for a plain image input (not a
    PDF) - the second half of the user's explicit request to support
    "PDF-y i obrazy naraz" (PDFs and images at once)."""

    def test_standalone_image_gets_a_true_colored_visual_redaction_pdf(self) -> None:
        with workspace_temp_dir() as temp_dir:
            temp_path = Path(temp_dir)
            image_path = temp_path / "dowod.png"
            _render_lines_to_image(
                image_path,
                [
                    "DOWOD OSOBISTY",
                    "Imie: Ewa Wisniewska",
                    "Numer: XYZ987654",
                ],
                (1400, 700),
            )

            output_path, counters = anonymize_image_file(image_path, output_dir=temp_path)

            self.assertTrue(output_path.exists())
            self.assertGreaterEqual(sum(counters.values()), 1)

            visual_pdf = temp_path / "dowod_ANON_VISUAL.pdf"
            self.assertTrue(
                visual_pdf.exists(),
                f"expected a true visual redaction PDF, found: "
                f"{sorted(p.name for p in temp_path.iterdir())}",
            )

            reextraction = extract_pdf_word_boxes(visual_pdf)
            reread_text = word_pages_from_ocr_boxes(reextraction.pages)[0].text
            self.assertNotIn("XYZ987654", reread_text)


if __name__ == "__main__":
    unittest.main()
