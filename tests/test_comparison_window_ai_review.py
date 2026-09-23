"""Tests for the comparison window's local-LLM suggestion review mode
(2026-09-23): loading suggestions for an open PDF, the accept / reject /
mark-by-hand / apply-all decisions, undo, the dashed overlay, saving the
decisions, and the main window's approval gate.

Same bare-instance approach as test_comparison_window_magic_pen_visuals.py:
a real (withdrawn) Tk root and real canvases/widgets, no full window
chrome. The display in the development sandbox is locked, so what these
cannot prove - how it actually looks - is listed in
docs/DO_ZWERYFIKOWANIA.md for a manual check.
"""

import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import tkinter as tk

import customtkinter as ctk

from anonymizer import candidate_llm_review_texts, word_pages_for_redaction_geometry
from gui_app import AnonymizerApp
from gui_comparison_window import (
    AI_SUGGESTION_OUTLINE_COLOR,
    AiReviewData,
    ComparisonWindow,
    ai_quote_text,
    ai_scroll_fraction,
    ai_suggestion_title_pl,
    prepare_ai_review,
)
from gui_helpers import MAGIC_PEN_BUILTIN_BINDINGS, MAGIC_PEN_MODE_DEFAULT
from llm_suggestions import (
    AI_SUGGESTION_SOURCE_COMPARISON,
    AI_SUGGESTION_SOURCE_NARRATIVE,
    AI_SUGGESTION_STATUS_ACCEPTED,
    AI_SUGGESTION_STATUS_PENDING,
    AI_SUGGESTION_STATUS_REJECTED,
    AiSuggestion,
    llm_suggestions_path,
    load_llm_suggestions_sidecar,
    save_llm_suggestions_result,
)
from manual_redaction import (
    AI_SUGGESTION_LABEL,
    EMPTY_MANUAL_EDITS,
    MANUAL_REDACTION_LABEL,
    rect_info_key,
)
from review import ReviewItem


def workspace_temp_dir():
    return tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "tests")


MISSED = AiSuggestion(
    id="comparison-0",
    source=AI_SUGGESTION_SOURCE_COMPARISON,
    category="PERSON_LIKE",
    justification="nazwisko bez redakcji",
    sentence_indices=(1,),
    finding_type="missed_redaction",
    page=1,
    rects=({"page": 1, "label": "PERSON_LIKE", "x0": 72.0, "y0": 60.0, "x1": 200.0, "y1": 75.0},),
)
UNNECESSARY = AiSuggestion(
    id="comparison-1",
    source=AI_SUGGESTION_SOURCE_COMPARISON,
    category="OTHER_SENSITIVE_CONTEXT",
    justification="to nie jest dana osobowa",
    sentence_indices=(2,),
    finding_type="unnecessary_redaction",
    page=1,
)
NARRATIVE = AiSuggestion(
    id="narrative-0",
    source=AI_SUGGESTION_SOURCE_NARRATIVE,
    category="QUASI_IDENTIFIER_COMBINATION",
    justification="zawód i miejsce razem",
    sentence_indices=(3,),
    confidence="likely",
    page=2,
)
MISSED_PAGE_2 = AiSuggestion(
    id="comparison-2",
    source=AI_SUGGESTION_SOURCE_COMPARISON,
    category="CONTACT_DATA_LIKE",
    justification="telefon",
    sentence_indices=(4,),
    finding_type="missed_redaction",
    page=2,
    rects=({"page": 2, "label": "CONTACT_DATA_LIKE", "x0": 72.0, "y0": 200.0, "x1": 150.0, "y1": 215.0},),
)
UNNECESSARY_AREA = {"page": 1, "x0": 72.0, "y0": 100.0, "x1": 300.0, "y1": 115.0}
REDACTION_IN_UNNECESSARY_AREA = {
    "page": 1, "label": "PESEL", "x0": 150.0, "y0": 101.0, "x1": 250.0, "y1": 114.0,
}
UNRELATED_REDACTION = {"page": 1, "label": "EMAIL", "x0": 72.0, "y0": 400.0, "x1": 200.0, "y1": 415.0}


def _review_data(*suggestions: AiSuggestion) -> AiReviewData:
    location_rects = {
        MISSED.id: [dict(MISSED.rects[0])],
        UNNECESSARY.id: [dict(UNNECESSARY_AREA)],
        NARRATIVE.id: [{"page": 2, "x0": 72.0, "y0": 90.0, "x1": 400.0, "y1": 105.0}],
        MISSED_PAGE_2.id: [dict(MISSED_PAGE_2.rects[0])],
    }
    return AiReviewData(
        list(suggestions),
        {s.id: location_rects[s.id] for s in suggestions},
        {s.id: [f"Zdanie {s.sentence_indices[0]}."] for s in suggestions},
        True,
    )


class AiReviewWindowTestBase(unittest.TestCase):
    _root = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._root = ctk.CTk()
        cls._root.withdraw()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._root.destroy()

    def _build_window(self, *suggestions: AiSuggestion, result_path: Path | None = None):
        window = ComparisonWindow.__new__(ComparisonWindow)
        window.app = types.SimpleNamespace(
            magic_pen_interaction_mode=MAGIC_PEN_MODE_DEFAULT,
            magic_pen_custom_bindings=dict(MAGIC_PEN_BUILTIN_BINDINGS[MAGIC_PEN_MODE_DEFAULT]),
            set_review_status=lambda *_args: None,
            review_dir=None,
        )
        window.window = self._root
        window.item = ReviewItem(output_name="doc_ANON.txt")
        window.locked = False
        window.edits = EMPTY_MANUAL_EDITS
        window.visible_rects = [dict(REDACTION_IN_UNNECESSARY_AREA), dict(UNRELATED_REDACTION)]
        window.pending_add_rects = []
        window.pending_remove_keys = set()
        window._original_strip_signatures = False
        window._current_strip_signatures = False
        window._strip_signatures_var = None
        window.save_button = None
        window.pen_status_label = None
        window._floating_actions = None
        window._edits_saved = False
        window._edit_undo_stack = []
        window._edit_redo_stack = []
        window.undo_button = None
        window.redo_button = None
        window._drag_start = None
        window._drag_rect_id = None
        window._active_gesture_action = None
        window._erased_this_gesture = set()
        window.right_frame = None
        window.left_frame = None
        window.zoom_linked = True
        window._original_page_widgets = {}
        window._page_entries = {}
        window._page_total_labels = {}
        window.original_page_count = 2
        window.result_page_count = 2
        window.original_current_page = 1
        window.result_current_page = 1
        window.legend_sidebar_collapsed = False
        window.result_path = result_path or Path("unused.pdf")
        window._page_canvases = {
            page: tk.Canvas(self._root, width=600, height=800) for page in (1, 2)
        }
        window._page_zoom = {1: 1.0, 2: 1.0}
        window._overlay_ids = {}
        window.ai_review = _review_data(*suggestions)
        return window

    @staticmethod
    def _dashed_outlines(window, page: int) -> list[tuple[float, ...]]:
        canvas = window._page_canvases[page]
        found = []
        for item_id in window._overlay_ids.get(page, []):
            if canvas.itemcget(item_id, "dash") and (
                canvas.itemcget(item_id, "outline") == AI_SUGGESTION_OUTLINE_COLOR
            ):
                found.append(tuple(canvas.coords(item_id)))
        return found


class AiReviewDecisionTests(AiReviewWindowTestBase):
    def test_accepting_a_missed_redaction_stages_its_proposed_rect_as_ai_labeled(self) -> None:
        window = self._build_window(MISSED, NARRATIVE)
        window._start_ai_review()
        self.assertEqual(window._ai_current_id, MISSED.id)

        window._accept_ai_suggestion()

        self.assertEqual(len(window.pending_add_rects), 1)
        rect = window.pending_add_rects[0]
        self.assertEqual(rect.label, AI_SUGGESTION_LABEL)
        self.assertEqual((rect.page, rect.x0, rect.y0, rect.x1, rect.y1), (1, 72.0, 60.0, 200.0, 75.0))
        self.assertEqual(window._ai_status(MISSED.id), AI_SUGGESTION_STATUS_ACCEPTED)
        # Word-style: moves straight on to the next undecided suggestion.
        self.assertEqual(window._ai_current_id, NARRATIVE.id)

    def test_undo_puts_an_accepted_suggestion_back_to_pending_and_redo_reaccepts(self) -> None:
        window = self._build_window(MISSED)
        window._start_ai_review()
        window._accept_ai_suggestion()

        window._undo_last_edit()
        self.assertEqual(window.pending_add_rects, [])
        self.assertEqual(window._ai_status(MISSED.id), AI_SUGGESTION_STATUS_PENDING)

        window._redo_last_edit()
        self.assertEqual(window._ai_status(MISSED.id), AI_SUGGESTION_STATUS_ACCEPTED)

    def test_erasing_the_staged_rect_by_hand_also_reverts_the_suggestion(self) -> None:
        window = self._build_window(MISSED)
        window._start_ai_review()
        window._accept_ai_suggestion()

        window._erase_at_point(100, 65, 1)

        self.assertEqual(window.pending_add_rects, [])
        self.assertEqual(window._ai_status(MISSED.id), AI_SUGGESTION_STATUS_PENDING)

    def test_rejecting_is_a_pending_change_that_undo_and_cancel_revert(self) -> None:
        window = self._build_window(MISSED, NARRATIVE)
        window._start_ai_review()

        window._reject_ai_suggestion()

        self.assertEqual(window._ai_status(MISSED.id), AI_SUGGESTION_STATUS_REJECTED)
        self.assertTrue(window._has_pending_changes())
        self.assertFalse(window._has_pending_document_changes())
        self.assertEqual(window._pending_change_count(), 1)

        window._undo_last_edit()
        self.assertEqual(window._ai_status(MISSED.id), AI_SUGGESTION_STATUS_PENDING)
        self.assertFalse(window._has_pending_changes())

        window._redo_last_edit()
        window._cancel_pending_changes()
        self.assertEqual(window._ai_status(MISSED.id), AI_SUGGESTION_STATUS_PENDING)

    def test_undo_ai_decision_only_takes_back_that_one_suggestion(self) -> None:
        window = self._build_window(MISSED, MISSED_PAGE_2)
        window._start_ai_review()
        window._accept_ai_suggestion()  # MISSED, moves on to MISSED_PAGE_2
        window._accept_ai_suggestion()  # MISSED_PAGE_2
        window._focus_ai_suggestion(MISSED.id)

        window._undo_ai_decision()

        self.assertEqual(window._ai_status(MISSED.id), AI_SUGGESTION_STATUS_PENDING)
        self.assertEqual(window._ai_status(MISSED_PAGE_2.id), AI_SUGGESTION_STATUS_ACCEPTED)
        self.assertEqual([rect.page for rect in window.pending_add_rects], [2])

    def test_unnecessary_redaction_stages_removal_of_redactions_inside_its_sentence(self) -> None:
        window = self._build_window(UNNECESSARY)
        window._start_ai_review()

        window._accept_ai_suggestion()

        self.assertEqual(
            window.pending_remove_keys, {rect_info_key(REDACTION_IN_UNNECESSARY_AREA)}
        )
        self.assertNotIn(rect_info_key(UNRELATED_REDACTION), window.pending_remove_keys)
        self.assertEqual(window._ai_status(UNNECESSARY.id), AI_SUGGESTION_STATUS_ACCEPTED)

    def test_unnecessary_redaction_with_nothing_to_unredact_falls_back_to_the_eraser(
        self,
    ) -> None:
        window = self._build_window(UNNECESSARY)
        window.visible_rects = [dict(UNRELATED_REDACTION)]
        window._start_ai_review()

        window._accept_ai_suggestion()
        self.assertEqual(window._ai_manual_id, UNNECESSARY.id)
        self.assertEqual(window._ai_status(UNNECESSARY.id), AI_SUGGESTION_STATUS_PENDING)

        # Erasing by hand while in that mode counts as accepting it.
        window._erase_at_point(100, 405, 1)
        self.assertEqual(window._ai_status(UNNECESSARY.id), AI_SUGGESTION_STATUS_ACCEPTED)

    def test_drawing_during_the_eraser_fallback_does_not_accept_unnecessary_redaction(
        self,
    ) -> None:
        # Review finding: a mark-drag there used to add a turquoise AI
        # redaction and count as accepting "this redaction is unnecessary".
        window = self._build_window(UNNECESSARY)
        window.visible_rects = [dict(UNRELATED_REDACTION)]
        window._start_ai_review()
        window._accept_ai_suggestion()
        self.assertEqual(window._ai_manual_id, UNNECESSARY.id)

        window._on_pane_button_press(types.SimpleNamespace(x=80, y=100, x_root=80, y_root=100), 1, "left")
        window._on_pane_button_release(
            types.SimpleNamespace(x=180, y=116, x_root=180, y_root=116), 1, "left"
        )

        self.assertEqual(len(window.pending_add_rects), 1)
        self.assertEqual(window.pending_add_rects[0].label, MANUAL_REDACTION_LABEL)
        self.assertEqual(window._ai_status(UNNECESSARY.id), AI_SUGGESTION_STATUS_PENDING)

    def test_narrative_accept_means_marking_by_hand_and_the_drawn_rect_is_ai_labeled(
        self,
    ) -> None:
        window = self._build_window(NARRATIVE)
        window._start_ai_review()

        window._accept_ai_suggestion()
        self.assertEqual(window.pending_add_rects, [])
        self.assertEqual(window._ai_manual_id, NARRATIVE.id)

        window._on_pane_button_press(types.SimpleNamespace(x=80, y=90, x_root=80, y_root=90), 2, "left")
        window._on_pane_button_release(
            types.SimpleNamespace(x=180, y=106, x_root=180, y_root=106), 2, "left"
        )

        self.assertEqual(len(window.pending_add_rects), 1)
        self.assertEqual(window.pending_add_rects[0].label, AI_SUGGESTION_LABEL)
        self.assertEqual(window._ai_status(NARRATIVE.id), AI_SUGGESTION_STATUS_ACCEPTED)

        window._exit_ai_manual_mode()
        window._on_pane_button_press(types.SimpleNamespace(x=80, y=300, x_root=80, y_root=300), 2, "left")
        window._on_pane_button_release(
            types.SimpleNamespace(x=180, y=320, x_root=180, y_root=320), 2, "left"
        )
        # Outside manual mode a drawn rect is an ordinary magic-pen one.
        self.assertEqual(window.pending_add_rects[-1].label, MANUAL_REDACTION_LABEL)

    def test_change_manually_narrows_a_proposal_instead_of_taking_it_whole(self) -> None:
        window = self._build_window(MISSED)
        window._start_ai_review()

        window._edit_ai_suggestion_manually()
        window._on_pane_button_press(types.SimpleNamespace(x=72, y=60, x_root=72, y_root=60), 1, "left")
        window._on_pane_button_release(
            types.SimpleNamespace(x=120, y=75, x_root=120, y_root=75), 1, "left"
        )

        self.assertEqual(len(window.pending_add_rects), 1)
        self.assertEqual(window.pending_add_rects[0].x1, 120)
        self.assertEqual(window._ai_status(MISSED.id), AI_SUGGESTION_STATUS_ACCEPTED)

    def test_apply_all_only_touches_suggestions_with_a_ready_rect_after_confirmation(
        self,
    ) -> None:
        window = self._build_window(MISSED, UNNECESSARY, NARRATIVE, MISSED_PAGE_2)

        with patch("gui_comparison_window.messagebox.askyesno", return_value=False) as ask:
            window._apply_all_ai_suggestions()
        self.assertIn("AI może się mylić", ask.call_args.args[1])
        self.assertEqual(window.pending_add_rects, [])

        with patch("gui_comparison_window.messagebox.askyesno", return_value=True):
            window._apply_all_ai_suggestions()

        self.assertEqual(window._ai_status(MISSED.id), AI_SUGGESTION_STATUS_ACCEPTED)
        self.assertEqual(window._ai_status(MISSED_PAGE_2.id), AI_SUGGESTION_STATUS_ACCEPTED)
        self.assertEqual(window._ai_status(UNNECESSARY.id), AI_SUGGESTION_STATUS_PENDING)
        self.assertEqual(window._ai_status(NARRATIVE.id), AI_SUGGESTION_STATUS_PENDING)
        self.assertEqual(window.pending_remove_keys, set())
        # One undo step takes the whole batch back.
        window._undo_last_edit()
        self.assertEqual(window.pending_add_rects, [])

    def test_navigation_wraps_in_both_directions(self) -> None:
        window = self._build_window(MISSED, UNNECESSARY, NARRATIVE)
        window._start_ai_review()
        window._step_ai_suggestion(-1)
        self.assertEqual(window._ai_current_id, NARRATIVE.id)
        window._step_ai_suggestion(1)
        self.assertEqual(window._ai_current_id, MISSED.id)


class AiReviewOverlayTests(AiReviewWindowTestBase):
    def test_pending_proposals_get_a_dashed_outline_and_accepted_ones_lose_it(self) -> None:
        window = self._build_window(MISSED, NARRATIVE)
        window._redraw_all_overlays()
        self.assertEqual(len(self._dashed_outlines(window, 1)), 1)
        # A narrative suggestion has no proposal: its location hint only
        # shows while it is the focused one.
        self.assertEqual(self._dashed_outlines(window, 2), [])

        window._start_ai_review()
        window._accept_ai_suggestion()  # focus moves to NARRATIVE

        self.assertEqual(self._dashed_outlines(window, 1), [])
        self.assertEqual(len(self._dashed_outlines(window, 2)), 1)
        canvas = window._page_canvases[1]
        staged_outlines = [
            canvas.itemcget(item_id, "outline")
            for item_id in window._overlay_ids[1]
            if canvas.itemcget(item_id, "fill") == "#111827"
        ]
        self.assertEqual(staged_outlines, [AI_SUGGESTION_OUTLINE_COLOR])

    def test_outline_follows_the_page_zoom(self) -> None:
        window = self._build_window(MISSED)
        window._page_zoom[1] = 2.0
        window._redraw_all_overlays()
        (coords,) = self._dashed_outlines(window, 1)
        self.assertEqual(coords, (142.0, 118.0, 402.0, 152.0))

    def test_rejected_suggestion_disappears(self) -> None:
        window = self._build_window(MISSED)
        window._start_ai_review()
        window._reject_ai_suggestion()
        self.assertEqual(self._dashed_outlines(window, 1), [])

    def test_review_panel_builds_in_every_state(self) -> None:
        window = self._build_window(MISSED, UNNECESSARY, NARRATIVE)
        parent = ctk.CTkFrame(self._root)
        window._build_ai_review_section(parent)
        window._build_ai_review_title_button(parent)
        self.assertIn("(3)", window._ai_title_button.cget("text"))

        window._start_ai_review()
        window._accept_ai_suggestion()
        window._reject_ai_suggestion()
        window._accept_ai_suggestion()  # narrative -> manual mode panel
        window._focus_ai_suggestion(MISSED.id)
        window._close_ai_review()
        self.assertIn("(1)", window._ai_title_button.cget("text"))
        window.ai_review = window.ai_review._replace(text_matched=False, suggestions=[])
        window._refresh_ai_review_ui()
        self.assertTrue(window._ai_section.winfo_children())


class AiReviewSaveTests(AiReviewWindowTestBase):
    def _write_sidecar(self, temp_path: Path) -> Path:
        result_path = temp_path / "doc_ANON_VISUAL.pdf"
        result_path.write_bytes(b"%PDF-1.4 placeholder")
        comparison = {
            "status": "completed",
            "findings": [
                {"finding_type": "missed_redaction", "sentence_index": 1},
                {"finding_type": "unnecessary_redaction", "sentence_index": 2},
                {"finding_type": "missed_redaction", "sentence_index": 4},
            ],
        }
        narrative = {"status": "completed", "suggestions": [{"sentence_indices": [3]}]}
        save_llm_suggestions_result(
            llm_suggestions_path(result_path),
            comparison_result=comparison,
            narrative_result=narrative,
            original_text="x",
        )
        return result_path

    def test_rejection_only_save_persists_decisions_without_regenerating_the_pdf(self) -> None:
        with workspace_temp_dir() as temp_dir:
            result_path = self._write_sidecar(Path(temp_dir))
            window = self._build_window(MISSED, NARRATIVE, result_path=result_path)
            window.source_path = Path(temp_dir) / "source.pdf"
            window._start_ai_review()
            window._reject_ai_suggestion()

            with patch.object(
                ComparisonWindow, "_regenerate_with_pending_edits", side_effect=AssertionError
            ):
                window._save_pending_changes()

            sidecar = load_llm_suggestions_sidecar(llm_suggestions_path(result_path))
            self.assertEqual(dict(sidecar.resolved), {MISSED.id: AI_SUGGESTION_STATUS_REJECTED})
            self.assertEqual([s.id for s in window.ai_review.suggestions], [NARRATIVE.id])
            self.assertFalse(window._has_pending_changes())

    def test_document_save_persists_accepted_and_rejected_after_regenerating(self) -> None:
        with workspace_temp_dir() as temp_dir:
            result_path = self._write_sidecar(Path(temp_dir))
            window = self._build_window(MISSED, NARRATIVE, result_path=result_path)
            window.source_path = Path(temp_dir) / "source.pdf"
            window._start_ai_review()
            window._accept_ai_suggestion()
            window._reject_ai_suggestion()

            regenerated = []

            def fake_regenerate(self_window):
                regenerated.append(list(self_window.pending_add_rects))
                return True

            with patch.object(
                ComparisonWindow, "_regenerate_with_pending_edits", fake_regenerate
            ), patch.object(ComparisonWindow, "_reload_visible_rects"), patch.object(
                ComparisonWindow, "_reload_pdf_pane"
            ), patch.object(ComparisonWindow, "_patch_report_with_manual_count"):
                window._save_pending_changes()

            self.assertEqual(len(regenerated), 1)
            self.assertEqual(regenerated[0][0].label, AI_SUGGESTION_LABEL)
            sidecar = load_llm_suggestions_sidecar(llm_suggestions_path(result_path))
            self.assertEqual(
                dict(sidecar.resolved),
                {
                    MISSED.id: AI_SUGGESTION_STATUS_ACCEPTED,
                    NARRATIVE.id: AI_SUGGESTION_STATUS_REJECTED,
                },
            )
            self.assertEqual(window.ai_review.suggestions, [])
            self.assertEqual(window.pending_add_rects, [])
            self.assertFalse(window._has_pending_changes())

    def test_failed_regeneration_persists_no_decision(self) -> None:
        with workspace_temp_dir() as temp_dir:
            result_path = self._write_sidecar(Path(temp_dir))
            window = self._build_window(MISSED, result_path=result_path)
            window.source_path = Path(temp_dir) / "source.pdf"
            window._start_ai_review()
            window._accept_ai_suggestion()

            with patch.object(
                ComparisonWindow, "_regenerate_with_pending_edits", return_value=False
            ):
                window._save_pending_changes()

            sidecar = load_llm_suggestions_sidecar(llm_suggestions_path(result_path))
            self.assertEqual(dict(sidecar.resolved), {})
            self.assertEqual(window._ai_status(MISSED.id), AI_SUGGESTION_STATUS_ACCEPTED)


class PrepareAiReviewTests(unittest.TestCase):
    def _write_pdf(self, path: Path, pages: list[list[str]]) -> None:
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

    def test_builds_located_suggestions_in_reading_order_and_skips_resolved_ones(self) -> None:
        with workspace_temp_dir() as temp_dir:
            temp_path = Path(temp_dir)
            source_path = temp_path / "source.pdf"
            self._write_pdf(
                source_path,
                [["Jan Kowalski mieszka w Warszawie.", "Ma trzy koty."], ["Pracuje jako chirurg."]],
            )
            word_pages = word_pages_for_redaction_geometry(source_path)
            reviewed_text = candidate_llm_review_texts(source_path, word_pages)[0]
            result_path = temp_path / "source_ANON_VISUAL.pdf"
            sidecar_path = llm_suggestions_path(result_path)
            save_llm_suggestions_result(
                sidecar_path,
                comparison_result={
                    "status": "completed",
                    "findings": [
                        {"finding_type": "missed_redaction", "category": "PERSON_LIKE",
                         "sentence_index": 3, "justification": "a"},
                        {"finding_type": "missed_redaction", "category": "PERSON_LIKE",
                         "sentence_index": 1, "justification": "b"},
                        {"finding_type": "missed_redaction", "category": "PERSON_LIKE",
                         "sentence_index": 2, "justification": "c"},
                    ],
                },
                narrative_result={
                    "status": "completed",
                    "suggestions": [{"category": "QUASI_IDENTIFIER_COMBINATION",
                                     "confidence": "likely", "sentence_indices": [3],
                                     "justification": "d"}],
                },
                original_text=reviewed_text,
            )
            data = json.loads(sidecar_path.read_text(encoding="utf-8"))
            data["resolved"] = {"comparison-2": "rejected"}
            sidecar_path.write_text(json.dumps(data), encoding="utf-8")

            review = prepare_ai_review(result_path, source_path, word_pages)

            self.assertTrue(review.text_matched)
            self.assertEqual(
                [s.id for s in review.suggestions], ["comparison-1", "comparison-0", "narrative-0"]
            )
            self.assertEqual(review.sentence_texts["comparison-0"], ["Pracuje jako chirurg."])
            self.assertEqual(review.location_rects["narrative-0"][0]["page"], 2)
            self.assertTrue(review.suggestions[0].rects)

    def test_a_text_mismatch_keeps_every_suggestion_but_without_any_location(self) -> None:
        with workspace_temp_dir() as temp_dir:
            temp_path = Path(temp_dir)
            source_path = temp_path / "source.pdf"
            self._write_pdf(source_path, [["Jan Kowalski mieszka w Warszawie."]])
            result_path = temp_path / "source_ANON_VISUAL.pdf"
            save_llm_suggestions_result(
                llm_suggestions_path(result_path),
                comparison_result={
                    "status": "completed",
                    "findings": [{"finding_type": "missed_redaction", "sentence_index": 1}],
                },
                narrative_result=None,
                original_text="Zupełnie inny tekst, który czytało AI.",
            )
            review = prepare_ai_review(
                result_path, source_path, word_pages_for_redaction_geometry(source_path)
            )

            self.assertFalse(review.text_matched)
            self.assertEqual(len(review.suggestions), 1)
            self.assertIsNone(review.suggestions[0].page)
            self.assertEqual(review.suggestions[0].rects, ())
            self.assertEqual(review.location_rects["comparison-0"], [])
            self.assertEqual(review.sentence_texts["comparison-0"], [])

    def test_an_unreadable_source_degrades_to_no_location_instead_of_raising(self) -> None:
        # Review finding: pypdf's own errors aren't OSError/ValueError and
        # used to escape, so the comparison window failed to open at all.
        from pypdf.errors import PdfReadError

        with workspace_temp_dir() as temp_dir:
            temp_path = Path(temp_dir)
            result_path = temp_path / "x_ANON_VISUAL.pdf"
            save_llm_suggestions_result(
                llm_suggestions_path(result_path),
                comparison_result={
                    "status": "completed",
                    "findings": [{"finding_type": "missed_redaction", "sentence_index": 1}],
                },
                narrative_result=None,
                original_text="Jan Kowalski.",
            )
            with patch(
                "gui_comparison_window.candidate_llm_review_texts",
                side_effect=PdfReadError("broken"),
            ):
                review = prepare_ai_review(result_path, temp_path / "x.pdf", [])

            self.assertFalse(review.text_matched)
            self.assertEqual([s.id for s in review.suggestions], ["comparison-0"])

    def test_no_sidecar_means_no_review(self) -> None:
        with workspace_temp_dir() as temp_dir:
            review = prepare_ai_review(
                Path(temp_dir) / "x_ANON_VISUAL.pdf", Path(temp_dir) / "x.pdf", []
            )
            self.assertEqual(review.suggestions, [])


class PureHelperTests(unittest.TestCase):
    def test_scroll_fraction_puts_the_target_a_third_down_the_viewport(self) -> None:
        # Page 2 starts 1000px in, target 300px into it, 600px viewport:
        # top of view = 1000 + 300 - 180 = 1120 of 4000.
        self.assertAlmostEqual(ai_scroll_fraction(1000, 300, 4000, 600), 1120 / 4000)
        self.assertEqual(ai_scroll_fraction(0, 10, 4000, 600), 0.0)
        self.assertEqual(ai_scroll_fraction(3900, 300, 4000, 600), 1.0)
        self.assertEqual(ai_scroll_fraction(10, 10, 0, 600), 0.0)

    def test_titles_and_quotes(self) -> None:
        self.assertEqual(ai_suggestion_title_pl(MISSED), "Możliwa pominięta dana: osoba")
        self.assertIn("zbędna", ai_suggestion_title_pl(UNNECESSARY))
        self.assertIn("prawdopodobne", ai_suggestion_title_pl(NARRATIVE))
        self.assertEqual(ai_quote_text(["Ala  ma\nkota.", "Kot ma Alę."]), "Ala ma kota. … Kot ma Alę.")
        long_quote = ai_quote_text(["x" * 500])
        self.assertEqual(len(long_quote), 160)
        self.assertTrue(long_quote.endswith("…"))


class ApprovalGateTests(unittest.TestCase):
    def _app(self, review_dir: Path, originals: dict[str, Path]):
        app = AnonymizerApp.__new__(AnonymizerApp)
        app.review_dir = review_dir
        app.original_path_by_output_name = originals
        app.root = None
        app.opened = []
        app.open_comparison = lambda item: app.opened.append(item.output_name)
        return app

    def _output_with_suggestions(self, review_dir: Path, base: str, count: int) -> ReviewItem:
        (review_dir / f"{base}_ANON.txt").write_text("x", encoding="utf-8")
        visual = review_dir / f"{base}_ANON_VISUAL.pdf"
        visual.write_bytes(b"%PDF-1.4 placeholder")
        if count:
            save_llm_suggestions_result(
                llm_suggestions_path(visual),
                comparison_result={
                    "status": "completed",
                    "findings": [{"sentence_index": 1}] * count,
                },
                narrative_result=None,
            )
        return ReviewItem(output_name=f"{base}_ANON.txt")

    def test_file_without_pending_suggestions_passes_straight_through(self) -> None:
        with workspace_temp_dir() as temp_dir:
            review_dir = Path(temp_dir)
            item = self._output_with_suggestions(review_dir, "a", 0)
            app = self._app(review_dir, {})
            with patch("gui_app.messagebox") as box:
                self.assertEqual(app._apply_ai_suggestion_gate([item]), [item])
            box.askyesno.assert_not_called()

    def test_single_reviewable_file_is_blocked_and_offers_the_comparison(self) -> None:
        with workspace_temp_dir() as temp_dir:
            review_dir = Path(temp_dir)
            item = self._output_with_suggestions(review_dir, "a", 2)
            source = review_dir / "a.pdf"
            source.write_bytes(b"%PDF")
            app = self._app(review_dir, {item.output_name: source})
            with patch("gui_app.messagebox.askyesno", return_value=True) as ask:
                self.assertEqual(app._apply_ai_suggestion_gate([item]), [])
            self.assertIn("2", ask.call_args.args[1])
            self.assertEqual(app.opened, [item.output_name])

    def test_unreviewable_file_needs_an_explicit_approve_anyway(self) -> None:
        with workspace_temp_dir() as temp_dir:
            review_dir = Path(temp_dir)
            item = self._output_with_suggestions(review_dir, "a", 1)
            app = self._app(review_dir, {})
            with patch("gui_app.messagebox.askyesno", return_value=False):
                self.assertEqual(app._apply_ai_suggestion_gate([item]), [])
            with patch("gui_app.messagebox.askyesno", return_value=True) as ask:
                self.assertEqual(app._apply_ai_suggestion_gate([item]), [item])
            self.assertIn("mimo to", ask.call_args.args[1])

    def test_bulk_approve_holds_back_only_the_files_that_need_review(self) -> None:
        with workspace_temp_dir() as temp_dir:
            review_dir = Path(temp_dir)
            clean = self._output_with_suggestions(review_dir, "clean", 0)
            pending = self._output_with_suggestions(review_dir, "pending", 3)
            source = review_dir / "pending.pdf"
            source.write_bytes(b"%PDF")
            app = self._app(review_dir, {pending.output_name: source})
            with patch("gui_app.messagebox.showwarning") as warn:
                self.assertEqual(app._apply_ai_suggestion_gate([clean, pending]), [clean])
            self.assertIn("pending_ANON.txt", warn.call_args.args[1])


if __name__ == "__main__":
    unittest.main()
