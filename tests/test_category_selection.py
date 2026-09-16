"""Tests for Etap 4: letting the user pick, per task, which of 8
user-facing categories actually get redacted - everything else
(DOWOD_OSOBISTY, PERSON_NAME_TYPO, NER_ORG, NER_LOCATION, NER_MISC, the
dictionary, RECZNE) stays always-on regardless of selection. See
docs/PROJECT_STATE.md's Etap 4 narrative for the full design.
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from anonymizer import (
    ALWAYS_ON_LABELS,
    CATEGORY_ADDRESS,
    CATEGORY_COMPANY,
    CATEGORY_EMAIL,
    CATEGORY_GROUPS,
    CATEGORY_PESEL,
    SUPPORTED_LABELS,
    _apply_dictionary_and_regex,
    _excluded_labels_for_audit,
    _pdf_detection_spans_for_word_pages,
    anonymize_batch,
    resolve_active_labels,
)
from audit import audit_text
from ner import NerContext, anonymize_text_with_ner


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


class ResolveActiveLabelsTests(unittest.TestCase):
    def test_none_means_no_filtering(self) -> None:
        self.assertIsNone(resolve_active_labels(None))

    def test_selecting_a_category_includes_its_labels(self) -> None:
        active = resolve_active_labels([CATEGORY_EMAIL])
        self.assertIn("EMAIL", active)

    def test_address_category_covers_all_three_address_labels(self) -> None:
        active = resolve_active_labels([CATEGORY_ADDRESS])
        self.assertIn("ULICA", active)
        self.assertIn("MIEJSCOWOSC", active)
        self.assertIn("POSTAL_CODE", active)

    def test_company_category_covers_nip_and_regon(self) -> None:
        active = resolve_active_labels([CATEGORY_COMPANY])
        self.assertIn("NIP", active)
        self.assertIn("REGON", active)

    def test_unselected_category_label_is_excluded(self) -> None:
        active = resolve_active_labels([CATEGORY_EMAIL])
        self.assertNotIn("TELEFON", active)
        self.assertNotIn("PESEL", active)

    def test_always_on_labels_are_included_even_with_empty_selection(self) -> None:
        active = resolve_active_labels([])
        for label in ALWAYS_ON_LABELS:
            self.assertIn(label, active)

    def test_always_on_labels_cover_the_expected_gaps(self) -> None:
        # Regression guard for the exact gap list the user confirmed
        # (2026-09-16): anything not covered by one of the 8 named
        # categories must never become togglable by accident.
        self.assertEqual(
            ALWAYS_ON_LABELS,
            frozenset(
                {"DOWOD_OSOBISTY", "PERSON_NAME_TYPO", "NER_ORG", "NER_LOCATION", "NER_MISC"}
            ),
        )

    def test_every_supported_label_is_reachable(self) -> None:
        # Every real regex label must be either in a category group or in
        # ALWAYS_ON_LABELS - never silently unreachable from either.
        covered = ALWAYS_ON_LABELS | frozenset(
            label for labels in CATEGORY_GROUPS.values() for label in labels
        )
        for label in SUPPORTED_LABELS:
            self.assertIn(label, covered)

    def test_unknown_category_id_is_ignored_not_an_error(self) -> None:
        active = resolve_active_labels(["not_a_real_category"])
        self.assertEqual(active, ALWAYS_ON_LABELS)


class ApplyDictionaryAndRegexFilteringTests(unittest.TestCase):
    def test_active_labels_none_redacts_everything(self) -> None:
        text = "Kontakt: test@example.com, PESEL 00000000000."
        anonymized, _counters, _ = _apply_dictionary_and_regex(text)
        self.assertIn("[EMAIL]", anonymized)
        self.assertIn("[PESEL]", anonymized)

    def test_excluded_label_is_left_untouched_in_the_text(self) -> None:
        text = "Kontakt: test@example.com, PESEL 00000000000."
        active = resolve_active_labels([CATEGORY_PESEL])  # email not selected

        anonymized, counters, _ = _apply_dictionary_and_regex(
            text, active_labels=active
        )

        self.assertIn("test@example.com", anonymized)
        self.assertNotIn("[EMAIL]", anonymized)
        self.assertIn("[PESEL]", anonymized)
        self.assertNotIn("EMAIL", counters)

    def test_excluding_phone_category_also_skips_weak_grouped_phone_pass(self) -> None:
        text = "Zadzwon pod numer 500 100 200 w sprawie zamowienia."
        active_without_phone = resolve_active_labels([CATEGORY_EMAIL])

        anonymized, counters, _ = _apply_dictionary_and_regex(
            text, active_labels=active_without_phone
        )

        self.assertNotIn("[TELEFON]", anonymized)
        self.assertNotIn("TELEFON", counters)


class AnonymizeTextWithNerFilteringTests(unittest.TestCase):
    def test_allowed_labels_none_redacts_every_entity(self) -> None:
        context = NerContext(enabled=True, status="available", model_name="x")
        with patch("ner.detect_entities_with_details") as mock_detect:
            from ner import NerEntity

            mock_detect.return_value = (
                [NerEntity(start=0, end=10, label="NER_PERSON")],
                {"NER_PERSON": 1},
                {},
                0,
            )
            anonymized, counters, _ = anonymize_text_with_ner(
                "Jan Kowalski przyszedl.", context
            )
        self.assertIn("[NER_PERSON]", anonymized)
        self.assertEqual(counters.get("NER_PERSON"), 1)

    def test_excluded_ner_label_is_left_in_text_but_still_counted(self) -> None:
        context = NerContext(enabled=True, status="available", model_name="x")
        with patch("ner.detect_entities_with_details") as mock_detect:
            from ner import NerEntity

            mock_detect.return_value = (
                [NerEntity(start=0, end=12, label="NER_PERSON")],
                {"NER_PERSON": 1},
                {},
                0,
            )
            anonymized, counters, _ = anonymize_text_with_ner(
                "Jan Kowalski przyszedl.",
                context,
                allowed_labels=frozenset({"NER_ORG"}),  # NER_PERSON excluded
            )
        self.assertEqual(anonymized, "Jan Kowalski przyszedl.")
        # Still reported as detected, even though not redacted - matches
        # this app's existing "detected vs redacted" reporting split.
        self.assertEqual(counters.get("NER_PERSON"), 1)


class AuditTextExclusionTests(unittest.TestCase):
    def test_excluded_label_never_flagged_as_a_finding(self) -> None:
        text = "Kontakt: test@example.com pozostal w tekscie."
        result = audit_text(text, excluded_labels=frozenset({"EMAIL"}))
        self.assertEqual(result["findings"]["EMAIL"], 0)
        self.assertEqual(result["status"], "ok")

    def test_unexcluded_label_is_still_flagged(self) -> None:
        text = "Kontakt: test@example.com pozostal w tekscie."
        result = audit_text(text, excluded_labels=frozenset({"PESEL"}))
        self.assertGreater(result["findings"]["EMAIL"], 0)
        self.assertEqual(result["status"], "warning")

    def test_none_excluded_labels_behaves_like_before(self) -> None:
        text = "Kontakt: test@example.com pozostal w tekscie."
        result = audit_text(text)
        self.assertGreater(result["findings"]["EMAIL"], 0)


class ExcludedLabelsForAuditTests(unittest.TestCase):
    def test_none_active_labels_means_none_excluded(self) -> None:
        self.assertIsNone(_excluded_labels_for_audit(None))

    def test_excludes_exactly_the_complement(self) -> None:
        active = resolve_active_labels([CATEGORY_EMAIL])
        excluded = _excluded_labels_for_audit(active)
        self.assertIn("PESEL", excluded)
        self.assertNotIn("EMAIL", excluded)


class EndToEndTxtCategorySelectionTests(unittest.TestCase):
    def test_batch_with_only_pesel_selected_leaves_email_visible(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            output_dir = Path(temp_dir) / "output"
            source_dir.mkdir()
            output_dir.mkdir()
            source_path = source_dir / "document.txt"
            source_path.write_text(
                "PESEL: 00000000000. Kontakt: test@example.com.",
                encoding="utf-8",
            )

            anonymize_batch(
                [source_path],
                output_dir,
                active_categories=[CATEGORY_PESEL],
            )

            anonymized_text = (output_dir / "document_ANON.txt").read_text(
                encoding="utf-8"
            )
        self.assertIn("[PESEL]", anonymized_text)
        self.assertIn("test@example.com", anonymized_text)
        self.assertNotIn("[EMAIL]", anonymized_text)

    def test_batch_with_no_active_categories_argument_redacts_everything(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            output_dir = Path(temp_dir) / "output"
            source_dir.mkdir()
            output_dir.mkdir()
            source_path = source_dir / "document.txt"
            source_path.write_text(
                "PESEL: 00000000000. Kontakt: test@example.com.",
                encoding="utf-8",
            )

            anonymize_batch([source_path], output_dir)

            anonymized_text = (output_dir / "document_ANON.txt").read_text(
                encoding="utf-8"
            )
        self.assertIn("[PESEL]", anonymized_text)
        self.assertIn("[EMAIL]", anonymized_text)

    def test_dowod_osobisty_stays_redacted_even_though_not_in_the_8_categories(
        self,
    ) -> None:
        with workspace_temp_dir() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            output_dir = Path(temp_dir) / "output"
            source_dir.mkdir()
            output_dir.mkdir()
            source_path = source_dir / "document.txt"
            source_path.write_text("Dowod osobisty: ABC123456.", encoding="utf-8")

            anonymize_batch(
                [source_path],
                output_dir,
                active_categories=[CATEGORY_EMAIL],  # nothing related selected
            )

            anonymized_text = (output_dir / "document_ANON.txt").read_text(
                encoding="utf-8"
            )
        self.assertIn("[DOWOD_OSOBISTY]", anonymized_text)


class PdfSpanFilteringTests(unittest.TestCase):
    def test_excluded_label_produces_no_pdf_span(self) -> None:
        from pdf_redaction import extract_pdf_word_pages

        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_text_pdf(
                source_path, ["Contact tester@example.test about PESEL 00000000000."]
            )
            word_pages = extract_pdf_word_pages(source_path)

            active = resolve_active_labels([CATEGORY_PESEL])  # email excluded
            spans = _pdf_detection_spans_for_word_pages(
                word_pages,
                sensitive_terms=None,
                ner_context=None,
                active_labels=active,
            )

            labels = {span.label for span in spans}
        self.assertIn("PESEL", labels)
        self.assertNotIn("EMAIL", labels)

    def test_none_active_labels_produces_every_span_as_before(self) -> None:
        from pdf_redaction import extract_pdf_word_pages

        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_text_pdf(
                source_path, ["Contact tester@example.test about PESEL 00000000000."]
            )
            word_pages = extract_pdf_word_pages(source_path)

            spans = _pdf_detection_spans_for_word_pages(
                word_pages, sensitive_terms=None, ner_context=None
            )

            labels = {span.label for span in spans}
        self.assertIn("PESEL", labels)
        self.assertIn("EMAIL", labels)


class EndToEndPdfCategorySelectionTests(unittest.TestCase):
    def test_visual_pdf_redacts_only_the_selected_category(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            output_dir = Path(temp_dir) / "output"
            source_dir.mkdir()
            output_dir.mkdir()
            source_path = source_dir / "document.pdf"
            write_fitz_text_pdf(
                source_path, ["Contact tester@example.test about PESEL 00000000000."]
            )

            anonymize_batch(
                [source_path],
                output_dir,
                active_categories=[CATEGORY_PESEL],
            )

            import pymupdf as fitz

            visual_pdf = output_dir / "document_ANON_VISUAL.pdf"
            self.assertTrue(visual_pdf.exists())
            with fitz.open(visual_pdf) as document:
                visible_text = "\n".join(page.get_text("text") for page in document)
        self.assertNotIn("00000000000", visible_text)
        self.assertIn("tester@example.test", visible_text)


if __name__ == "__main__":
    unittest.main()
