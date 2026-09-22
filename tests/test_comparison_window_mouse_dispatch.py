"""Tests for ComparisonWindow's mode-driven mouse-button dispatch (Etap 3
- see docs/PROJECT_STATE.md). Drives the plain-Python handler methods
directly against a bare instance (via __new__, real Tk canvases but no
full window chrome), since none of this dispatch logic needs the rest of
the widget tree to be built.
"""

import sys
import types
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import customtkinter as ctk
import tkinter as tk

from gui_comparison_window import ComparisonWindow
from gui_helpers import (
    MAGIC_PEN_BUILTIN_BINDINGS,
    MAGIC_PEN_MODE_CLASSIC,
    MAGIC_PEN_MODE_CUSTOM,
    MAGIC_PEN_MODE_DEFAULT,
)
from manual_redaction import EMPTY_MANUAL_EDITS


def _event(x, y, x_root=None, y_root=None):
    return types.SimpleNamespace(
        x=x,
        y=y,
        x_root=x_root if x_root is not None else x,
        y_root=y_root if y_root is not None else y,
    )


class FakeApp:
    def __init__(self, mode=MAGIC_PEN_MODE_DEFAULT, custom_bindings=None):
        self.magic_pen_interaction_mode = mode
        self.magic_pen_custom_bindings = (
            custom_bindings
            if custom_bindings is not None
            else dict(MAGIC_PEN_BUILTIN_BINDINGS[MAGIC_PEN_MODE_DEFAULT])
        )


class ComparisonWindowMouseDispatchTests(unittest.TestCase):
    """One shared hidden root per test-run rather than per test: building
    a real Tk/CTk root is the slow part, and nothing here depends on a
    fresh one - each test builds its own bare window/canvas instead."""

    _root = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._root = ctk.CTk()
        cls._root.withdraw()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._root.destroy()

    def _build_window(self, *, mode=MAGIC_PEN_MODE_DEFAULT, custom_bindings=None):
        window = ComparisonWindow.__new__(ComparisonWindow)
        window.app = FakeApp(mode=mode, custom_bindings=custom_bindings)
        window.locked = False
        window.edits = EMPTY_MANUAL_EDITS
        window.visible_rects = [
            {"page": 1, "label": "EMAIL", "x0": 10, "y0": 10, "x1": 100, "y1": 30},
            {"page": 1, "label": "PESEL", "x0": 10, "y0": 40, "x1": 100, "y1": 60},
        ]
        window.pending_add_rects = []
        window.pending_remove_keys = set()
        window._drag_start = None
        window._drag_rect_id = None
        window._active_gesture_action = None
        window._erased_this_gesture = set()
        window._edit_undo_stack = []
        window._edit_redo_stack = []
        window.undo_button = None
        window.redo_button = None
        window.save_button = None
        window.cancel_button = None
        window.finish_button = None
        window.pen_status_label = None
        window._floating_actions = None
        window._edits_saved = False
        window._original_strip_signatures = False
        window._current_strip_signatures = False

        window.right_frame = ctk.CTkScrollableFrame(self._root, width=300, height=300)
        window.right_frame.pack()
        canvas = tk.Canvas(window.right_frame, width=300, height=300)
        canvas.pack()
        window._page_canvases = {1: canvas}
        window._page_zoom = {1: 1.0}
        window._overlay_ids = {}
        self._root.update_idletasks()
        return window

    def test_left_button_drag_marks_a_new_redaction_in_default_mode(self) -> None:
        window = self._build_window(mode=MAGIC_PEN_MODE_DEFAULT)

        window._on_pane_button_press(_event(150, 150), 1, "left")
        window._on_pane_button_drag(_event(200, 190), 1, "left")
        window._on_pane_button_release(_event(200, 190), 1, "left")

        self.assertEqual(len(window.pending_add_rects), 1)

    def test_right_button_pans_and_never_marks_or_erases_in_default_mode(self) -> None:
        window = self._build_window(mode=MAGIC_PEN_MODE_DEFAULT)

        window._on_pane_button_press(_event(50, 20), 1, "right")
        window._on_pane_button_drag(_event(80, 80), 1, "right")
        window._on_pane_button_release(_event(80, 80), 1, "right")

        self.assertEqual(window.pending_add_rects, [])
        self.assertEqual(window.pending_remove_keys, set())

    def test_middle_button_click_erases_the_rect_under_the_cursor_in_default_mode(
        self,
    ) -> None:
        window = self._build_window(mode=MAGIC_PEN_MODE_DEFAULT)

        window._on_pane_button_press(_event(50, 20), 1, "middle")
        window._on_pane_button_release(_event(50, 20), 1, "middle")

        self.assertEqual(len(window.pending_remove_keys), 1)

    def test_second_separate_erase_click_on_same_rect_toggles_it_back(self) -> None:
        window = self._build_window(mode=MAGIC_PEN_MODE_DEFAULT)

        window._on_pane_button_press(_event(50, 20), 1, "middle")
        window._on_pane_button_release(_event(50, 20), 1, "middle")
        window._on_pane_button_press(_event(50, 20), 1, "middle")
        window._on_pane_button_release(_event(50, 20), 1, "middle")

        self.assertEqual(window.pending_remove_keys, set())

    def test_drag_erase_removes_each_rect_once_even_when_gesture_revisits_it(
        self,
    ) -> None:
        window = self._build_window(mode=MAGIC_PEN_MODE_DEFAULT)

        window._on_pane_button_press(_event(50, 20), 1, "middle")
        window._on_pane_button_drag(_event(50, 50), 1, "middle")  # 2nd rect
        window._on_pane_button_drag(_event(50, 20), 1, "middle")  # back over 1st
        window._on_pane_button_release(_event(50, 20), 1, "middle")

        self.assertEqual(len(window.pending_remove_keys), 2)

    def test_classic_mode_right_button_erases_instead_of_panning(self) -> None:
        window = self._build_window(mode=MAGIC_PEN_MODE_CLASSIC)

        window._on_pane_button_press(_event(50, 20), 1, "right")
        window._on_pane_button_release(_event(50, 20), 1, "right")

        self.assertEqual(len(window.pending_remove_keys), 1)

    def test_classic_mode_middle_button_pans_instead_of_erasing(self) -> None:
        window = self._build_window(mode=MAGIC_PEN_MODE_CLASSIC)

        window._on_pane_button_press(_event(50, 20), 1, "middle")
        window._on_pane_button_release(_event(50, 20), 1, "middle")

        self.assertEqual(window.pending_remove_keys, set())

    def test_locked_file_never_binds_but_dispatch_itself_is_unaffected(self) -> None:
        # _on_pane_button_press etc. don't check self.locked themselves -
        # the canvas simply never gets bound in the first place for a
        # locked file (see _build_magic_pen_pane) - documented here so a
        # future refactor doesn't assume the handler enforces it.
        window = self._build_window(mode=MAGIC_PEN_MODE_DEFAULT)
        window.locked = True

        window._on_pane_button_press(_event(150, 150), 1, "left")
        window._on_pane_button_drag(_event(200, 190), 1, "left")
        window._on_pane_button_release(_event(200, 190), 1, "left")

        self.assertEqual(len(window.pending_add_rects), 1)

    def test_custom_mode_uses_the_apps_custom_bindings(self) -> None:
        custom = {"left": "erase", "right": "mark", "middle": "pan"}
        window = self._build_window(mode=MAGIC_PEN_MODE_CUSTOM, custom_bindings=custom)

        window._on_pane_button_press(_event(50, 20), 1, "left")
        window._on_pane_button_release(_event(50, 20), 1, "left")
        self.assertEqual(len(window.pending_remove_keys), 1)

        window._on_pane_button_press(_event(150, 150), 1, "right")
        window._on_pane_button_drag(_event(200, 190), 1, "right")
        window._on_pane_button_release(_event(200, 190), 1, "right")
        self.assertEqual(len(window.pending_add_rects), 1)


if __name__ == "__main__":
    unittest.main()
