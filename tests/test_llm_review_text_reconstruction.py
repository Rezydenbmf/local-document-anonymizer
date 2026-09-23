"""The comparison window must renumber sentences exactly the way the local
LLM saw them - the model only ever returns sentence NUMBERS (see
llm_review.py), so a text that differs by one sentence boundary would put
every proposed rect on the wrong sentence. The sidecar deliberately never
stores the document text, only its fingerprint, so the window rebuilds the
text itself (anonymizer.candidate_llm_review_texts) and proves the match
(llm_suggestions.select_review_text).

Each test runs the real anonymization pipeline with the LLM calls mocked
to capture the exact ``original_text`` they received, then rebuilds that
text the way the comparison window does - from the source file plus the
same word_pages its detection cache holds - and checks the fingerprint
and the sentence numbering both match.
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from anonymizer import (
    _anonymize_image_file_result,
    _anonymize_pdf_file_result,
    candidate_llm_review_texts,
    word_pages_for_redaction_geometry,
)
from llm_review import normalize_review_text, split_into_review_sentences
from llm_suggestions import (
    llm_suggestions_path,
    load_llm_suggestions_sidecar,
    review_text_fingerprint,
    select_review_text,
)
from ocr import OcrWordPageExtraction, build_ocr_metadata, detect_ocr_support
from review import preferred_review_output_path


def workspace_temp_dir():
    return tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "tests")


def _fake_ocr_page(page_number: int, lines: list[str]) -> dict[str, object]:
    words = []
    for line_no, line in enumerate(lines):
        x = 72.0
        y = 72.0 + line_no * 18
        for word_no, text in enumerate(line.split()):
            width = 6.0 * len(text)
            words.append(
                {
                    "text": text,
                    "rect": (x, y, x + width, y + 12),
                    "block_no": 0,
                    "line_no": line_no,
                    "word_no": word_no,
                }
            )
            x += width + 4
    return {"page_number": page_number, "words": words}


class _CapturingLlm:
    """Stands in for run_llm_comparison_review/run_llm_narrative_review,
    recording the original text each one was given."""

    def __init__(self) -> None:
        self.comparison_texts: list[str] = []
        self.narrative_texts: list[str] = []

    def comparison(self, original_text, _anonymized_text, *, enabled, model_name):
        self.comparison_texts.append(original_text)
        return {"status": "completed", "findings": []}

    def narrative(self, original_text, *, enabled, model_name):
        self.narrative_texts.append(original_text)
        return {"status": "completed", "suggestions": []}


def _write_text_pdf(path: Path, pages: list[list[str]]) -> None:
    import pymupdf as fitz

    document = fitz.open()
    for lines in pages:
        page = document.new_page()
        y = 72
        for line in lines:
            page.insert_text((72, y), line, fontsize=12)
            y += 18
    document.save(path)
    document.close()


def _write_blank_pdf(path: Path, page_count: int) -> None:
    import pymupdf as fitz

    document = fitz.open()
    for _ in range(page_count):
        document.new_page()
    document.save(path)
    document.close()


class ReviewTextReconstructionTests(unittest.TestCase):
    def _assert_window_rebuilds_the_reviewed_text(
        self, source_path: Path, sidecar_owner: Path, captured: _CapturingLlm
    ) -> None:
        self.assertEqual(len(captured.comparison_texts), 1)
        reviewed_text = captured.comparison_texts[0]
        # Both features number the same text.
        self.assertEqual(captured.narrative_texts, [reviewed_text])

        sidecar = load_llm_suggestions_sidecar(llm_suggestions_path(sidecar_owner))
        self.assertEqual(sidecar.original_text_sha256, review_text_fingerprint(reviewed_text))
        self.assertNotIn(
            "Kowalski",
            llm_suggestions_path(sidecar_owner).read_text(encoding="utf-8"),
            "the sidecar must hold a fingerprint, never document text",
        )

        word_pages = word_pages_for_redaction_geometry(source_path)
        rebuilt = select_review_text(
            candidate_llm_review_texts(source_path, word_pages),
            sidecar.original_text_sha256,
        )
        self.assertIsNotNone(rebuilt, "no reconstructed candidate matched the fingerprint")
        self.assertEqual(
            split_into_review_sentences(normalize_review_text(rebuilt)),
            split_into_review_sentences(normalize_review_text(reviewed_text)),
        )

    def test_text_layer_pdf(self) -> None:
        captured = _CapturingLlm()
        with workspace_temp_dir() as temp_dir:
            output_dir = Path(temp_dir)
            source_path = output_dir / "umowa.pdf"
            _write_text_pdf(
                source_path,
                [
                    ["Jan Kowalski mieszka w Warszawie.", "Ma 30 lat i trzy koty."],
                    ["Pracuje jako chirurg. Operuje w szpitalu."],
                ],
            )
            with patch("anonymizer.run_llm_comparison_review", captured.comparison), patch(
                "anonymizer.run_llm_narrative_review", captured.narrative
            ):
                result = _anonymize_pdf_file_result(
                    source_path,
                    output_dir=output_dir,
                    use_llm_comparison_review=True,
                    use_llm_narrative_review=True,
                    llm_model_name="local-model",
                )
            sidecar_owner = preferred_review_output_path(output_dir, result.output_path.name)

            self._assert_window_rebuilds_the_reviewed_text(source_path, sidecar_owner, captured)

    def test_scanned_pdf_uses_the_ocr_word_pages_text(self) -> None:
        captured = _CapturingLlm()
        fake_extraction = OcrWordPageExtraction(
            pages=[
                _fake_ocr_page(1, ["Jan Kowalski mieszka w Warszawie.", "Ma 30 lat."]),
                _fake_ocr_page(2, ["Pracuje jako chirurg.", "Operuje w szpitalu."]),
            ],
            metadata=build_ocr_metadata(
                used=True, status="available", input_type="pdf", items_processed=2
            ),
        )
        with workspace_temp_dir() as temp_dir:
            output_dir = Path(temp_dir)
            source_path = output_dir / "skan.pdf"
            _write_blank_pdf(source_path, 2)
            with patch("anonymizer.extract_pdf_word_boxes", return_value=fake_extraction), patch(
                "anonymizer.run_llm_comparison_review", captured.comparison
            ), patch("anonymizer.run_llm_narrative_review", captured.narrative):
                result = _anonymize_pdf_file_result(
                    source_path,
                    output_dir=output_dir,
                    use_llm_comparison_review=True,
                    use_llm_narrative_review=True,
                    llm_model_name="local-model",
                )
                sidecar_owner = preferred_review_output_path(
                    output_dir, result.output_path.name
                )
                self._assert_window_rebuilds_the_reviewed_text(
                    source_path, sidecar_owner, captured
                )
        # A blank scan has no pypdf text, so the OCR join is the only
        # candidate - proves the scan branch was actually exercised.
        self.assertIn("\f", captured.comparison_texts[0])

    def test_image_uses_its_single_ocr_page_text(self) -> None:
        from PIL import Image

        captured = _CapturingLlm()
        fake_extraction = OcrWordPageExtraction(
            pages=[_fake_ocr_page(1, ["Jan Kowalski mieszka w Warszawie.", "Ma 30 lat."])],
            metadata=build_ocr_metadata(
                used=True, status="available", input_type="image", items_processed=1
            ),
        )
        with workspace_temp_dir() as temp_dir:
            output_dir = Path(temp_dir)
            source_path = output_dir / "dowod.png"
            Image.new("RGB", (612, 792), "white").save(source_path)
            with patch(
                "anonymizer.extract_image_word_boxes", return_value=fake_extraction
            ), patch("anonymizer.run_llm_comparison_review", captured.comparison), patch(
                "anonymizer.run_llm_narrative_review", captured.narrative
            ):
                result = _anonymize_image_file_result(
                    source_path,
                    output_dir=output_dir,
                    use_llm_comparison_review=True,
                    use_llm_narrative_review=True,
                    llm_model_name="local-model",
                )
                visual_output = output_dir / result.pdf_redaction_result["output_name"]
                self._assert_window_rebuilds_the_reviewed_text(
                    source_path, visual_output, captured
                )

    @unittest.skipUnless(
        detect_ocr_support("pdf").get("status") == "available",
        "requires a real local Tesseract",
    )
    def test_scanned_pdf_with_real_ocr_is_reproducible(self) -> None:
        # The mocked test above proves the formula; this one proves real
        # OCR run twice (pipeline, then window) yields the same text.
        import pymupdf as fitz
        from PIL import Image, ImageDraw, ImageFont

        captured = _CapturingLlm()
        with workspace_temp_dir() as temp_dir:
            output_dir = Path(temp_dir)
            image_path = output_dir / "src.png"
            image = Image.new("RGB", (1700, 700), "white")
            draw = ImageDraw.Draw(image)
            try:
                font = ImageFont.truetype("arial.ttf", 40)
            except OSError:
                font = ImageFont.load_default()
            for index, line in enumerate(
                ["Jan Kowalski mieszka w Warszawie.", "Pracuje jako chirurg."]
            ):
                draw.text((80, 80 + index * 80), line, fill="black", font=font)
            image.save(image_path)
            source_path = output_dir / "skan.pdf"
            document = fitz.open()
            page = document.new_page(width=1700, height=700)
            page.insert_image(fitz.Rect(0, 0, 1700, 700), filename=str(image_path))
            document.save(source_path)
            document.close()

            with patch("anonymizer.run_llm_comparison_review", captured.comparison), patch(
                "anonymizer.run_llm_narrative_review", captured.narrative
            ):
                result = _anonymize_pdf_file_result(
                    source_path,
                    output_dir=output_dir,
                    use_llm_comparison_review=True,
                    use_llm_narrative_review=True,
                    llm_model_name="local-model",
                )
            sidecar_owner = preferred_review_output_path(output_dir, result.output_path.name)

            self._assert_window_rebuilds_the_reviewed_text(source_path, sidecar_owner, captured)

    def test_a_mismatching_text_fails_closed(self) -> None:
        fingerprint = review_text_fingerprint("Jan Kowalski. Ma 30 lat.")
        self.assertIsNone(select_review_text(["Jan Kowalski Ma 30 lat."], fingerprint))
        self.assertEqual(
            select_review_text(["inny tekst", "Jan Kowalski. Ma 30 lat."], fingerprint),
            "Jan Kowalski. Ma 30 lat.",
        )

    def test_legacy_sidecar_without_fingerprint_takes_the_first_non_empty_candidate(
        self,
    ) -> None:
        self.assertEqual(select_review_text(["  ", "pierwszy", "drugi"], None), "pierwszy")
        self.assertIsNone(select_review_text([], None))

    def test_fingerprint_ignores_a_leading_bom_like_the_review_does(self) -> None:
        self.assertEqual(
            review_text_fingerprint("﻿Jan Kowalski."),
            review_text_fingerprint("Jan Kowalski."),
        )


if __name__ == "__main__":
    unittest.main()
