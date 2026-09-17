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
    load_category_selection,
    resolve_active_labels,
    save_category_selection,
)
from audit import audit_text
from ner import NerContext, NerEntity, anonymize_text_with_ner
from pdf_redaction import PdfWordPage, save_redacted_pdf_copy


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
            from ner import NerEntity

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

            self.assertEqual(load_category_selection(path), ("pesel", "email"))

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
        self.assertEqual(recorded, (CATEGORY_PESEL,))


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


if __name__ == "__main__":
    unittest.main()
