"""Tests for Stage 26 manual "magic pen" PDF redaction overrides."""

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from manual_redaction import (
    EMPTY_MANUAL_EDITS,
    ManualEdits,
    ManualRect,
    apply_manual_redaction_count_to_report_text,
    apply_pending_overrides,
    compute_visible_redaction_rects,
    load_manual_edits,
    manual_edits_path,
    rect_info_key,
    regenerate_pdf_with_manual_overrides,
    save_manual_edits,
)
from pdf_redaction import manual_edit_span_key


def workspace_temp_dir():
    return tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "tests")


def write_fitz_text_pdf(path: Path, lines: list[str]) -> None:
    import pymupdf as fitz

    document = fitz.open()
    page = document.new_page()
    y = 72
    for line in lines:
        page.insert_text((72, y), line, fontsize=12)
        y += 18
    document.save(path)
    document.close()


class ManualEditsPathTests(unittest.TestCase):
    def test_manual_edits_path_is_named_after_visual_output(self) -> None:
        output_pdf = Path("C:/out/document_ANON_VISUAL.pdf")
        self.assertEqual(
            manual_edits_path(output_pdf).name,
            "document_ANON_VISUAL_MANUAL_EDITS.json",
        )


class ManualEditsPersistenceTests(unittest.TestCase):
    def test_load_missing_file_returns_empty_edits(self) -> None:
        with workspace_temp_dir() as temp_dir:
            missing = Path(temp_dir) / "does_not_exist_MANUAL_EDITS.json"
            self.assertEqual(load_manual_edits(missing), EMPTY_MANUAL_EDITS)

    def test_load_corrupt_file_returns_empty_edits(self) -> None:
        with workspace_temp_dir() as temp_dir:
            corrupt = Path(temp_dir) / "corrupt_MANUAL_EDITS.json"
            corrupt.write_text("{not valid json", encoding="utf-8")
            self.assertEqual(load_manual_edits(corrupt), EMPTY_MANUAL_EDITS)

    def test_save_and_load_round_trips_removed_and_added(self) -> None:
        with workspace_temp_dir() as temp_dir:
            path = Path(temp_dir) / "roundtrip_MANUAL_EDITS.json"
            edits = ManualEdits(
                removed=frozenset(
                    {(1, "EMAIL", 10.0, 20.0, 100.0, 30.0)}
                ),
                added=(ManualRect(page=2, x0=1.0, y0=2.0, x1=3.0, y1=4.0),),
            )

            save_manual_edits(path, edits)
            loaded = load_manual_edits(path)

            self.assertEqual(loaded, edits)

    def test_empty_edits_is_empty(self) -> None:
        self.assertTrue(EMPTY_MANUAL_EDITS.is_empty)
        non_empty = ManualEdits(added=(ManualRect(1, 0, 0, 1, 1),))
        self.assertFalse(non_empty.is_empty)


class RegeneratePdfWithManualOverridesTests(unittest.TestCase):
    def test_regenerate_without_edits_matches_normal_auto_redaction(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_text_pdf(
                source_path,
                ["Contact tester@example.test today.", "Header Alpha Beta Gamma"],
            )
            output_path = Path(temp_dir) / "source_ANON_VISUAL.pdf"

            result = regenerate_pdf_with_manual_overrides(
                source_path,
                output_path=output_path,
                edits=EMPTY_MANUAL_EDITS,
            )

            self.assertTrue(output_path.exists())
            self.assertTrue(result["applied_rects"])
            self.assertEqual(result["counters"].get("EMAIL"), 1)

    def test_regenerate_applies_removed_and_added_overrides(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_text_pdf(
                source_path,
                ["Contact tester@example.test today.", "Header Alpha Beta Gamma"],
            )
            output_path = Path(temp_dir) / "source_ANON_VISUAL.pdf"

            baseline = regenerate_pdf_with_manual_overrides(
                source_path,
                output_path=output_path,
                edits=EMPTY_MANUAL_EDITS,
            )
            email_rect = next(
                rect for rect in baseline["applied_rects"] if rect["label"] == "EMAIL"
            )

            import pymupdf as fitz

            removed_key = manual_edit_span_key(
                email_rect["page"],
                email_rect["label"],
                fitz.Rect(
                    email_rect["x0"], email_rect["y0"], email_rect["x1"], email_rect["y1"]
                ),
            )
            from pdf_redaction import extract_pdf_word_pages

            alpha_word = next(
                word
                for word in extract_pdf_word_pages(source_path)[0].words
                if word.text == "Alpha"
            )
            edits = ManualEdits(
                removed=frozenset({removed_key}),
                added=(
                    ManualRect(
                        page=1,
                        x0=alpha_word.rect.x0,
                        y0=alpha_word.rect.y0,
                        x1=alpha_word.rect.x1,
                        y1=alpha_word.rect.y1,
                    ),
                ),
            )

            result = regenerate_pdf_with_manual_overrides(
                source_path,
                output_path=output_path,
                edits=edits,
            )

            with fitz.open(output_path) as document:
                visible_text = "\n".join(page.get_text("text") for page in document)
            self.assertIn("tester@example.test", visible_text)
            self.assertNotIn("Alpha", visible_text)
            self.assertIn("Beta", visible_text)
            self.assertEqual(result["counters"].get("RECZNE"), 1)
            self.assertNotIn("EMAIL", result["counters"])


class ComputeVisibleRedactionRectsTests(unittest.TestCase):
    def test_visible_rects_combine_auto_minus_removed_with_added(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_text_pdf(
                source_path,
                ["Contact tester@example.test today.", "Header Alpha Beta Gamma"],
            )

            baseline = compute_visible_redaction_rects(
                source_path, edits=EMPTY_MANUAL_EDITS
            )
            email_rect = next(rect for rect in baseline if rect["label"] == "EMAIL")

            import pymupdf as fitz

            removed_key = manual_edit_span_key(
                email_rect["page"],
                email_rect["label"],
                fitz.Rect(
                    email_rect["x0"], email_rect["y0"], email_rect["x1"], email_rect["y1"]
                ),
            )
            edits = ManualEdits(
                removed=frozenset({removed_key}),
                added=(ManualRect(page=1, x0=1.0, y0=2.0, x1=50.0, y1=20.0),),
            )

            visible = compute_visible_redaction_rects(source_path, edits=edits)

            self.assertFalse(any(rect["label"] == "EMAIL" for rect in visible))
            self.assertTrue(
                any(
                    rect["label"] == "RECZNE" and rect["x0"] == 1.0
                    for rect in visible
                )
            )


class ApplyPendingOverridesTests(unittest.TestCase):
    AUTO_RECT = {"page": 1, "label": "EMAIL", "x0": 10.0, "y0": 20.0, "x1": 100.0, "y1": 30.0}

    def test_staging_removal_of_auto_rect_adds_it_to_removed(self) -> None:
        key = rect_info_key(self.AUTO_RECT)
        result = apply_pending_overrides(
            EMPTY_MANUAL_EDITS,
            visible_rects=[self.AUTO_RECT],
            pending_remove_keys={key},
            pending_add_rects=[],
        )
        self.assertIn(key, result.removed)
        self.assertEqual(result.added, ())

    def test_staging_removal_of_previously_added_manual_rect_drops_it(self) -> None:
        added_rect = ManualRect(page=1, x0=1.0, y0=2.0, x1=3.0, y1=4.0)
        edits = ManualEdits(added=(added_rect,))
        key = manual_edit_span_key(added_rect.page, "RECZNE", added_rect)

        result = apply_pending_overrides(
            edits,
            visible_rects=[],
            pending_remove_keys={key},
            pending_add_rects=[],
        )

        self.assertEqual(result.added, ())
        self.assertEqual(result.removed, frozenset())

    def test_pending_additions_are_appended(self) -> None:
        new_rect = ManualRect(page=2, x0=5.0, y0=6.0, x1=7.0, y1=8.0)
        result = apply_pending_overrides(
            EMPTY_MANUAL_EDITS,
            visible_rects=[],
            pending_remove_keys=set(),
            pending_add_rects=[new_rect],
        )
        self.assertEqual(result.added, (new_rect,))

    def test_unrelated_existing_edits_are_preserved(self) -> None:
        kept_rect = ManualRect(page=3, x0=1.0, y0=1.0, x1=2.0, y1=2.0)
        edits = ManualEdits(removed=frozenset({("prior", "key")}), added=(kept_rect,))
        result = apply_pending_overrides(
            edits, visible_rects=[], pending_remove_keys=set(), pending_add_rects=[]
        )
        self.assertEqual(result.removed, frozenset({("prior", "key")}))
        self.assertEqual(result.added, (kept_rect,))


class ApplyManualRedactionCountToReportTextTests(unittest.TestCase):
    def test_appends_a_distinct_note_without_touching_original_categories(self) -> None:
        report = (
            "Anonymization report\n\n"
            "Status: completed\n\n"
            "Detected categories:\n"
            "* EMAIL: 1\n\n"
            "Manual review required: yes\n"
        )

        result = apply_manual_redaction_count_to_report_text(report, 2)

        self.assertIn("Detected categories:\n* EMAIL: 1\n", result)
        self.assertIn("Manual review required: yes", result)
        self.assertIn("--- Magic pen (manual PDF edits) ---", result)
        self.assertIn("Manually hidden fragments currently in the PDF: 2", result)
        self.assertIn("--- end magic pen ---", result)

    def test_calling_again_with_a_new_count_replaces_the_note_in_place(self) -> None:
        report = "Anonymization report\n\nDetected categories:\n* EMAIL: 1\n"

        first = apply_manual_redaction_count_to_report_text(report, 1)
        second = apply_manual_redaction_count_to_report_text(first, 3)

        self.assertEqual(second.count("--- Magic pen (manual PDF edits) ---"), 1)
        self.assertIn("Manually hidden fragments currently in the PDF: 3", second)
        self.assertNotIn("currently in the PDF: 1", second)

    def test_zero_count_removes_a_previously_added_note(self) -> None:
        report = "Anonymization report\n\nDetected categories:\n* EMAIL: 1\n"
        with_note = apply_manual_redaction_count_to_report_text(report, 2)

        cleared = apply_manual_redaction_count_to_report_text(with_note, 0)

        self.assertNotIn("Magic pen", cleared)
        self.assertIn("Detected categories:\n* EMAIL: 1\n", cleared)

    def test_zero_count_on_a_report_without_a_note_is_unchanged(self) -> None:
        report = "Anonymization report\n\nDetected categories:\n* EMAIL: 1\n"
        self.assertEqual(apply_manual_redaction_count_to_report_text(report, 0), report)


if __name__ == "__main__":
    unittest.main()
