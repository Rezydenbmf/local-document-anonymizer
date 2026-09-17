"""Tests for the pilot-feedback-round-4 magic pen visibility fixes (see
docs/PROJECT_STATE.md): the undo/redo buttons recoloring on enable, the
per-button mode-indicator badges, and the idle/live document cursor
reflecting what each mouse button currently does. Same bare-instance
approach as test_comparison_window_mouse_dispatch.py - a real Tk/CTk
root and real widgets, but no full window chrome.
"""

import sys
import types
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import tkinter as tk

import customtkinter as ctk

from gui_comparison_window import ComparisonWindow
from gui_helpers import (
    COLOR_ACCENT,
    COLOR_BORDER,
    COLOR_TEXT_MUTED,
    MAGIC_PEN_BUILTIN_BINDINGS,
    MAGIC_PEN_MODE_CLASSIC,
    MAGIC_PEN_MODE_CUSTOM,
    MAGIC_PEN_MODE_DEFAULT,
)
from manual_redaction import EMPTY_MANUAL_EDITS


def _event(x, y):
    return types.SimpleNamespace(x=x, y=y, x_root=x, y_root=y)


class FakeApp:
    def __init__(self, mode=MAGIC_PEN_MODE_DEFAULT, custom_bindings=None):
        self.magic_pen_interaction_mode = mode
        self.magic_pen_custom_bindings = (
            custom_bindings
            if custom_bindings is not None
            else dict(MAGIC_PEN_BUILTIN_BINDINGS[MAGIC_PEN_MODE_DEFAULT])
        )


class MagicPenVisualsTests(unittest.TestCase):
    _root = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._root = ctk.CTk()
        cls._root.withdraw()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._root.destroy()

    def _build_window(self, *, mode=MAGIC_PEN_MODE_DEFAULT, custom_bindings=None, locked=False):
        window = ComparisonWindow.__new__(ComparisonWindow)
        window.app = FakeApp(mode=mode, custom_bindings=custom_bindings)
        window.locked = locked
        window.edits = EMPTY_MANUAL_EDITS
        window.visible_rects = [
            {"page": 1, "label": "EMAIL", "x0": 10, "y0": 10, "x1": 100, "y1": 30},
        ]
        window.pending_add_rects = []
        window.pending_remove_keys = set()
        window._drag_start = None
        window._drag_rect_id = None
        window._active_gesture_action = None
        window._erased_this_gesture = set()

        window.undo_button = ctk.CTkButton(self._root, text="↶")
        window.redo_button = ctk.CTkButton(self._root, text="↷")
        window._edit_undo_stack = []
        window._edit_redo_stack = []

        window.mode_indicator_frame = ctk.CTkFrame(self._root, fg_color="transparent")

        window.right_frame = ctk.CTkScrollableFrame(self._root, width=100, height=100)
        window.right_frame.pack()
        canvas = tk.Canvas(window.right_frame, width=100, height=100)
        canvas.pack()
        window._page_canvases = {1: canvas}
        window._page_zoom = {1: 1.0}
        window._overlay_ids = {}
        self._root.update_idletasks()
        return window

    # -- undo/redo recoloring -------------------------------------------

    def test_undo_redo_start_muted_when_stacks_are_empty(self) -> None:
        window = self._build_window()
        window._update_undo_redo_buttons()
        self.assertEqual(window.undo_button.cget("state"), "disabled")
        self.assertEqual(window.undo_button.cget("border_color"), COLOR_BORDER)
        self.assertEqual(window.undo_button.cget("text_color"), COLOR_TEXT_MUTED)

    def test_undo_recolors_and_enables_once_something_is_undoable(self) -> None:
        window = self._build_window()
        window._edit_undo_stack = [{"kind": "add"}]
        window._update_undo_redo_buttons()
        self.assertEqual(window.undo_button.cget("state"), "normal")
        self.assertEqual(window.undo_button.cget("border_color"), COLOR_ACCENT)
        self.assertEqual(window.undo_button.cget("text_color"), COLOR_ACCENT)

    def test_redo_reverts_to_muted_once_its_stack_empties_again(self) -> None:
        window = self._build_window()
        window._edit_redo_stack = [{"kind": "add"}]
        window._update_undo_redo_buttons()
        self.assertEqual(window.redo_button.cget("state"), "normal")

        window._edit_redo_stack = []
        window._update_undo_redo_buttons()
        self.assertEqual(window.redo_button.cget("state"), "disabled")
        self.assertEqual(window.redo_button.cget("border_color"), COLOR_BORDER)

    # -- mode-indicator badges -------------------------------------------

    def test_default_mode_produces_one_badge_per_button(self) -> None:
        window = self._build_window(mode=MAGIC_PEN_MODE_DEFAULT)
        window._populate_mode_indicator(window.mode_indicator_frame)
        badges = window.mode_indicator_frame.winfo_children()
        self.assertEqual(len(badges), 3)

    def test_repopulating_replaces_old_badges_instead_of_stacking(self) -> None:
        window = self._build_window(mode=MAGIC_PEN_MODE_DEFAULT)
        window._populate_mode_indicator(window.mode_indicator_frame)
        window._populate_mode_indicator(window.mode_indicator_frame)
        self.assertEqual(len(window.mode_indicator_frame.winfo_children()), 3)

    def test_custom_mode_badges_reflect_the_apps_custom_bindings(self) -> None:
        custom = {"left": "erase", "right": "mark", "middle": "pan"}
        window = self._build_window(mode=MAGIC_PEN_MODE_CUSTOM, custom_bindings=custom)
        window._populate_mode_indicator(window.mode_indicator_frame)
        # One label per badge frame, carrying the short button code and
        # an action icon - just assert every badge got real text, since
        # the exact icon glyphs are a presentation detail, not a contract.
        badge_texts = [
            badge.winfo_children()[0].cget("text")
            for badge in window.mode_indicator_frame.winfo_children()
        ]
        self.assertEqual(len(badge_texts), 3)
        self.assertTrue(all(text.strip() for text in badge_texts))

    # -- document cursor ---------------------------------------------------

    def test_idle_cursor_follows_left_buttons_action_in_default_mode(self) -> None:
        window = self._build_window(mode=MAGIC_PEN_MODE_DEFAULT)
        self.assertEqual(window._idle_magic_pen_cursor(), "pencil")  # left = mark

    def test_idle_cursor_follows_left_buttons_action_in_classic_mode(self) -> None:
        window = self._build_window(mode=MAGIC_PEN_MODE_CLASSIC)
        self.assertEqual(window._idle_magic_pen_cursor(), "pencil")  # left = mark

    def test_idle_cursor_is_arrow_for_a_locked_file(self) -> None:
        window = self._build_window(mode=MAGIC_PEN_MODE_DEFAULT, locked=True)
        self.assertEqual(window._idle_magic_pen_cursor(), "arrow")

    def test_custom_mode_idle_cursor_follows_whatever_left_does(self) -> None:
        custom = {"left": "pan", "right": "mark", "middle": "erase"}
        window = self._build_window(mode=MAGIC_PEN_MODE_CUSTOM, custom_bindings=custom)
        self.assertEqual(window._idle_magic_pen_cursor(), "hand2")

    def test_pressing_a_button_updates_the_canvas_cursor_to_its_own_action(self) -> None:
        window = self._build_window(mode=MAGIC_PEN_MODE_DEFAULT)
        canvas = window._page_canvases[1]

        # A point nowhere near the fixture's one rect - the cursor swap
        # happens unconditionally at press time, before the erase hit
        # test, so this only needs "middle" to resolve to erase, not an
        # actual hit.
        window._on_pane_button_press(_event(500, 500), 1, "middle")  # middle = erase

        self.assertEqual(canvas.cget("cursor"), "X_cursor")

    def test_releasing_restores_the_idle_left_button_cursor(self) -> None:
        window = self._build_window(mode=MAGIC_PEN_MODE_DEFAULT)
        canvas = window._page_canvases[1]

        window._on_pane_button_press(_event(10, 10), 1, "right")  # right = pan
        self.assertEqual(canvas.cget("cursor"), "hand2")
        window._on_pane_button_release(_event(10, 10), 1, "right")

        self.assertEqual(canvas.cget("cursor"), window._idle_magic_pen_cursor())

    # -- refresh after Ustawienia closes -----------------------------------

    def test_refresh_rebuilds_badges_and_resets_canvas_cursors_for_new_mode(self) -> None:
        window = self._build_window(mode=MAGIC_PEN_MODE_DEFAULT)
        window._populate_mode_indicator(window.mode_indicator_frame)
        canvas = window._page_canvases[1]
        canvas.configure(cursor="tcross")

        # Simulate the user switching to classic mode via Ustawienia,
        # then this window's own on_saved callback firing.
        window.app.magic_pen_interaction_mode = MAGIC_PEN_MODE_CLASSIC
        window._refresh_magic_pen_mode()

        self.assertEqual(len(window.mode_indicator_frame.winfo_children()), 3)
        self.assertEqual(canvas.cget("cursor"), window._idle_magic_pen_cursor())

    def test_refresh_skips_canvas_cursor_reset_for_a_locked_file(self) -> None:
        window = self._build_window(mode=MAGIC_PEN_MODE_DEFAULT, locked=True)
        canvas = window._page_canvases[1]
        canvas.configure(cursor="arrow")

        window._refresh_magic_pen_mode()

        self.assertEqual(canvas.cget("cursor"), "arrow")


if __name__ == "__main__":
    unittest.main()
