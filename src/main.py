"""Application entry point for the local document anonymizer."""

import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from gui import start_gui


def _suppress_child_console_windows() -> None:
    """On Windows, a windowed (console-less) process that spawns a child
    via subprocess still gets a new, briefly-visible console window for
    that child - Windows allocates one whenever the parent has none,
    regardless of the parent's own windowed/--noconsole build. Real
    user report: 2-3 terminal windows flashing a couple seconds after
    the GUI appears, right as the background startup checks (OCR
    language list via pytesseract, pip dependency-update check, the
    spaCy/NER model check) each spawn their own subprocess. None of
    those call sites - including inside the vendored pytesseract
    library, which this app can't edit - pass Windows' console-
    suppression flags themselves, so this patches subprocess.Popen
    itself (every subprocess.run/check_output/Popen call in the process
    constructs one internally) rather than fixing each call site
    separately. This app has no legitimate reason to ever show a
    spawned console window, so the patch applies unconditionally, not
    just to specific commands."""
    if sys.platform != "win32":
        return
    original_init = subprocess.Popen.__init__

    def _patched_init(self, *args, **kwargs):
        kwargs["creationflags"] = kwargs.get("creationflags", 0) | subprocess.CREATE_NO_WINDOW
        original_init(self, *args, **kwargs)

    subprocess.Popen.__init__ = _patched_init


def _log_crash(exc: BaseException) -> None:
    """Write an uncaught startup/runtime crash to a local log file.

    A windowed launch (pythonw.exe, or the packaged --noconsole .exe)
    has no console to print a traceback to, so a crash here would
    otherwise be completely silent - the window just never appears,
    with no way to tell why. Never raises itself; a failure to write
    the log must never mask the original crash.
    """
    try:
        log_dir = Path.home() / ".anonimizer"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "ostatni_blad.log"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"\n--- {datetime.now(timezone.utc).isoformat()} ---\n")
            traceback.print_exception(type(exc), exc, exc.__traceback__, file=handle)
    except OSError:
        pass


def main() -> None:
    """Start the default desktop GUI."""
    _suppress_child_console_windows()
    try:
        start_gui()
    except Exception as error:
        _log_crash(error)
        raise


if __name__ == "__main__":
    main()
