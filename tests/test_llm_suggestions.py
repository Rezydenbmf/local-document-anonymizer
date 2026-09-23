"""Tests for llm_suggestions.py - resolving llm_review.py's sentence-
index-based findings/suggestions to real PDF pages/rects via word-level
matching against pdf_redaction.extract_pdf_word_pages (see that module's
docstring for why word-level, not character-offset, matching is used).
"""

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from file_readers import read_pdf_file_pages
from llm_suggestions import (
    AI_SUGGESTION_SOURCE_COMPARISON,
    AI_SUGGESTION_SOURCE_NARRATIVE,
    AI_SUGGESTION_STATUS_PENDING,
    AiSuggestion,
    ai_suggestion_ids,
    ai_suggestion_sentence_texts,
    build_ai_suggestions,
    count_unresolved_ai_suggestions,
    llm_suggestions_path,
    load_llm_suggestions_result,
    load_llm_suggestions_sidecar,
    locate_sentence_texts,
    redactions_overlapping_area,
    resolve_sentence_page,
    resolve_sentence_rects,
    save_ai_suggestion_resolutions,
    save_llm_suggestions_result,
)
from pdf_redaction import extract_pdf_word_pages


def workspace_temp_dir():
    return tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "tests")


def write_fitz_text_pdf(path: Path, pages: list[list[str]]) -> None:
    """Write a real multi-page PDF via PyMuPDF, one list of lines per page -
    matching the helper other test_manual_redaction.py/test_pdf_io.py
    fixtures already use, extended here to support multiple pages."""
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


class ResolveSentenceRectsTests(unittest.TestCase):
    def test_finds_a_single_line_sentence_and_returns_its_page_and_rect(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_text_pdf(
                source_path,
                [["Jan Kowalski mieszka w Warszawie.", "Ma 30 lat."]],
            )
            word_pages = extract_pdf_word_pages(source_path)

            result = resolve_sentence_rects(
                "Jan Kowalski mieszka w Warszawie.", "PERSON_LIKE", word_pages
            )

            self.assertIsNotNone(result)
            page_number, rects = result
            self.assertEqual(page_number, 1)
            self.assertEqual(len(rects), 1)
            self.assertEqual(rects[0]["label"], "PERSON_LIKE")
            self.assertEqual(rects[0]["page"], 1)
            # The rect must cover the sentence's words, not the whole
            # page or the unrelated second sentence.
            self.assertGreater(rects[0]["x1"], rects[0]["x0"])

    def test_does_not_falsely_match_a_partial_word_overlap(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_text_pdf(
                source_path,
                [["Jan Kowalski mieszka w Warszawie.", "Ma 30 lat."]],
            )
            word_pages = extract_pdf_word_pages(source_path)

            result = resolve_sentence_rects(
                "Kompletnie inne zdanie.", "PERSON_LIKE", word_pages
            )

            self.assertIsNone(result)

    def test_finds_the_correct_page_in_a_multi_page_document(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_text_pdf(
                source_path,
                [
                    ["Strona pierwsza, nic ciekawego."],
                    ["Anna Nowak pracuje w Krakowie."],
                    ["Strona trzecia, znowu nic."],
                ],
            )
            word_pages = extract_pdf_word_pages(source_path)

            result = resolve_sentence_rects(
                "Anna Nowak pracuje w Krakowie.", "PERSON_LIKE", word_pages
            )

            self.assertIsNotNone(result)
            page_number, rects = result
            self.assertEqual(page_number, 2)
            self.assertTrue(rects)

    def test_returns_none_when_the_sentence_appears_on_no_page(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_text_pdf(source_path, [["Some ordinary text here."]])
            word_pages = extract_pdf_word_pages(source_path)

            result = resolve_sentence_rects(
                "This sentence was never in the document.",
                "PERSON_LIKE",
                word_pages,
            )

            self.assertIsNone(result)

    def test_case_insensitive_fallback_still_finds_a_real_run(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_text_pdf(source_path, [["Jan Kowalski mieszka tutaj."]])
            word_pages = extract_pdf_word_pages(source_path)

            # Differs only in case from what's actually on the page -
            # simulates a harmless casing difference between the two
            # text-extraction engines.
            result = resolve_sentence_rects(
                "jan kowalski mieszka tutaj.", "PERSON_LIKE", word_pages
            )

            self.assertIsNotNone(result)

    def test_empty_sentence_text_resolves_to_nothing(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_text_pdf(source_path, [["Anything at all."]])
            word_pages = extract_pdf_word_pages(source_path)

            self.assertIsNone(resolve_sentence_rects("   ", "PERSON_LIKE", word_pages))


class ResolveSentencePageTests(unittest.TestCase):
    def test_returns_just_the_page_number(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_text_pdf(
                source_path,
                [["Pierwsza strona tutaj."], ["Druga strona z Anna Nowak."]],
            )
            word_pages = extract_pdf_word_pages(source_path)

            self.assertEqual(
                resolve_sentence_page("Druga strona z Anna Nowak.", word_pages), 2
            )
            self.assertIsNone(resolve_sentence_page("Nie ma takiego zdania.", word_pages))


class CrossExtractionEngineTests(unittest.TestCase):
    """The whole point of matching at the word level (see llm_suggestions.py's
    module docstring): the ORIGINAL text llm_review.py actually splits into
    sentences comes from pypdf (file_readers.read_pdf_file_pages), not from
    PyMuPDF (pdf_redaction.extract_pdf_word_pages) - these tests build
    ``original_text`` the same way anonymizer.py's real PDF pipeline does,
    from a genuinely separate extraction call, rather than typing out the
    same string the fixture already used elsewhere in this file."""

    def test_a_real_pypdf_extracted_sentence_still_resolves_against_pymupdf_words(
        self,
    ) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_text_pdf(
                source_path,
                [["Jan Kowalski mieszka w Warszawie.", "Ma trzydziesci lat."]],
            )

            # This is genuinely pypdf's own extraction, not PyMuPDF's -
            # exactly what anonymizer.py's PDF path feeds run_llm_
            # comparison_review/run_llm_narrative_review as original_text.
            pypdf_page_texts = read_pdf_file_pages(source_path)
            original_text = "\n\n".join(pypdf_page_texts)
            word_pages = extract_pdf_word_pages(source_path)

            from llm_review import split_into_review_sentences

            sentences = split_into_review_sentences(original_text)
            self.assertTrue(
                any("Kowalski" in sentence for sentence in sentences),
                f"expected a sentence containing Kowalski, got: {sentences}",
            )
            target_sentence = next(s for s in sentences if "Kowalski" in s)

            result = resolve_sentence_rects(target_sentence, "PERSON_LIKE", word_pages)

            self.assertIsNotNone(
                result,
                "word-level matching should bridge pypdf's sentence text to "
                "PyMuPDF's word coordinates even though they come from "
                "different extraction libraries",
            )
            page_number, rects = result
            self.assertEqual(page_number, 1)
            self.assertTrue(rects)


class BuildAiSuggestionsTests(unittest.TestCase):
    def test_missed_redaction_finding_resolves_page_and_rects(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_text_pdf(
                source_path,
                [["Jan Kowalski mieszka w Warszawie.", "Nic wiecej tu nie ma."]],
            )
            word_pages = extract_pdf_word_pages(source_path)
            original_text = (
                "Jan Kowalski mieszka w Warszawie. Nic wiecej tu nie ma."
            )
            comparison_result = {
                "findings": [
                    {
                        "finding_type": "missed_redaction",
                        "category": "PERSON_LIKE",
                        "sentence_index": 1,
                        "justification": "wyglada jak imie i nazwisko",
                    }
                ]
            }

            suggestions = build_ai_suggestions(
                original_text,
                comparison_result=comparison_result,
                narrative_result=None,
                word_pages=word_pages,
            )

            self.assertEqual(len(suggestions), 1)
            suggestion = suggestions[0]
            self.assertEqual(suggestion.source, AI_SUGGESTION_SOURCE_COMPARISON)
            self.assertEqual(suggestion.status, AI_SUGGESTION_STATUS_PENDING)
            self.assertEqual(suggestion.page, 1)
            self.assertTrue(suggestion.rects)
            self.assertEqual(suggestion.sentence_indices, (1,))

    def test_unnecessary_redaction_finding_resolves_page_but_no_rects(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_text_pdf(source_path, [["Kontakt: biuro@example.test."]])
            word_pages = extract_pdf_word_pages(source_path)
            original_text = "Kontakt: biuro@example.test."
            comparison_result = {
                "findings": [
                    {
                        "finding_type": "unnecessary_redaction",
                        "category": "EMAIL",
                        "sentence_index": 1,
                        "justification": "to publiczny adres biura, nie osoby",
                    }
                ]
            }

            suggestions = build_ai_suggestions(
                original_text,
                comparison_result=comparison_result,
                narrative_result=None,
                word_pages=word_pages,
            )

            self.assertEqual(len(suggestions), 1)
            self.assertEqual(suggestions[0].page, 1)
            self.assertEqual(suggestions[0].rects, ())

    def test_narrative_suggestion_resolves_page_from_first_locatable_sentence(
        self,
    ) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_text_pdf(
                source_path,
                [["Jedyny na swiecie taki zabieg.", "Pacjent ma trzy rece."]],
            )
            word_pages = extract_pdf_word_pages(source_path)
            original_text = "Jedyny na swiecie taki zabieg. Pacjent ma trzy rece."
            narrative_result = {
                "suggestions": [
                    {
                        "confidence": "likely",
                        "category": "QUASI_IDENTIFIER_COMBINATION",
                        "sentence_indices": [1, 2],
                        "justification": "unikalna kombinacja szczegolow",
                    }
                ]
            }

            suggestions = build_ai_suggestions(
                original_text,
                comparison_result=None,
                narrative_result=narrative_result,
                word_pages=word_pages,
            )

            self.assertEqual(len(suggestions), 1)
            suggestion = suggestions[0]
            self.assertEqual(suggestion.source, AI_SUGGESTION_SOURCE_NARRATIVE)
            self.assertEqual(suggestion.confidence, "likely")
            self.assertEqual(suggestion.sentence_indices, (1, 2))
            self.assertEqual(suggestion.page, 1)
            self.assertEqual(suggestion.rects, ())

    def test_unresolvable_sentence_still_produces_a_suggestion_with_no_page(
        self,
    ) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_text_pdf(source_path, [["Zupelnie inna tresc dokumentu."]])
            word_pages = extract_pdf_word_pages(source_path)
            # sentence_index 1 in THIS original_text doesn't match anything
            # on the page above - simulates a pypdf/PyMuPDF extraction
            # mismatch severe enough that word matching fails outright.
            original_text = "To zdanie nigdy nie trafilo na strone."
            comparison_result = {
                "findings": [
                    {
                        "finding_type": "missed_redaction",
                        "category": "PERSON_LIKE",
                        "sentence_index": 1,
                        "justification": "test",
                    }
                ]
            }

            suggestions = build_ai_suggestions(
                original_text,
                comparison_result=comparison_result,
                narrative_result=None,
                word_pages=word_pages,
            )

            self.assertEqual(len(suggestions), 1)
            self.assertIsNone(suggestions[0].page)
            self.assertEqual(suggestions[0].rects, ())

    def test_out_of_range_sentence_index_is_defensive_not_a_crash(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_text_pdf(source_path, [["Jedno zdanie tylko."]])
            word_pages = extract_pdf_word_pages(source_path)
            comparison_result = {
                "findings": [
                    {
                        "finding_type": "missed_redaction",
                        "category": "PERSON_LIKE",
                        "sentence_index": 99,
                        "justification": "test",
                    }
                ]
            }

            suggestions = build_ai_suggestions(
                "Jedno zdanie tylko.",
                comparison_result=comparison_result,
                narrative_result=None,
                word_pages=word_pages,
            )

            self.assertEqual(len(suggestions), 1)
            self.assertIsNone(suggestions[0].page)

    def test_no_results_produces_an_empty_list(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_text_pdf(source_path, [["Anything."]])
            word_pages = extract_pdf_word_pages(source_path)

            suggestions = build_ai_suggestions(
                "Anything.",
                comparison_result=None,
                narrative_result=None,
                word_pages=word_pages,
            )

            self.assertEqual(suggestions, [])

    def test_garbage_top_level_results_do_not_crash(self) -> None:
        # A malformed/legacy result shape (a string, a bare list) must
        # degrade to "no suggestions from that source", never an
        # unhandled AttributeError that would abort building suggestions
        # for every OTHER finding in the same document too.
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_text_pdf(source_path, [["Anything."]])
            word_pages = extract_pdf_word_pages(source_path)

            suggestions = build_ai_suggestions(
                "Anything.",
                comparison_result="llm call failed",
                narrative_result=["not", "a", "dict"],
                word_pages=word_pages,
            )

            self.assertEqual(suggestions, [])

    def test_boolean_sentence_index_is_excluded_like_an_invalid_one(self) -> None:
        # bool is a subclass of int in Python - True must not silently
        # behave as sentence index 1.
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_text_pdf(source_path, [["Jan Kowalski mieszka tutaj."]])
            word_pages = extract_pdf_word_pages(source_path)
            comparison_result = {
                "findings": [
                    {
                        "finding_type": "missed_redaction",
                        "category": "PERSON_LIKE",
                        "sentence_index": True,
                        "justification": "test",
                    }
                ]
            }

            suggestions = build_ai_suggestions(
                "Jan Kowalski mieszka tutaj.",
                comparison_result=comparison_result,
                narrative_result=None,
                word_pages=word_pages,
            )

            self.assertEqual(len(suggestions), 1)
            self.assertEqual(suggestions[0].sentence_indices, ())
            self.assertIsNone(suggestions[0].page)

    def test_a_leading_bom_does_not_shift_sentence_one_out_of_alignment(self) -> None:
        # run_llm_comparison_review/run_llm_narrative_review normalize
        # (BOM-strip) original_text before splitting it into sentences,
        # via llm_review.normalize_review_text - build_ai_suggestions
        # must apply the exact same normalization, or sentence_index 1
        # would resolve against a first "sentence" that still has the
        # BOM character glued to its first word.
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_text_pdf(source_path, [["Jan Kowalski mieszka tutaj."]])
            word_pages = extract_pdf_word_pages(source_path)
            comparison_result = {
                "findings": [
                    {
                        "finding_type": "missed_redaction",
                        "category": "PERSON_LIKE",
                        "sentence_index": 1,
                        "justification": "test",
                    }
                ]
            }

            suggestions = build_ai_suggestions(
                "﻿Jan Kowalski mieszka tutaj.",
                comparison_result=comparison_result,
                narrative_result=None,
                word_pages=word_pages,
            )

            self.assertEqual(suggestions[0].page, 1)
            self.assertTrue(suggestions[0].rects)

    def test_sentence_wrapping_across_two_lines_still_resolves(self) -> None:
        # A real paragraph sentence commonly wraps onto a second line -
        # _merge_rects_by_line must group the matched words into
        # per-line rects covering the whole sentence, not just the part
        # that happens to share the first line.
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            # Two insert_text calls simulate two separate PDF lines that
            # together make up one sentence, exactly as a wrapped
            # paragraph line would extract via PyMuPDF's word list
            # (different line_no, contiguous word order).
            write_fitz_text_pdf(
                source_path,
                [
                    [
                        "Pacjentka urodzona w Warszawie obecnie mieszka",
                        "w Krakowie i pracuje jako pielegniarka.",
                    ]
                ],
            )
            word_pages = extract_pdf_word_pages(source_path)
            sentence = (
                "Pacjentka urodzona w Warszawie obecnie mieszka "
                "w Krakowie i pracuje jako pielegniarka."
            )

            result = resolve_sentence_rects(sentence, "PERSON_LIKE", word_pages)

            self.assertIsNotNone(result)
            page_number, rects = result
            self.assertEqual(page_number, 1)
            # One rect per PDF line the sentence's words span.
            self.assertEqual(len(rects), 2)

    def test_empty_word_pages_resolves_to_nothing_rather_than_crashing(self) -> None:
        self.assertIsNone(resolve_sentence_rects("Anything.", "PERSON_LIKE", []))
        self.assertIsNone(resolve_sentence_page("Anything.", []))

        suggestions = build_ai_suggestions(
            "Anything.",
            comparison_result={
                "findings": [
                    {
                        "finding_type": "missed_redaction",
                        "category": "PERSON_LIKE",
                        "sentence_index": 1,
                        "justification": "test",
                    }
                ]
            },
            narrative_result=None,
            word_pages=[],
        )

        self.assertEqual(len(suggestions), 1)
        self.assertIsNone(suggestions[0].page)

    def test_duplicate_sentence_text_resolves_to_the_first_occurrence(self) -> None:
        # Pinning down the documented, known limitation (see
        # llm_suggestions.py's module docstring): a sentence that
        # legitimately repeats verbatim resolves to whichever occurrence
        # is found first, not necessarily the one a human would expect.
        # This test exists so that behavior stays intentional and
        # visible, not an unspecified accident a future change could
        # silently alter either direction.
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_text_pdf(
                source_path,
                [
                    ["Jan Kowalski, PESEL 12345678901."],
                    ["Jan Kowalski, PESEL 12345678901."],
                ],
            )
            word_pages = extract_pdf_word_pages(source_path)

            result = resolve_sentence_rects(
                "Jan Kowalski, PESEL 12345678901.", "PERSON_LIKE", word_pages
            )

            self.assertIsNotNone(result)
            page_number, _rects = result
            self.assertEqual(page_number, 1)


class LlmSuggestionsSidecarTests(unittest.TestCase):
    def test_path_lives_in_hidden_internal_subfolder_named_after_output(self) -> None:
        with workspace_temp_dir() as temp_dir:
            output_pdf = Path(temp_dir) / "document_ANON_VISUAL.pdf"
            path = llm_suggestions_path(output_pdf)

            self.assertEqual(path.name, "document_ANON_VISUAL_LLM_SUGGESTIONS.json")
            self.assertEqual(path.parent, Path(temp_dir) / "_wewnetrzne")

    def test_save_and_load_round_trips_both_results(self) -> None:
        with workspace_temp_dir() as temp_dir:
            output_pdf = Path(temp_dir) / "document_ANON_VISUAL.pdf"
            comparison_result = {"status": "completed", "findings": [{"category": "PERSON_LIKE"}]}
            narrative_result = {"status": "completed", "suggestions": [{"confidence": "likely"}]}

            save_llm_suggestions_result(
                llm_suggestions_path(output_pdf),
                comparison_result=comparison_result,
                narrative_result=narrative_result,
            )
            loaded_comparison, loaded_narrative = load_llm_suggestions_result(
                llm_suggestions_path(output_pdf)
            )

            self.assertEqual(loaded_comparison, comparison_result)
            self.assertEqual(loaded_narrative, narrative_result)

    def test_load_missing_file_returns_none_none(self) -> None:
        with workspace_temp_dir() as temp_dir:
            missing = Path(temp_dir) / "does_not_exist_LLM_SUGGESTIONS.json"

            self.assertEqual(load_llm_suggestions_result(missing), (None, None))

    def test_load_corrupt_file_returns_none_none(self) -> None:
        with workspace_temp_dir() as temp_dir:
            corrupt = Path(temp_dir) / "corrupt_LLM_SUGGESTIONS.json"
            corrupt.write_text("{not valid json", encoding="utf-8")

            self.assertEqual(load_llm_suggestions_result(corrupt), (None, None))

    def test_save_normalizes_a_non_dict_result_to_none(self) -> None:
        with workspace_temp_dir() as temp_dir:
            path = Path(temp_dir) / "garbage_LLM_SUGGESTIONS.json"

            save_llm_suggestions_result(
                path, comparison_result="not a dict", narrative_result=None
            )
            loaded_comparison, loaded_narrative = load_llm_suggestions_result(path)

            self.assertIsNone(loaded_comparison)
            self.assertIsNone(loaded_narrative)


_COMPARISON = {
    "status": "completed",
    "findings": [
        {"finding_type": "missed_redaction", "sentence_index": 1},
        "garbage entry - skipped but still consumes index 1",
        {"finding_type": "unnecessary_redaction", "sentence_index": 2},
    ],
}
_NARRATIVE = {"status": "completed", "suggestions": [{"sentence_indices": [1]}]}


class SuggestionResolutionPersistenceTests(unittest.TestCase):
    def test_ids_match_what_build_ai_suggestions_produces(self) -> None:
        built = build_ai_suggestions(
            "Jedno. Dwa.",
            comparison_result=_COMPARISON,
            narrative_result=_NARRATIVE,
            word_pages=[],
        )
        self.assertEqual(
            ai_suggestion_ids(_COMPARISON, _NARRATIVE),
            [suggestion.id for suggestion in built],
        )
        self.assertEqual(
            ai_suggestion_ids(_COMPARISON, _NARRATIVE),
            ["comparison-0", "comparison-2", "narrative-0"],
        )

    def test_resolutions_merge_into_the_sidecar_and_drive_the_unresolved_count(
        self,
    ) -> None:
        with workspace_temp_dir() as temp_dir:
            output_pdf = Path(temp_dir) / "doc_ANON_VISUAL.pdf"
            sidecar_path = llm_suggestions_path(output_pdf)
            save_llm_suggestions_result(
                sidecar_path,
                comparison_result=_COMPARISON,
                narrative_result=_NARRATIVE,
                original_text="Jedno. Dwa.",
            )
            self.assertEqual(count_unresolved_ai_suggestions(output_pdf), 3)

            save_ai_suggestion_resolutions(sidecar_path, {"comparison-0": "accepted"})
            save_ai_suggestion_resolutions(sidecar_path, {"narrative-0": "rejected"})

            sidecar = load_llm_suggestions_sidecar(sidecar_path)
            self.assertEqual(
                dict(sidecar.resolved),
                {"comparison-0": "accepted", "narrative-0": "rejected"},
            )
            self.assertEqual(sidecar.unresolved_ids(), ["comparison-2"])
            self.assertEqual(count_unresolved_ai_suggestions(output_pdf), 1)
            # Everything else survives the merge untouched.
            self.assertEqual(sidecar.comparison_result, _COMPARISON)
            self.assertIsNotNone(sidecar.original_text_sha256)

    def test_invalid_resolution_values_are_never_trusted(self) -> None:
        with workspace_temp_dir() as temp_dir:
            sidecar_path = Path(temp_dir) / "x_LLM_SUGGESTIONS.json"
            save_llm_suggestions_result(
                sidecar_path, comparison_result=_COMPARISON, narrative_result=None
            )
            save_ai_suggestion_resolutions(
                sidecar_path, {"comparison-0": "maybe", "comparison-2": "accepted"}
            )
            self.assertEqual(
                dict(load_llm_suggestions_sidecar(sidecar_path).resolved),
                {"comparison-2": "accepted"},
            )

    def test_no_sidecar_means_nothing_to_resolve_and_nothing_written(self) -> None:
        with workspace_temp_dir() as temp_dir:
            output_pdf = Path(temp_dir) / "doc_ANON_VISUAL.pdf"
            self.assertEqual(count_unresolved_ai_suggestions(output_pdf), 0)
            self.assertIsNone(
                save_ai_suggestion_resolutions(
                    llm_suggestions_path(output_pdf), {"comparison-0": "accepted"}
                )
            )
            self.assertFalse(llm_suggestions_path(output_pdf).exists())


class SuggestionLocationTests(unittest.TestCase):
    def test_sentence_texts_resolve_locally_by_index(self) -> None:
        suggestion = AiSuggestion(
            id="narrative-0",
            source=AI_SUGGESTION_SOURCE_NARRATIVE,
            category="QUASI",
            justification="",
            sentence_indices=(2, 99),
        )
        self.assertEqual(
            ai_suggestion_sentence_texts("Pierwsze zdanie. Drugie zdanie.", suggestion),
            ["Drugie zdanie."],
        )

    def test_locate_sentence_texts_returns_hint_rects_on_the_right_page(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            write_fitz_text_pdf(source_path, [["Nic tu nie ma."], ["Pracuje jako chirurg."]])
            word_pages = extract_pdf_word_pages(source_path)

            rects = locate_sentence_texts(["Pracuje jako chirurg.", "Nie istnieje."], word_pages)

            self.assertEqual(len(rects), 1)
            self.assertEqual(rects[0]["page"], 2)

    def test_redactions_overlapping_area_only_picks_same_page_overlaps(self) -> None:
        area = [{"page": 1, "x0": 50, "y0": 50, "x1": 200, "y1": 70}]
        inside = {"page": 1, "label": "PESEL", "x0": 60, "y0": 52, "x1": 120, "y1": 68}
        other_line = {"page": 1, "label": "PESEL", "x0": 60, "y0": 80, "x1": 120, "y1": 95}
        other_page = {"page": 2, "label": "PESEL", "x0": 60, "y0": 52, "x1": 120, "y1": 68}
        touching_edge = {"page": 1, "label": "PESEL", "x0": 200, "y0": 52, "x1": 220, "y1": 68}

        result = redactions_overlapping_area([inside, other_line, other_page, touching_edge], area)

        self.assertEqual(result, [inside])

    def test_a_neighbouring_line_that_only_grazes_the_sentence_is_not_picked(self) -> None:
        # Review finding: tightly-leaded lines' word boxes overlap by a
        # fraction of a point - that must not stage un-redacting PII on the
        # line below the sentence.
        area = [{"page": 1, "x0": 50, "y0": 100.0, "x1": 300, "y1": 113.6}]
        next_line = {"page": 1, "label": "PESEL", "x0": 60, "y0": 113.2, "x1": 160, "y1": 126.8}
        same_line = {"page": 1, "label": "PESEL", "x0": 60, "y0": 100.4, "x1": 160, "y1": 113.9}

        result = redactions_overlapping_area([next_line, same_line], area)

        self.assertEqual(result, [same_line])


if __name__ == "__main__":
    unittest.main()
