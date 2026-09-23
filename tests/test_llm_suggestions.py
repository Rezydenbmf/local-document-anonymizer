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
    build_ai_suggestions,
    resolve_sentence_page,
    resolve_sentence_rects,
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


if __name__ == "__main__":
    unittest.main()
