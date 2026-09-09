"""Startup check for newer versions of the pip-managed libraries this app
depends on, plus a fully silent, in-place update path for them.

Scope is deliberately limited to packages that live inside the app's own
virtual environment and are installed with pip (see `requirements.txt`).
For those, "update" is a plain `pip install --upgrade <package>` run as a
subprocess in this same interpreter's environment - no browser, no manual
download, no separate installer to run by hand. The user only ever sees
one confirmation before the install starts.

Tesseract and Ollama are deliberately out of scope here: they are
external system installers, not pip packages, and updating them safely
(download, verify, silently run an elevated installer) is a materially
different and riskier problem than upgrading a wheel inside a venv. They
keep using the existing "Pobierz" (open download page) flow in
`environment_check.py`.

MAINTENANCE NOTE: `DEFAULT_PACKAGES` is not auto-derived from
`requirements.txt` - it is the explicit list of pip packages this check
knows to look at. Any future added/removed dependency in
`requirements.txt` needs the same change made here, or it will silently
stop being covered by both the update check and the one-click updater.
"""

from __future__ import annotations

import importlib.metadata
import json
import subprocess
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

try:
    from packaging.version import InvalidVersion, Version
except ImportError:  # pragma: no cover - packaging ships with pip/setuptools
    Version = None  # type: ignore[assignment,misc]
    InvalidVersion = Exception  # type: ignore[assignment,misc]


DEFAULT_PACKAGES: tuple[str, ...] = (
    "python-docx",
    "pypdf",
    "pytesseract",
    "Pillow",
    "PyMuPDF",
    "spacy",
    "customtkinter",
    "tkinterdnd2",
)

PYPI_JSON_URL_TEMPLATE = "https://pypi.org/pypi/{name}/json"
DEFAULT_NETWORK_TIMEOUT_SECONDS = 4.0


@dataclass(frozen=True)
class PackageUpdateCheck:
    """One package's update-check result, safe to show directly in the UI."""

    package: str
    installed_version: str | None
    latest_version: str | None
    update_available: bool
    ok: bool
    error_pl: str | None = None


def get_installed_version(package: str) -> str | None:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def get_latest_version_from_pypi(
    package: str, timeout_seconds: float = DEFAULT_NETWORK_TIMEOUT_SECONDS
) -> str | None:
    """Best-effort lookup of the newest version on PyPI. Never raises - any
    network, timeout, or parsing failure just means "unknown", not a crash.
    """
    url = PYPI_JSON_URL_TEMPLATE.format(name=package)
    try:
        with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None
    version = payload.get("info", {}).get("version")
    return version if isinstance(version, str) and version else None


def _is_newer(latest: str, installed: str) -> bool:
    if Version is None:
        return latest != installed
    try:
        return Version(latest) > Version(installed)
    except InvalidVersion:
        return latest != installed


def check_package_update(
    package: str, timeout_seconds: float = DEFAULT_NETWORK_TIMEOUT_SECONDS
) -> PackageUpdateCheck:
    installed = get_installed_version(package)
    if installed is None:
        return PackageUpdateCheck(
            package, None, None, False, False, "Biblioteka nie jest zainstalowana."
        )

    latest = get_latest_version_from_pypi(package, timeout_seconds)
    if latest is None:
        return PackageUpdateCheck(
            package,
            installed,
            None,
            False,
            False,
            "Nie udało się sprawdzić najnowszej wersji (brak połączenia z internetem?).",
        )

    return PackageUpdateCheck(
        package, installed, latest, _is_newer(latest, installed), True
    )


def check_dependency_updates(
    packages: tuple[str, ...] = DEFAULT_PACKAGES,
    timeout_seconds: float = DEFAULT_NETWORK_TIMEOUT_SECONDS,
    max_workers: int = 8,
) -> list[PackageUpdateCheck]:
    """Check every known package for a newer version, in parallel.

    Runs the (network-bound) per-package checks concurrently so the total
    wall time stays close to one package's timeout instead of scaling with
    the package count - important when offline, where every lookup times
    out individually.
    """
    if not packages:
        return []
    with ThreadPoolExecutor(max_workers=min(max_workers, len(packages))) as pool:
        results = list(
            pool.map(lambda name: check_package_update(name, timeout_seconds), packages)
        )
    return results


def install_package_update(
    package: str, timeout_seconds: int = 300
) -> tuple[bool, str]:
    """Run `pip install --upgrade <package>` in this app's own venv.

    Same contained-install shape as `environment_check.install_ner_model`:
    no admin rights, no system changes, everything stays inside the venv
    pip already manages.
    """
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", package],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, str(error)
    if completed.returncode == 0:
        return True, ""
    return False, (completed.stderr or completed.stdout or "").strip()[-800:]


__all__ = [
    "DEFAULT_PACKAGES",
    "PackageUpdateCheck",
    "check_dependency_updates",
    "check_package_update",
    "get_installed_version",
    "get_latest_version_from_pypi",
    "install_package_update",
]
