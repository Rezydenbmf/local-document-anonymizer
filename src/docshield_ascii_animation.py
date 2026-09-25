"""Framework-agnostic ASCII animation for DocShield's processing screen.

Integration API
---------------
Create ``DocShieldAsciiAnimation(document_count)`` and let the GUI redraw a
monospaced text widget from ``render_frame()`` on its own timer (roughly every
80-150 ms). Backend events control the animation through ``start_document()``,
``mark_current_completed()``, ``advance_to_next()``, and one of
``stop_success()``, ``stop_error()`` or ``cancel()``. ``request_cancel()``
only changes the status line while the current document is still finishing
(DocShield can stop a batch between files, not inside one).

The animation deliberately has no percentage. ``source_id`` is an opaque value
returned in snapshots for integration purposes and is never rendered. No text
from a real document is accepted or displayed; all visible document contents
below are fixed fictional constants.

Origin: prototype ``docshield_ascii_animation.py`` (2026-09-25), integrated
with the Polish status messages spelled with diacritics and the added
``request_cancel()``. Nothing here imports a GUI toolkit.
"""

from __future__ import annotations

import sys
import threading
import time
from collections.abc import Hashable
from dataclasses import dataclass
from enum import Enum


class AnimationState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    DOCUMENT_COMPLETED = "document_completed"
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"


TERMINAL_STATES = frozenset(
    {AnimationState.SUCCESS, AnimationState.ERROR, AnimationState.CANCELLED}
)


@dataclass(frozen=True)
class AnimationSnapshot:
    """Machine-readable state; safe for GUI control logic."""

    state: AnimationState
    document_number: int
    document_count: int
    source_id: Hashable | None
    is_terminal: bool


class DocShieldAsciiAnimation:
    """Generate complete, fixed-width text frames without owning a GUI timer."""

    FRAME_WIDTH = 64
    DOCUMENT_WIDTH = 48
    MASK = "█"

    MESSAGE_IDLE = "Gotowy"
    MESSAGE_RUNNING = "Analiza lokalna w toku"
    MESSAGE_DOCUMENT_COMPLETED = "Dokument zakończony"
    MESSAGE_SUCCESS = "Wszystkie dokumenty zakończone"
    MESSAGE_ERROR = "Przetwarzanie zatrzymane: błąd"
    MESSAGE_CANCEL_PENDING = "Anulowanie - kończę bieżący dokument"
    MESSAGE_CANCELLED = "Przetwarzanie anulowane"

    # Fixed demo data only. Never replace these strings with extracted content.
    _DOCUMENT_ROWS = (
        ".:/=+--*..::/=+*--..:/=+*..--::/=+*...",
        "::..//==++--**..:://==++--**..:://==++",
        "DANE: JAN KOWALSKI",
        "+=-:..//*+==--::..//*+==--::..//*+==--",
        "PESEL 82010112345",
        "..::==//**--++..::==//**--++..::==//**",
        "TEL. 501 234 567",
        "//--..::++==**//--..::++==**//--..::++",
        "ADRES: LESNA 14",
        "**++==--//::..**++==--//::..**++==--//",
        ".-+=/:*..-+=/:*..-+=/:*..-+=/:*..-+=/:",
    )
    _PRIVATE_FRAGMENTS = (
        "JAN KOWALSKI",
        "PESEL 82010112345",
        "TEL. 501 234 567",
        "ADRES: LESNA 14",
    )
    _SPINNER = ("|", "/", "-", "\\")

    def __init__(self, document_count: int, *, frame_interval: float = 0.10):
        if document_count < 1:
            raise ValueError("document_count must be at least 1")
        if frame_interval <= 0:
            raise ValueError("frame_interval must be positive")
        self.document_count = document_count
        self.frame_interval = frame_interval
        self._state = AnimationState.IDLE
        self._document_number = 0
        self._source_id: Hashable | None = None
        self._started_at = time.monotonic()
        self._message = self.MESSAGE_IDLE
        self._cancel_requested = False
        self._lock = threading.RLock()

    def start_document(self, source_id: Hashable | None = None) -> None:
        """Start animating the current/first item; source_id is never displayed."""
        with self._lock:
            if self._state in TERMINAL_STATES:
                raise RuntimeError("animation has already stopped")
            if self._document_number == 0:
                self._document_number = 1
            self._source_id = source_id
            self._state = AnimationState.RUNNING
            self._started_at = time.monotonic()
            self._message = self._running_message()

    def mark_current_completed(self) -> None:
        """Mark the current file complete; does not advance automatically."""
        with self._lock:
            self._require_current(AnimationState.RUNNING)
            self._state = AnimationState.DOCUMENT_COMPLETED
            self._message = self.MESSAGE_DOCUMENT_COMPLETED

    def advance_to_next(self, source_id: Hashable | None = None) -> None:
        """Advance after completion and start animation for the next real file."""
        with self._lock:
            self._require_current(AnimationState.DOCUMENT_COMPLETED)
            if self._document_number >= self.document_count:
                raise RuntimeError("there is no next document")
            self._document_number += 1
            self._source_id = source_id
            self._state = AnimationState.RUNNING
            self._started_at = time.monotonic()
            self._message = self._running_message()

    def request_cancel(self) -> None:
        """The user asked to cancel; the current document is still finishing.

        Only the status line changes - ``cancel()`` is still expected once
        processing has actually stopped."""
        with self._lock:
            if self._state in TERMINAL_STATES:
                return
            self._cancel_requested = True
            if self._state == AnimationState.RUNNING:
                self._message = self.MESSAGE_CANCEL_PENDING

    def stop_success(self) -> None:
        """Stop after the queue has completed successfully."""
        with self._lock:
            if self._state not in {
                AnimationState.RUNNING,
                AnimationState.DOCUMENT_COMPLETED,
            }:
                raise RuntimeError("no active queue")
            self._state = AnimationState.SUCCESS
            self._message = self.MESSAGE_SUCCESS

    def stop_error(self, _private_error: object | None = None) -> None:
        """Stop on failure. Error details are intentionally not rendered."""
        with self._lock:
            self._state = AnimationState.ERROR
            self._message = self.MESSAGE_ERROR

    def cancel(self) -> None:
        """Stop on user cancellation."""
        with self._lock:
            self._state = AnimationState.CANCELLED
            self._message = self.MESSAGE_CANCELLED

    def snapshot(self) -> AnimationSnapshot:
        with self._lock:
            return AnimationSnapshot(
                state=self._state,
                document_number=self._document_number,
                document_count=self.document_count,
                source_id=self._source_id,
                is_terminal=self._state in TERMINAL_STATES,
            )

    def render_frame(self, now: float | None = None) -> str:
        """Return one frame. Call from the GUI's own timer/event loop."""
        with self._lock:
            elapsed = max(0.0, (time.monotonic() if now is None else now) - self._started_at)
            tick = int(elapsed / self.frame_interval)
            rows = self._render_document_rows(tick)
            number = self._document_number or 1
            title = f"Dokument {number} z {self.document_count}"
            spinner = self._SPINNER[tick % len(self._SPINNER)] if self._state == AnimationState.RUNNING else " "

            output = [self._box_top()]
            output.append(self._box_line(f" DOCSHIELD  {spinner}  {title}"))
            output.append(self._box_divider())
            output.extend(self._box_line(" " + row) for row in rows)
            output.append(self._box_divider())
            output.append(self._box_line(f" {self._message}"))
            output.append(self._box_top(bottom=True))
            return "\n".join(output)

    def _running_message(self) -> str:
        return self.MESSAGE_CANCEL_PENDING if self._cancel_requested else self.MESSAGE_RUNNING

    def _render_document_rows(self, tick: int) -> list[str]:
        scan_row = tick % (len(self._DOCUMENT_ROWS) + 3) - 1
        terminal = self._state in {
            AnimationState.DOCUMENT_COMPLETED,
            AnimationState.SUCCESS,
        }
        result: list[str] = []
        for row_index, original in enumerate(self._DOCUMENT_ROWS):
            row = original
            for fragment in self._PRIVATE_FRAGMENTS:
                if fragment in row and (terminal or row_index <= scan_row):
                    row = row.replace(fragment, self.MASK * len(fragment))
            row = row[: self.DOCUMENT_WIDTH].ljust(self.DOCUMENT_WIDTH)

            # Tiny operator and its marker travel beside the document. They are
            # decorative and never affect or expose document content.
            if self._state == AnimationState.RUNNING and row_index == scan_row:
                marker = " >o>" if tick % 2 == 0 else " >O/"
            else:
                marker = "    "
            result.append(row + marker)
        return result

    def _box_line(self, text: str) -> str:
        inner = self.FRAME_WIDTH - 2
        return "|" + text[:inner].ljust(inner) + "|"

    def _box_top(self, *, bottom: bool = False) -> str:
        del bottom  # Same ASCII corners keep every terminal/font predictable.
        return "+" + "-" * (self.FRAME_WIDTH - 2) + "+"

    def _box_divider(self) -> str:
        return "+" + "-" * (self.FRAME_WIDTH - 2) + "+"

    def _require_current(self, expected: AnimationState) -> None:
        if self._state != expected or self._document_number == 0:
            raise RuntimeError(f"expected state: {expected.value}")


def _terminal_demo(document_count: int = 3) -> None:
    """Small optional preview: ``python docshield_ascii_animation.py``."""
    animation = DocShieldAsciiAnimation(document_count)
    for index in range(document_count):
        if index == 0:
            animation.start_document(source_id=f"opaque-{index + 1}")
        else:
            animation.advance_to_next(source_id=f"opaque-{index + 1}")
        for _ in range(32):
            sys.stdout.write("\x1b[2J\x1b[H" + animation.render_frame())
            sys.stdout.flush()
            time.sleep(animation.frame_interval)
        animation.mark_current_completed()
        sys.stdout.write("\x1b[2J\x1b[H" + animation.render_frame())
        sys.stdout.flush()
        time.sleep(0.65)
    animation.stop_success()
    sys.stdout.write("\x1b[2J\x1b[H" + animation.render_frame() + "\n")


if __name__ == "__main__":
    _terminal_demo()
