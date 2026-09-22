"""Tests for Etap 4: letting the user pick, per task, which of 8
user-facing categories actually get redacted. "Adres" and "Dane firmy"
also cover the AI-detected NER_LOCATION/NER_ORG spans, not just their
regex counterparts (revised 2026-09-17 after live testing showed
deselecting everything but PESEL still left company names and address
fragments redacted - a checkbox promising "Adres" must mean no
address-shaped text survives, whichever detector found it). Everything
else (DOWOD_OSOBISTY, PERSON_NAME_TYPO, NER_MISC, the dictionary,
RECZNE) stays always-on regardless of selection. See
docs/PROJECT_STATE.md's Etap 4 narrative for the full design.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from anonymizer import (
    _PATTERNS,
    ALWAYS_ON_LABELS,
    CATEGORY_ADDRESS,
    CATEGORY_COMPANY,
    CATEGORY_EMAIL,
    CATEGORY_GROUPS,
    CATEGORY_PERSON,
    CATEGORY_PESEL,
    SUPPORTED_LABELS,
    _apply_dictionary_and_regex,
    _attach_pdf_coverage_metadata,
    _excluded_labels_for_audit,
    _pdf_detection_spans_for_word_pages,
    anonymize_batch,
    category_selection_path,
    compute_pdf_redaction_spans,
    load_active_pages_selection,
    load_category_selection,
    load_signature_stripping_selection,
    resolve_active_labels,
    resolve_active_pages,
    save_category_selection,
    update_signature_stripping_selection,
)
from audit import audit_text
from ner import NerContext, NerEntity, anonymize_text_with_ner
from pdf_redaction import PdfWordPage, pdf_page_count, save_redacted_pdf_copy


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


def write_fitz_multi_page_pdf(path: Path, pages: list[list[str]]) -> None:
    """Etap 5 page-range tests need more than one page - write_fitz_text_pdf
    only ever produces a single page."""
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


class ResolveActiveLabelsTests(unittest.TestCase):
    def test_none_means_no_filtering(self) -> None:
        self.assertIsNone(resolve_active_labels(None))

    def test_selecting_a_category_includes_its_labels(self) -> None:
        active = resolve_active_labels([CATEGORY_EMAIL])
        self.assertIn("EMAIL", active)

    def test_address_category_covers_regex_and_ai_detected_address_labels(
        self,
    ) -> None:
        active = resolve_active_labels([CATEGORY_ADDRESS])
        self.assertIn("ULICA", active)
        self.assertIn("MIEJSCOWOSC", active)
        self.assertIn("POSTAL_CODE", active)
        self.assertIn("NER_LOCATION", active)

    def test_company_category_covers_nip_regon_and_ai_detected_org_name(
        self,
    ) -> None:
        active = resolve_active_labels([CATEGORY_COMPANY])
        self.assertIn("NIP", active)
        self.assertIn("REGON", active)
        self.assertIn("NAZWA_FIRMY", active)
        self.assertIn("NER_ORG", active)

    def test_deselecting_address_excludes_the_ai_detected_location_too(
        self,
    ) -> None:
        active = resolve_active_labels([CATEGORY_PESEL])
        self.assertNotIn("NER_LOCATION", active)

    def test_deselecting_company_excludes_the_ai_detected_org_name_too(
        self,
    ) -> None:
        active = resolve_active_labels([CATEGORY_PESEL])
        self.assertNotIn("NER_ORG", active)

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
        # (2026-09-16, revised 2026-09-17: NER_ORG/NER_LOCATION moved into
        # CATEGORY_COMPANY/CATEGORY_ADDRESS - see the module docstring).
        # Anything not covered by one of the 8 named categories must
        # never become togglable by accident.
        self.assertEqual(
            ALWAYS_ON_LABELS,
            frozenset({"DOWOD_OSOBISTY", "PERSON_NAME_TYPO", "NER_MISC"}),
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


class ResolveActivePagesTests(unittest.TestCase):
    """Etap 5: restricting automatic PDF redaction to a chosen page
    range, the same "None means no filtering" contract
    resolve_active_labels already established for categories."""

    def test_none_means_no_filtering(self) -> None:
        self.assertIsNone(resolve_active_pages(None))

    def test_empty_or_whitespace_string_means_no_filtering(self) -> None:
        self.assertIsNone(resolve_active_pages(""))
        self.assertIsNone(resolve_active_pages("   "))

    def test_single_pages(self) -> None:
        self.assertEqual(resolve_active_pages("1,3,5"), frozenset({1, 3, 5}))

    def test_inclusive_range(self) -> None:
        self.assertEqual(resolve_active_pages("1-3"), frozenset({1, 2, 3}))

    def test_mixed_ranges_and_single_pages(self) -> None:
        self.assertEqual(resolve_active_pages("1-3,5"), frozenset({1, 2, 3, 5}))

    def test_tolerates_extra_whitespace(self) -> None:
        self.assertEqual(resolve_active_pages(" 1 - 3 , 5 "), frozenset({1, 2, 3, 5}))

    def test_non_numeric_token_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            resolve_active_pages("1-3,abc")

    def test_zero_or_negative_page_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            resolve_active_pages("0-3")

    def test_reversed_range_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            resolve_active_pages("5-3")

    def test_excessively_large_page_number_raises_value_error(self) -> None:
        """Regression test for a real gap code review caught: without an
        upper bound, a typo like "1-999999999" (meant to be "1-9") would
        build a set with hundreds of millions of entries synchronously
        on the GUI thread during start_anonymize's own validation call,
        before any processing/progress screen shows - freezing/risking
        an OOM instead of surfacing the same friendly error every other
        bad input gets."""
        with self.assertRaises(ValueError):
            resolve_active_pages("1-999999999")

    def test_page_number_exceeding_actual_page_count_is_harmless(self) -> None:
        """Without an explicit page_count, a range naming a page beyond
        the real document (e.g. "1-99" on a 2-page PDF) is not itself an
        error, it just never matches anything - most callers have no way
        to know a document's real page count at all."""
        self.assertEqual(resolve_active_pages("1-99"), frozenset(range(1, 100)))

    def test_page_count_none_skips_the_bounds_check(self) -> None:
        self.assertEqual(
            resolve_active_pages("1-99", page_count=None), frozenset(range(1, 100))
        )

    def test_page_count_accepts_a_range_within_bounds(self) -> None:
        self.assertEqual(
            resolve_active_pages("1-3", page_count=5), frozenset({1, 2, 3})
        )

    def test_page_count_rejects_a_page_beyond_the_real_document(self) -> None:
        """Per-file page-range redesign: once a document's real page
        count is known (see pdf_redaction.pdf_page_count), a range
        naming a page it doesn't have becomes a real error, unlike the
        no-page_count case above."""
        with self.assertRaises(ValueError) as ctx:
            resolve_active_pages("1-5", page_count=3)
        self.assertIn("5", str(ctx.exception))
        self.assertIn("3", str(ctx.exception))

    def test_page_count_error_uses_correct_polish_plural(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            resolve_active_pages("2", page_count=1)
        self.assertIn("stronę", str(ctx.exception))
        with self.assertRaises(ValueError) as ctx:
            resolve_active_pages("5", page_count=3)
        self.assertIn("strony", str(ctx.exception))
        with self.assertRaises(ValueError) as ctx:
            resolve_active_pages("10", page_count=5)
        self.assertIn("stron", str(ctx.exception))
        self.assertNotIn("strony", str(ctx.exception))


class PdfPageCountTests(unittest.TestCase):
    """Per-file page-range redesign: pdf_page_count is the cheap,
    synchronous-safe lookup the GUI calls the moment a PDF is added to
    the file list, so a page range can be validated against a specific
    document's real page count before the user ever runs anything."""

    def test_returns_the_real_page_count_of_a_multi_page_pdf(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.pdf"
            write_fitz_multi_page_pdf(source_path, [["a"], ["b"], ["c"]])

            self.assertEqual(pdf_page_count(source_path), 3)

    def test_returns_none_for_a_missing_file(self) -> None:
        self.assertIsNone(pdf_page_count("does_not_exist.pdf"))

    def test_returns_none_for_a_non_pdf_file_instead_of_raising(self) -> None:
        with workspace_temp_dir() as temp_dir:
            junk_path = Path(temp_dir) / "not_really_a.pdf"
            junk_path.write_bytes(b"this is not a pdf file at all")

            self.assertIsNone(pdf_page_count(junk_path))


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

    def test_excluded_ner_label_is_left_in_text_and_not_counted_as_handled(
        self,
    ) -> None:
        """Regression guard: an earlier version built the returned
        counters from the full (unfiltered) detection result, so a
        category the caller excluded still showed up as "anonymized" in
        the report even though nothing was substituted - a false
        reassurance that PII was handled when it was still fully in the
        clear. The report-facing counters must reflect only what was
        actually redacted.
        """
        context = NerContext(enabled=True, status="available", model_name="x")
        with patch("ner.detect_entities_with_details") as mock_detect:
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
        self.assertNotIn("NER_PERSON", counters)

    def test_selecting_only_pesel_leaves_an_ai_detected_company_name_visible(
        self,
    ) -> None:
        """Direct regression test for the exact scenario reported live:
        deselect every category but PESEL, and a company name detected
        by NER (not a regex label at all) must stay untouched - before
        CATEGORY_COMPANY grew NER_ORG (2026-09-17), this always redacted
        anyway, contradicting what the "Dane firmy" checkbox promises.
        """
        context = NerContext(enabled=True, status="available", model_name="x")
        with patch("ner.detect_entities_with_details") as mock_detect:
            mock_detect.return_value = (
                [NerEntity(start=0, end=13, label="NER_ORG")],
                {"NER_ORG": 1},
                {},
                0,
            )
            anonymized, counters, _ = anonymize_text_with_ner(
                "Firma Testowa Sp. z o.o.",
                context,
                allowed_labels=resolve_active_labels([CATEGORY_PESEL]),
            )
        self.assertEqual(anonymized, "Firma Testowa Sp. z o.o.")
        self.assertNotIn("NER_ORG", counters)


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

    def test_active_pages_skips_out_of_scope_pages_entirely(self) -> None:
        """Etap 5: a page outside active_pages must produce zero spans
        from every source (dictionary, regex, NER together) - the page
        is meant to stay completely untouched, not just have some
        categories suppressed on it."""
        from pdf_redaction import extract_pdf_word_pages

        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_multi_page_pdf(
                source_path,
                [
                    ["PESEL 00000000000 on page one."],
                    ["PESEL 11111111111 on page two."],
                ],
            )
            word_pages = extract_pdf_word_pages(source_path)

            spans = _pdf_detection_spans_for_word_pages(
                word_pages,
                sensitive_terms=None,
                ner_context=None,
                active_pages=frozenset({1}),
            )

            pages_with_spans = {span.page_number for span in spans}
        self.assertEqual(pages_with_spans, {1})

    def test_active_pages_none_produces_spans_on_every_page(self) -> None:
        from pdf_redaction import extract_pdf_word_pages

        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_multi_page_pdf(
                source_path,
                [
                    ["PESEL 00000000000 on page one."],
                    ["PESEL 11111111111 on page two."],
                ],
            )
            word_pages = extract_pdf_word_pages(source_path)

            spans = _pdf_detection_spans_for_word_pages(
                word_pages, sensitive_terms=None, ner_context=None
            )

            pages_with_spans = {span.page_number for span in spans}
        self.assertEqual(pages_with_spans, {1, 2})


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

    def test_visual_pdf_page_range_leaves_out_of_scope_pages_untouched(self) -> None:
        """Etap 5 end-to-end: a page outside the chosen range must come
        through the visual PDF exactly as in the source, while a page
        inside the range is redacted as normal."""
        with workspace_temp_dir() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            output_dir = Path(temp_dir) / "output"
            source_dir.mkdir()
            output_dir.mkdir()
            source_path = source_dir / "document.pdf"
            write_fitz_multi_page_pdf(
                source_path,
                [
                    ["PESEL 00000000000 on page one."],
                    ["PESEL 11111111111 on page two."],
                ],
            )

            anonymize_batch(
                [source_path],
                output_dir,
                page_range="1",
            )

            import pymupdf as fitz

            visual_pdf = output_dir / "document_ANON_VISUAL.pdf"
            self.assertTrue(visual_pdf.exists())
            with fitz.open(visual_pdf) as document:
                page_one_text = document[0].get_text("text")
                page_two_text = document[1].get_text("text")
        self.assertNotIn("00000000000", page_one_text)
        self.assertIn("11111111111", page_two_text)

    def test_page_ranges_gives_each_file_in_a_batch_its_own_range(self) -> None:
        """Per-file page-range redesign: two PDFs in one batch, each
        with its own entry in page_ranges (keyed by resolved path) -
        each output must only respect its own file's range, never the
        other file's."""
        with workspace_temp_dir() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            output_dir = Path(temp_dir) / "output"
            source_dir.mkdir()
            output_dir.mkdir()
            first_path = source_dir / "first.pdf"
            second_path = source_dir / "second.pdf"
            write_fitz_multi_page_pdf(
                first_path,
                [
                    ["PESEL 00000000000 on page one of first."],
                    ["PESEL 11111111111 on page two of first."],
                ],
            )
            write_fitz_multi_page_pdf(
                second_path,
                [
                    ["PESEL 22222222222 on page one of second."],
                    ["PESEL 33333333333 on page two of second."],
                ],
            )

            anonymize_batch(
                [first_path, second_path],
                output_dir,
                page_ranges={
                    str(first_path.resolve()): "1",
                    str(second_path.resolve()): "2",
                },
            )

            import pymupdf as fitz

            with fitz.open(output_dir / "first_ANON_VISUAL.pdf") as document:
                first_page_one = document[0].get_text("text")
                first_page_two = document[1].get_text("text")
            with fitz.open(output_dir / "second_ANON_VISUAL.pdf") as document:
                second_page_one = document[0].get_text("text")
                second_page_two = document[1].get_text("text")
        # first.pdf: only page 1 in scope
        self.assertNotIn("00000000000", first_page_one)
        self.assertIn("11111111111", first_page_two)
        # second.pdf: only page 2 in scope - the opposite of first.pdf
        self.assertIn("22222222222", second_page_one)
        self.assertNotIn("33333333333", second_page_two)

    def test_page_ranges_missing_entry_falls_back_to_the_shared_page_range(self) -> None:
        """A file with no entry in page_ranges keeps using the older,
        whole-batch page_range value - full backward compatibility."""
        with workspace_temp_dir() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            output_dir = Path(temp_dir) / "output"
            source_dir.mkdir()
            output_dir.mkdir()
            source_path = source_dir / "document.pdf"
            write_fitz_multi_page_pdf(
                source_path,
                [
                    ["PESEL 00000000000 on page one."],
                    ["PESEL 11111111111 on page two."],
                ],
            )

            anonymize_batch(
                [source_path],
                output_dir,
                page_range="1",
                page_ranges={},
            )

            import pymupdf as fitz

            with fitz.open(output_dir / "document_ANON_VISUAL.pdf") as document:
                page_one_text = document[0].get_text("text")
                page_two_text = document[1].get_text("text")
        self.assertNotIn("00000000000", page_one_text)
        self.assertIn("11111111111", page_two_text)

    def test_page_range_beyond_document_surfaces_warning_end_to_end(self) -> None:
        """User-reported gap: a page range that doesn't overlap the real
        document (e.g. '5-8' on a 3-page PDF) used to anonymize
        "successfully" with no explanation that nothing happened. Exercises
        the real anonymize_batch -> _anonymize_pdf_file_result ->
        _attach_pdf_coverage_metadata wiring (page_count=len(active_word_pages)),
        not just the metadata helper directly."""
        with workspace_temp_dir() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            output_dir = Path(temp_dir) / "output"
            source_dir.mkdir()
            output_dir.mkdir()
            source_path = source_dir / "document.pdf"
            write_fitz_multi_page_pdf(
                source_path,
                [
                    ["PESEL 00000000000 on page one."],
                    ["PESEL 11111111111 on page two."],
                    ["PESEL 22222222222 on page three."],
                ],
            )

            batch_result = anonymize_batch(
                [source_path],
                output_dir,
                page_range="5-8",
            )

            self.assertEqual(len(batch_result.results), 1)
            warning = str(
                batch_result.results[0].get("pdf_redaction_warning", "")
            )
            self.assertIn("5, 6, 7, 8", warning)
            self.assertIn("3-page", warning)

    def test_visual_pdf_redacts_table_separated_nip_and_regon(self) -> None:
        """anonymizer.py's own PDF word-coordinate path
        (_table_separated_nip_regon_pdf_spans/_regex_pdf_spans_for_page)
        for the table-separated NIP/REGON fallback - the direct
        regression test for the exact scenario reported live on a real
        invoice (label block, then value block, a few lines apart).
        pdf_redaction.py's independent copy of the same fallback is
        covered separately in tests/test_pdf_io.py, since this module
        can't import that one's copy (circular import)."""
        with workspace_temp_dir() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            output_dir = Path(temp_dir) / "output"
            source_dir.mkdir()
            output_dir.mkdir()
            source_path = source_dir / "invoice.pdf"
            write_fitz_text_pdf(
                source_path, ["NIP", "REGON", "526-000-12-46", "012345678"]
            )

            anonymize_batch(
                [source_path],
                output_dir,
                active_categories=[CATEGORY_COMPANY],
            )

            import pymupdf as fitz

            visual_pdf = output_dir / "invoice_ANON_VISUAL.pdf"
            self.assertTrue(visual_pdf.exists())
            with fitz.open(visual_pdf) as document:
                visible_text = "\n".join(page.get_text("text") for page in document)
        self.assertNotIn("526-000-12-46", visible_text)
        self.assertNotIn("012345678", visible_text)

    def test_visual_pdf_redacts_company_name_with_legal_form_suffix(self) -> None:
        """Direct regression test for the other real miss reported live
        on the same invoice: spaCy's NER only caught "z o.o." out of
        "Usługi Biurowe Testowski Sp. z o.o." and missed "Firma Wzorcowa
        S.A." entirely. NAZWA_FIRMY_PATTERN (_PATTERNS) is a
        deterministic regex safety net that runs regardless of NER."""
        with workspace_temp_dir() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            output_dir = Path(temp_dir) / "output"
            source_dir.mkdir()
            output_dir.mkdir()
            source_path = source_dir / "invoice.pdf"
            write_fitz_text_pdf(
                source_path,
                ["Uslugi Biurowe Testowski Sp. z o.o.", "Firma Wzorcowa S.A."],
            )

            anonymize_batch(
                [source_path],
                output_dir,
                active_categories=[CATEGORY_COMPANY],
            )

            import pymupdf as fitz

            visual_pdf = output_dir / "invoice_ANON_VISUAL.pdf"
            self.assertTrue(visual_pdf.exists())
            with fitz.open(visual_pdf) as document:
                visible_text = "\n".join(page.get_text("text") for page in document)
        self.assertNotIn("Testowski", visible_text)
        self.assertNotIn("Wzorcowa", visible_text)


class PdfSpanOrderingRegressionTests(unittest.TestCase):
    """Regression guard for a real bug the code-review pass caught: an
    earlier version filtered spans *after* detection, but _add_pdf_span
    reserves the character range in occupied_ranges as a side effect of
    being called - regardless of whether that span survived to the
    filtered result. An excluded regex label (e.g. ULICA, part of the
    "address" category) would still reserve its range, silently blocking
    an always-on NER span (e.g. NER_PERSON) for overlapping text from
    ever being added by the later NER pass - leaving that PII completely
    unredacted in both categories. Fixed by filtering *before* each span
    is added, in every per-page helper, not just at the end.
    """

    def test_excluding_address_does_not_block_an_overlapping_always_on_ner_span(
        self,
    ) -> None:
        text = "Klient mieszka: ul. Jana Kowalskiego 5, dziekujemy."
        ulica_pattern = dict(_PATTERNS)["ULICA"]
        match = ulica_pattern.search(text)
        self.assertIsNotNone(
            match, "test setup: ULICA pattern must match the fixture text"
        )
        word_pages = [PdfWordPage(page_number=1, text=text, words=())]
        ner_context = NerContext(enabled=True, status="available", model_name="x")

        with patch("anonymizer.detect_entities_with_details") as mock_detect:
            mock_detect.return_value = (
                [NerEntity(start=match.start(), end=match.end(), label="NER_PERSON")],
                {"NER_PERSON": 1},
                {},
                0,
            )
            active = resolve_active_labels([CATEGORY_PERSON])  # address excluded
            spans = _pdf_detection_spans_for_word_pages(
                word_pages,
                sensitive_terms=None,
                ner_context=ner_context,
                active_labels=active,
            )

        labels = {span.label for span in spans}
        self.assertNotIn("ULICA", labels)
        self.assertIn(
            "NER_PERSON",
            labels,
            "an excluded category's span must not have reserved the range "
            "and silently blocked an always-on category's span for the "
            "same text",
        )


class AuditAddressProxyExclusionTests(unittest.TestCase):
    """Regression guard: audit.py's own leftover-risk scanner has its own,
    broader ADDRESS_LIKE/STREET_LIKE proxy patterns with no exact
    counterpart in SUPPORTED_LABELS - excluding "address" must suppress
    those too, or the scanner keeps flagging a deliberately-unredacted
    address as false "high risk"."""

    def test_excluding_address_also_suppresses_the_audit_only_proxy_patterns(
        self,
    ) -> None:
        text = "Klient mieszka przy ul. Kwiatowa 12."
        active = resolve_active_labels(
            [c for c in CATEGORY_GROUPS if c != CATEGORY_ADDRESS]
        )
        result = audit_text(text, excluded_labels=_excluded_labels_for_audit(active))
        self.assertEqual(result["findings"].get("ADDRESS_LIKE", 0), 0)
        self.assertEqual(result["findings"].get("STREET_LIKE", 0), 0)

    def test_address_proxy_patterns_still_flagged_when_address_is_active(
        self,
    ) -> None:
        text = "Klient mieszka przy ul. Kwiatowa 12."
        active = resolve_active_labels(list(CATEGORY_GROUPS))  # everything selected
        result = audit_text(text, excluded_labels=_excluded_labels_for_audit(active))
        self.assertGreater(result["findings"].get("ADDRESS_LIKE", 0), 0)


class MagicPenRegenerateRespectsCategorySelectionTests(unittest.TestCase):
    """Regression guard for a real bug the code-review pass caught: the
    magic-pen manual-edit "regenerate" path had no active_categories
    parameter at all, so saving any unrelated manual edit silently
    redacted every category again - even ones the user had explicitly
    excluded from the original run - overwriting the approved output
    with a different, more-redacted document with no warning."""

    def test_category_selection_sidecar_round_trips(self) -> None:
        with workspace_temp_dir() as temp_dir:
            output_path = Path(temp_dir) / "document_ANON_VISUAL.pdf"
            path = category_selection_path(output_path)

            save_category_selection(path, ["pesel", "email"])

            loaded = load_category_selection(path)
        self.assertEqual(loaded, resolve_active_labels(["pesel", "email"]))
        self.assertIn("PESEL", loaded)
        self.assertIn("EMAIL", loaded)
        self.assertNotIn("TELEFON", loaded)

    def test_page_range_sidecar_round_trips(self) -> None:
        """Sibling of test_category_selection_sidecar_round_trips for
        Etap 5's page-range field, via load_active_pages_selection - an
        independent function reading the same sidecar file rather than
        widening load_category_selection's return shape, so every
        existing caller/test of the label-only loader above keeps
        working unchanged."""
        with workspace_temp_dir() as temp_dir:
            output_path = Path(temp_dir) / "document_ANON_VISUAL.pdf"
            path = category_selection_path(output_path)

            save_category_selection(path, ["pesel"], page_range="1-3,5")

            loaded_labels = load_category_selection(path)
            loaded_pages = load_active_pages_selection(path)
        self.assertEqual(loaded_labels, resolve_active_labels(["pesel"]))
        self.assertEqual(loaded_pages, frozenset({1, 2, 3, 5}))

    def test_old_format_sidecar_without_active_pages_loads_as_none(self) -> None:
        """A sidecar written before Etap 5 existed has no "active_pages"
        key at all - must fall back to None ("no filtering"), the same
        safe direction test_old_format_sidecar_without_active_labels_loads_as_none
        already established for the label-only case."""
        with workspace_temp_dir() as temp_dir:
            output_path = Path(temp_dir) / "document_ANON_VISUAL.pdf"
            path = category_selection_path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps({"active_categories": ["pesel"]}), encoding="utf-8"
            )

            self.assertIsNone(load_active_pages_selection(path))

    def test_malformed_sidecar_with_non_positive_pages_loads_as_none(self) -> None:
        """Regression test for a real bug code review caught: without
        this check, a hand-edited/corrupted sidecar containing
        {"active_pages": [-1, 0]} would load as a literal frozenset no
        real page.page_number (always >= 1) ever matches - silently
        making every page look "out of scope" on the next magic-pen
        regenerate, redacting nothing anywhere with no error surfaced.
        Falling back to None (no filtering) is the same safe direction
        every other malformed-sidecar case in this mechanism already
        takes."""
        with workspace_temp_dir() as temp_dir:
            output_path = Path(temp_dir) / "document_ANON_VISUAL.pdf"
            path = category_selection_path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps({"active_pages": [-1, 0]}), encoding="utf-8"
            )

            self.assertIsNone(load_active_pages_selection(path))

    def test_sidecar_freezes_the_label_set_active_at_save_time(self) -> None:
        """Regression test for a real bug found live (2026-09-17):
        CATEGORY_GROUPS's mapping can itself change between app versions
        (confirmed: NER_ORG/NER_LOCATION moved into CATEGORY_COMPANY/
        CATEGORY_ADDRESS). A sidecar written under an *older* mapping
        must keep meaning what it meant at save time, not silently
        change meaning when a later regenerate reads it back under a
        *newer* mapping - proven here by passing a fabricated
        active_categories value that resolve_active_labels would treat
        completely differently, and confirming compute_pdf_redaction_spans
        used the frozen active_labels instead.
        """
        with workspace_temp_dir() as temp_dir:
            output_path = Path(temp_dir) / "document_ANON_VISUAL.pdf"
            path = category_selection_path(output_path)
            save_category_selection(path, [CATEGORY_PESEL])
            frozen_labels = load_category_selection(path)

            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_text_pdf(
                source_path, ["Contact tester@example.test about PESEL 00000000000."]
            )
            _word_pages, spans = compute_pdf_redaction_spans(
                source_path,
                # A category name resolve_active_labels would expand to
                # *every* category - if the frozen active_labels weren't
                # actually taking precedence, EMAIL would show up too.
                active_categories=list(CATEGORY_GROUPS),
                active_labels=frozen_labels,
            )

        labels_found = {s.label for s in spans}
        self.assertIn("PESEL", labels_found)
        self.assertNotIn("EMAIL", labels_found)

    def test_old_format_sidecar_without_active_labels_loads_as_none(self) -> None:
        """An old-format sidecar (from before active_labels existed)
        only has active_categories - re-resolving those names against
        today's CATEGORY_GROUPS could silently change what they meant
        (see test_sidecar_freezes_the_label_set_active_at_save_time), so
        this must fall back to None ("no filtering") rather than guess -
        the same safe direction a missing/corrupt sidecar already took.
        """
        with workspace_temp_dir() as temp_dir:
            output_path = Path(temp_dir) / "document_ANON_VISUAL.pdf"
            path = category_selection_path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps({"active_categories": ["pesel"]}), encoding="utf-8"
            )

            self.assertIsNone(load_category_selection(path))

    def test_missing_sidecar_loads_as_none_meaning_unfiltered(self) -> None:
        with workspace_temp_dir() as temp_dir:
            missing = category_selection_path(
                Path(temp_dir) / "document_ANON_VISUAL.pdf"
            )
            self.assertIsNone(load_category_selection(missing))

    def test_corrupt_sidecar_loads_as_none_not_a_crash(self) -> None:
        with workspace_temp_dir() as temp_dir:
            output_path = Path(temp_dir) / "document_ANON_VISUAL.pdf"
            path = category_selection_path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{not valid json", encoding="utf-8")

            self.assertIsNone(load_category_selection(path))

    def test_compute_pdf_redaction_spans_respects_active_categories(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_text_pdf(
                source_path, ["Contact tester@example.test about PESEL 00000000000."]
            )

            _word_pages, unfiltered_spans = compute_pdf_redaction_spans(source_path)
            _word_pages, filtered_spans = compute_pdf_redaction_spans(
                source_path, active_categories=["pesel"]
            )

        self.assertIn("EMAIL", {s.label for s in unfiltered_spans})
        self.assertNotIn("EMAIL", {s.label for s in filtered_spans})
        self.assertIn("PESEL", {s.label for s in filtered_spans})

    def test_compute_pdf_redaction_spans_respects_page_range(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_multi_page_pdf(
                source_path,
                [
                    ["PESEL 00000000000 on page one."],
                    ["PESEL 11111111111 on page two."],
                ],
            )

            _word_pages, unfiltered_spans = compute_pdf_redaction_spans(source_path)
            _word_pages, filtered_spans = compute_pdf_redaction_spans(
                source_path, page_range="1"
            )

        self.assertEqual(
            {s.page_number for s in unfiltered_spans}, {1, 2}
        )
        self.assertEqual({s.page_number for s in filtered_spans}, {1})

    def test_batch_run_writes_a_category_selection_sidecar_for_the_visual_pdf(
        self,
    ) -> None:
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
                [source_path], output_dir, active_categories=[CATEGORY_PESEL]
            )

            visual_pdf = output_dir / "document_ANON_VISUAL.pdf"
            self.assertTrue(visual_pdf.exists())
            recorded = load_category_selection(category_selection_path(visual_pdf))
        self.assertEqual(recorded, resolve_active_labels([CATEGORY_PESEL]))

    def test_batch_run_writes_a_page_range_sidecar_for_the_visual_pdf(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            output_dir = Path(temp_dir) / "output"
            source_dir.mkdir()
            output_dir.mkdir()
            source_path = source_dir / "document.pdf"
            write_fitz_multi_page_pdf(
                source_path,
                [
                    ["PESEL 00000000000 on page one."],
                    ["PESEL 11111111111 on page two."],
                ],
            )

            anonymize_batch([source_path], output_dir, page_range="1")

            visual_pdf = output_dir / "document_ANON_VISUAL.pdf"
            self.assertTrue(visual_pdf.exists())
            recorded = load_active_pages_selection(category_selection_path(visual_pdf))
        self.assertEqual(recorded, frozenset({1}))

    def test_magic_pen_regenerate_reuses_the_frozen_page_range(self) -> None:
        """End-to-end regression guard, mirroring
        MagicPenRegenerateRespectsCategorySelectionTests' own reasoning
        for active_labels: a manual edit's "regenerate" pass must keep
        honoring the page range the document was first produced with,
        loaded from the same sidecar - never silently redact an
        out-of-scope page again just because an unrelated manual edit
        was saved."""
        from manual_redaction import (
            EMPTY_MANUAL_EDITS,
            regenerate_pdf_with_manual_overrides,
        )

        with workspace_temp_dir() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            output_dir = Path(temp_dir) / "output"
            source_dir.mkdir()
            output_dir.mkdir()
            source_path = source_dir / "document.pdf"
            write_fitz_multi_page_pdf(
                source_path,
                [
                    ["PESEL 00000000000 on page one."],
                    ["PESEL 11111111111 on page two."],
                ],
            )

            anonymize_batch([source_path], output_dir, page_range="1")
            visual_pdf = output_dir / "document_ANON_VISUAL.pdf"
            frozen_pages = load_active_pages_selection(
                category_selection_path(visual_pdf)
            )

            regenerate_pdf_with_manual_overrides(
                source_path,
                output_path=visual_pdf,
                edits=EMPTY_MANUAL_EDITS,
                active_pages=frozen_pages,
            )

            import pymupdf as fitz

            with fitz.open(visual_pdf) as document:
                page_one_text = document[0].get_text("text")
                page_two_text = document[1].get_text("text")
        self.assertNotIn("00000000000", page_one_text)
        self.assertIn("11111111111", page_two_text)


class UpdateSignatureStrippingSelectionTests(unittest.TestCase):
    """Coverage for the sidecar patch ComparisonWindow's magic-pen
    signature-removal toggle uses (see _save_pending_changes) - rewrites
    only strip_signatures, from already-resolved active_labels/
    active_pages, without re-resolving raw category names/page-range
    text (which ComparisonWindow never retains - see the function's own
    docstring for why re-resolving would reopen the CATEGORY_GROUPS-
    mapping staleness problem load_category_selection guards against)."""

    def test_round_trips_the_new_strip_signatures_value(self) -> None:
        with workspace_temp_dir() as temp_dir:
            output_path = Path(temp_dir) / "document_ANON_VISUAL.pdf"
            path = category_selection_path(output_path)
            save_category_selection(path, ["pesel"], strip_signatures=False)

            update_signature_stripping_selection(
                path,
                active_labels=frozenset({"PESEL"}),
                active_pages=None,
                strip_signatures=True,
            )

            self.assertTrue(load_signature_stripping_selection(path))

    def test_preserves_active_labels_and_active_pages(self) -> None:
        """The whole point of this function over re-calling
        save_category_selection: active_labels/active_pages must pass
        through unchanged, exactly as ComparisonWindow already had them
        resolved at window-open time."""
        with workspace_temp_dir() as temp_dir:
            output_path = Path(temp_dir) / "document_ANON_VISUAL.pdf"
            path = category_selection_path(output_path)

            update_signature_stripping_selection(
                path,
                active_labels=frozenset({"PESEL", "EMAIL"}),
                active_pages=frozenset({1, 3}),
                strip_signatures=True,
            )

            self.assertEqual(
                load_category_selection(path), frozenset({"PESEL", "EMAIL"})
            )
            self.assertEqual(load_active_pages_selection(path), frozenset({1, 3}))
            self.assertTrue(load_signature_stripping_selection(path))

    def test_none_active_labels_and_pages_round_trip_as_no_filtering(self) -> None:
        with workspace_temp_dir() as temp_dir:
            output_path = Path(temp_dir) / "document_ANON_VISUAL.pdf"
            path = category_selection_path(output_path)

            update_signature_stripping_selection(
                path,
                active_labels=None,
                active_pages=None,
                strip_signatures=False,
            )

            self.assertIsNone(load_category_selection(path))
            self.assertIsNone(load_active_pages_selection(path))
            self.assertFalse(load_signature_stripping_selection(path))


class AttachPdfCoverageMetadataCategoryAwarenessTests(unittest.TestCase):
    """Direct coverage for the active_labels branch - previously only
    exercised indirectly through the full PDF end-to-end test."""

    def test_deliberately_excluded_category_does_not_trigger_coverage_warning(
        self,
    ) -> None:
        active = resolve_active_labels([CATEGORY_PESEL])  # EMAIL excluded

        metadata = _attach_pdf_coverage_metadata(
            {"counters": {"PESEL": 1}},  # PDF redacted PESEL only
            counters={"PESEL": 1, "EMAIL": 1},  # both detected in the text
            audit_result={"findings": {}},
            ner_result={"counters": {}},
            active_labels=active,
        )

        self.assertNotIn("warning", metadata)
        self.assertEqual(metadata.get("detected_not_pdf_redacted_categories"), {})

    def test_unexcluded_gap_still_triggers_coverage_warning(self) -> None:
        active = resolve_active_labels([CATEGORY_PESEL, CATEGORY_EMAIL])

        metadata = _attach_pdf_coverage_metadata(
            {"counters": {"PESEL": 1}},  # EMAIL detected but not redacted
            counters={"PESEL": 1, "EMAIL": 1},
            audit_result={"findings": {}},
            ner_result={"counters": {}},
            active_labels=active,
        )

        self.assertIn("warning", metadata)
        self.assertIn("EMAIL", metadata.get("detected_not_pdf_redacted_categories", {}))

    def test_active_labels_none_behaves_like_before(self) -> None:
        metadata = _attach_pdf_coverage_metadata(
            {"counters": {"PESEL": 1}},
            counters={"PESEL": 1, "EMAIL": 1},
            audit_result={"findings": {}},
            ner_result={"counters": {}},
        )

        self.assertIn("warning", metadata)

    def test_active_pages_suppresses_the_coverage_warning_entirely(self) -> None:
        """Regression test for a real bug code review caught: every count
        this function compares is whole-document (the parallel TXT/
        report pipeline is never page-scoped), so a category detected
        only on a deliberately out-of-scope page looked identical to a
        genuine redaction gap - firing PDF_COVERAGE_WARNING on the
        *normal, expected* case of a user restricting to page 1 and
        having, say, a PESEL on page 2. That directly contradicts the
        "Strony" field's own promise that the rest of the document stays
        untouched, so the whole gap check must be suppressed (not just
        narrowed) whenever any page restriction is active."""
        metadata = _attach_pdf_coverage_metadata(
            {"counters": {}},  # nothing redacted on the in-scope page
            counters={"PESEL": 1},  # detected somewhere in the whole document
            audit_result={"findings": {}},
            ner_result={"counters": {}},
            active_pages=frozenset({1}),
        )

        self.assertNotIn("warning", metadata)
        self.assertEqual(metadata.get("detected_not_pdf_redacted_categories"), {})

    def test_active_pages_none_behaves_like_before(self) -> None:
        metadata = _attach_pdf_coverage_metadata(
            {"counters": {}},
            counters={"PESEL": 1},
            audit_result={"findings": {}},
            ner_result={"counters": {}},
        )

        self.assertIn("warning", metadata)

    def test_page_range_entirely_beyond_document_triggers_warning(self) -> None:
        """A user typing e.g. '5-8' on a 3-page document used to silently
        produce a no-op 'successful' anonymization with no explanation -
        reported by the user after testing Etap 5. With page_count now
        wired through, this must surface a warning instead of staying
        silent."""
        metadata = _attach_pdf_coverage_metadata(
            {"counters": {}},
            counters={},
            audit_result={"findings": {}},
            ner_result={"counters": {}},
            active_pages=frozenset({5, 6, 7, 8}),
            page_count=3,
        )

        self.assertIn("warning", metadata)
        self.assertIn("5, 6, 7, 8", metadata["warning"])
        self.assertIn("3-page", metadata["warning"])

    def test_page_range_partially_overlapping_document_does_not_warn(self) -> None:
        metadata = _attach_pdf_coverage_metadata(
            {"counters": {}},
            counters={"PESEL": 1},
            audit_result={"findings": {}},
            ner_result={"counters": {}},
            active_pages=frozenset({2, 3, 4}),
            page_count=3,
        )

        self.assertNotIn("warning", metadata)

    def test_page_count_defaulting_to_zero_skips_out_of_bounds_check(self) -> None:
        """Callers that don't know the real page count (page_count's
        default) must not have the bounds check misfire on frozenset({}) *
        range(1, 1) always being disjoint."""
        metadata = _attach_pdf_coverage_metadata(
            {"counters": {}},
            counters={},
            audit_result={"findings": {}},
            ner_result={"counters": {}},
            active_pages=frozenset({5, 6}),
        )

        self.assertNotIn("warning", metadata)


class SaveRedactedPdfCopyCategoryFilteringTests(unittest.TestCase):
    """Direct coverage for the "original_redaction" text-search fallback
    PDF path's own active_labels filtering - previously only exercised
    indirectly through the word-coordinate visual PDF end-to-end test,
    which never reaches this separate, duplicated pattern set."""

    def test_active_labels_filters_the_fallback_redaction_path_too(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_text_pdf(
                source_path, ["Contact tester@example.test about PESEL 00000000000."]
            )
            active = resolve_active_labels([CATEGORY_PESEL])  # email excluded

            result = save_redacted_pdf_copy(
                source_path,
                output_path=Path(temp_dir) / "out.pdf",
                active_labels=active,
            )

            import pymupdf as fitz

            with fitz.open(Path(temp_dir) / "out.pdf") as document:
                visible_text = "\n".join(page.get_text("text") for page in document)
        self.assertNotIn("00000000000", visible_text)
        self.assertIn("tester@example.test", visible_text)
        self.assertNotIn("EMAIL", result["counters"])

    def test_active_pages_filters_the_fallback_redaction_path_too(self) -> None:
        """Regression test for a real gap code review caught: this
        "experimental original-layout redaction" output mode is a
        separate code path from the default visual-redaction one and
        was burning PII out of every page regardless of the user's
        chosen page range."""
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_multi_page_pdf(
                source_path,
                [
                    ["PESEL 00000000000 on page one."],
                    ["PESEL 11111111111 on page two."],
                ],
            )

            save_redacted_pdf_copy(
                source_path,
                output_path=Path(temp_dir) / "out.pdf",
                active_pages=frozenset({1}),
            )

            import pymupdf as fitz

            with fitz.open(Path(temp_dir) / "out.pdf") as document:
                page_one_text = document[0].get_text("text")
                page_two_text = document[1].get_text("text")
        self.assertNotIn("00000000000", page_one_text)
        self.assertIn("11111111111", page_two_text)


class WeakPhoneLikeSkippedCountPageRangeTests(unittest.TestCase):
    """Regression test for a real gap code review caught: this count
    fed the "PDF redaction blocks" report section and iterated every
    page regardless of active_pages, so the report could claim a weak
    phone-like value was "skipped" on a page that was never touched at
    all when a page range was active."""

    def test_batch_report_only_counts_weak_phone_like_values_on_in_scope_pages(
        self,
    ) -> None:
        with workspace_temp_dir() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            output_dir = Path(temp_dir) / "output"
            source_dir.mkdir()
            output_dir.mkdir()
            source_path = source_dir / "document.pdf"
            # A bare 9-digit run with no phone-context keyword nearby is
            # exactly what _weak_phone_like_without_context_count flags.
            write_fitz_multi_page_pdf(
                source_path,
                [
                    ["Reference number 123 456 789 for this record."],
                    ["Reference number 987 654 321 for this record."],
                ],
            )

            anonymize_batch([source_path], output_dir, page_range="2")

            report_text = (
                output_dir / "_wewnetrzne" / "document_RAPORT.txt"
            ).read_text(encoding="utf-8")
            blocks_line = next(
                line
                for line in report_text.splitlines()
                if line.startswith("Weak phone-like numeric values skipped:")
            )
        self.assertEqual(int(blocks_line.rsplit(":", 1)[1].strip()), 1)


class PageRangeDoesNotApplyToImagesTests(unittest.TestCase):
    """Regression test for a real gap code review checked (and confirmed
    correct): page_range must never silently apply to an image input's
    single "page" - the "Strony" field's own label says "tylko PDF"."""

    def test_image_input_ignores_page_range(self) -> None:
        from ocr import (
            OCR_INPUT_TYPE_IMAGE,
            OCR_STATUS_AVAILABLE,
            OcrExtraction,
            build_ocr_metadata,
        )

        extraction = OcrExtraction(
            text="PESEL 00000000000",
            metadata=build_ocr_metadata(
                used=True,
                status=OCR_STATUS_AVAILABLE,
                input_type=OCR_INPUT_TYPE_IMAGE,
                items_processed=1,
            ),
        )

        with workspace_temp_dir() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            output_dir = Path(temp_dir) / "output"
            source_dir.mkdir()
            output_dir.mkdir()
            source_path = source_dir / "scan.png"
            source_path.write_bytes(b"synthetic image placeholder")

            with patch("anonymizer.extract_text_with_ocr", return_value=extraction):
                # An out-of-range page number ("99") would be a no-op even
                # for a PDF - the point here is that it must not somehow
                # suppress redaction on the image's own single "page".
                anonymize_batch([source_path], output_dir, page_range="99")

            output_text = (output_dir / "scan_ANON.txt").read_text(encoding="utf-8")
        self.assertIn("[PESEL]", output_text)


class OutOfBoundsWarningSurvivesOcrDoubleFallbackTests(unittest.TestCase):
    """Regression test for a real gap code review caught: for a scanned
    PDF whose word-level OCR is itself unavailable (OcrUnavailableError,
    e.g. no Tesseract), _anonymize_pdf_file_result falls back to plain
    ocr_word_pages staying empty - so page_count=len(active_word_pages)
    silently became 0 and disabled the out-of-bounds check for exactly
    this doubly-degraded path. Fixed by sourcing page_count from
    word_pages instead, which extract_pdf_word_pages always populates
    (one entry per real document page, even wordless ones) before the
    text-vs-OCR branch runs."""

    def test_out_of_bounds_range_still_warns_when_word_box_ocr_is_unavailable(
        self,
    ) -> None:
        from ocr import (
            OCR_INPUT_TYPE_PDF,
            OCR_STATUS_ENGINE_NOT_FOUND,
            OcrExtraction,
            OcrUnavailableError,
            build_ocr_metadata,
        )

        extraction = OcrExtraction(
            text="No PII here.",
            metadata=build_ocr_metadata(
                used=True,
                status=OCR_STATUS_ENGINE_NOT_FOUND,
                input_type=OCR_INPUT_TYPE_PDF,
                items_processed=3,
            ),
        )

        with workspace_temp_dir() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            output_dir = Path(temp_dir) / "output"
            source_dir.mkdir()
            output_dir.mkdir()
            source_path = source_dir / "scan.pdf"
            # No lines on any page -> no extractable text -> triggers the
            # word-box-OCR-then-plain-OCR fallback chain, exactly like a
            # real scanned PDF.
            write_fitz_multi_page_pdf(source_path, [[], [], []])

            with (
                patch(
                    "anonymizer.extract_pdf_word_boxes",
                    side_effect=OcrUnavailableError(
                        OCR_STATUS_ENGINE_NOT_FOUND, OCR_INPUT_TYPE_PDF, ""
                    ),
                ),
                patch("anonymizer.extract_text_with_ocr", return_value=extraction),
            ):
                batch_result = anonymize_batch(
                    [source_path], output_dir, page_range="10-20"
                )

            self.assertEqual(len(batch_result.results), 1)
            warning = str(batch_result.results[0].get("pdf_redaction_warning", ""))
        self.assertIn("10, 11", warning)
        self.assertIn("3-page", warning)


if __name__ == "__main__":
    unittest.main()
