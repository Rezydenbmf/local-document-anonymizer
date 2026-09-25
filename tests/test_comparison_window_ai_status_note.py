"""The comparison window says *why* there are no AI suggestions (2026-09-25
user report: both reviews had timed out, and the window looked the same
as "the AI found nothing")."""

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gui_comparison_window import ai_review_status_note, prepare_ai_review
from llm_suggestions import (
    LlmSuggestionsSidecar,
    llm_suggestions_path,
    save_llm_suggestions_result,
)


def workspace_temp_dir():
    return tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "tests")


class AiReviewStatusNoteTests(unittest.TestCase):
    def test_no_ai_run_gives_no_note(self) -> None:
        self.assertEqual(ai_review_status_note(LlmSuggestionsSidecar()), "")
        disabled = LlmSuggestionsSidecar(
            comparison_result={"status": "disabled"},
            narrative_result={"status": "disabled"},
        )
        self.assertEqual(ai_review_status_note(disabled), "")

    def test_timeout_is_named_explicitly(self) -> None:
        sidecar = LlmSuggestionsSidecar(
            comparison_result={"status": "timeout", "findings": []},
            narrative_result={"status": "completed", "suggestions": []},
        )
        self.assertIn("limit czasu", ai_review_status_note(sidecar))

    def test_other_failure(self) -> None:
        sidecar = LlmSuggestionsSidecar(
            comparison_result={"status": "invalid_response", "findings": []},
        )
        self.assertIn("nie powiodła się", ai_review_status_note(sidecar))

    def test_no_model_configured_is_named_explicitly(self) -> None:
        # The real 2026-09-25 sidecar: AI toggled on from the home screen,
        # no model chosen - it used to read as a generic failure.
        sidecar = LlmSuggestionsSidecar(
            comparison_result={"status": "no_model_configured", "findings": []},
            narrative_result={"status": "no_model_configured", "suggestions": []},
        )
        self.assertIn("nie wybrano modelu", ai_review_status_note(sidecar))

    def test_missing_model_and_unreachable_ollama(self) -> None:
        missing = LlmSuggestionsSidecar(
            comparison_result={"status": "model_missing", "findings": []},
        )
        self.assertIn("nie ma", ai_review_status_note(missing))
        for status in ("ollama_not_found", "service_unavailable", "unavailable"):
            sidecar = LlmSuggestionsSidecar(
                comparison_result={"status": status, "findings": []},
            )
            self.assertIn("Ollama nie odpowiada", ai_review_status_note(sidecar))

    def test_completed_with_nothing_found(self) -> None:
        sidecar = LlmSuggestionsSidecar(
            comparison_result={"status": "completed", "findings": []},
            narrative_result={"status": "disabled"},
        )
        self.assertIn("nie zgłosiło", ai_review_status_note(sidecar))


class PrepareAiReviewStatusNoteTests(unittest.TestCase):
    def test_timed_out_sidecar_yields_a_note_and_no_suggestions(self) -> None:
        with workspace_temp_dir() as temp_dir:
            result_path = Path(temp_dir) / "doc_ANON_VISUAL.pdf"
            save_llm_suggestions_result(
                llm_suggestions_path(result_path),
                comparison_result={"status": "timeout", "findings": []},
                narrative_result={"status": "timeout", "suggestions": []},
                original_text="tekst",
            )

            review = prepare_ai_review(result_path, Path(temp_dir) / "src.pdf", [])

        self.assertEqual(review.suggestions, [])
        self.assertIn("limit czasu", review.status_note)

    def test_missing_sidecar_yields_no_note(self) -> None:
        with workspace_temp_dir() as temp_dir:
            result_path = Path(temp_dir) / "doc_ANON_VISUAL.pdf"
            review = prepare_ai_review(result_path, Path(temp_dir) / "src.pdf", [])
        self.assertEqual(review.status_note, "")


if __name__ == "__main__":
    unittest.main()
