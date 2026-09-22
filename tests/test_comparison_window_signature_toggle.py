"""Tests for the magic-pen signature-removal toggle (Etap 7 follow-up,
2026-09-22): letting the user flip "Usuń podpisy elektroniczne" from
inside ComparisonWindow, not only once at pre-anonymization time.
Exercises the plain-Python pending-state bookkeeping directly against a
bare instance (via __new__, bypassing Tk widget construction), since
none of this logic touches the GUI - see
test_comparison_window_detection_cache.py for the same pattern.
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gui_comparison_window import ComparisonWindow


def make_bare_window(
    *, original_strip_signatures: bool = False
) -> ComparisonWindow:
    window = ComparisonWindow.__new__(ComparisonWindow)
    window.pending_add_rects = []
    window.pending_remove_keys = set()
    window._original_strip_signatures = original_strip_signatures
    window._current_strip_signatures = original_strip_signatures
    window._strip_signatures_var = None
    window.save_button = None
    window.pen_status_label = None
    window._floating_actions = None
    window._edits_saved = False
    window._edit_undo_stack = []
    window._edit_redo_stack = []
    window.undo_button = None
    window.redo_button = None
    window._page_canvases = {}
    return window


class HasPendingChangesSignatureAwarenessTests(unittest.TestCase):
    def test_no_pending_changes_when_nothing_touched(self) -> None:
        window = make_bare_window()
        self.assertFalse(window._has_pending_changes())

    def test_signature_toggle_alone_counts_as_a_pending_change(self) -> None:
        window = make_bare_window(original_strip_signatures=False)
        window._current_strip_signatures = True
        self.assertTrue(window._has_pending_changes())

    def test_toggling_back_to_original_clears_pending_state(self) -> None:
        window = make_bare_window(original_strip_signatures=True)
        window._current_strip_signatures = False
        self.assertTrue(window._has_pending_changes())
        window._current_strip_signatures = True
        self.assertFalse(window._has_pending_changes())


class PendingChangeCountTests(unittest.TestCase):
    def test_signature_toggle_alone_counts_as_one(self) -> None:
        window = make_bare_window(original_strip_signatures=False)
        window._current_strip_signatures = True
        self.assertEqual(window._pending_change_count(), 1)

    def test_rect_edits_and_signature_toggle_both_count(self) -> None:
        window = make_bare_window(original_strip_signatures=False)
        window._current_strip_signatures = True
        window.pending_remove_keys = {"a", "b"}
        self.assertEqual(window._pending_change_count(), 3)

    def test_unchanged_signature_does_not_inflate_the_count(self) -> None:
        window = make_bare_window(original_strip_signatures=True)
        window.pending_add_rects = [object()]
        self.assertEqual(window._pending_change_count(), 1)


class CancelPendingChangesResetsSignatureToggleTests(unittest.TestCase):
    def test_cancel_reverts_current_to_original(self) -> None:
        window = make_bare_window(original_strip_signatures=False)
        window._current_strip_signatures = True

        window._cancel_pending_changes()

        self.assertFalse(window._current_strip_signatures)
        self.assertFalse(window._has_pending_changes())


if __name__ == "__main__":
    unittest.main()
