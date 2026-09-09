"""Tests for the pip-package update check and silent updater."""

import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import dependency_updates as du


class GetInstalledVersionTests(unittest.TestCase):
    def test_returns_version_when_installed(self) -> None:
        with patch("dependency_updates.importlib.metadata.version", return_value="1.2.3"):
            self.assertEqual(du.get_installed_version("pypdf"), "1.2.3")

    def test_returns_none_when_not_installed(self) -> None:
        import importlib.metadata

        with patch(
            "dependency_updates.importlib.metadata.version",
            side_effect=importlib.metadata.PackageNotFoundError,
        ):
            self.assertIsNone(du.get_installed_version("nope"))


class GetLatestVersionFromPypiTests(unittest.TestCase):
    def test_returns_version_from_json_payload(self) -> None:
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b'{"info": {"version": "9.9.9"}}'

        with (
            patch("dependency_updates.urllib.request.urlopen", return_value=FakeResponse()),
            patch(
                "dependency_updates.json.load",
                return_value={"info": {"version": "9.9.9"}},
            ),
        ):
            self.assertEqual(du.get_latest_version_from_pypi("pypdf"), "9.9.9")

    def test_returns_none_on_network_error(self) -> None:
        import urllib.error

        with patch(
            "dependency_updates.urllib.request.urlopen",
            side_effect=urllib.error.URLError("offline"),
        ):
            self.assertIsNone(du.get_latest_version_from_pypi("pypdf"))

    def test_returns_none_on_timeout(self) -> None:
        with patch(
            "dependency_updates.urllib.request.urlopen", side_effect=TimeoutError
        ):
            self.assertIsNone(du.get_latest_version_from_pypi("pypdf"))

    def test_returns_none_on_malformed_payload(self) -> None:
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        with (
            patch("dependency_updates.urllib.request.urlopen", return_value=FakeResponse()),
            patch("dependency_updates.json.load", return_value={}),
        ):
            self.assertIsNone(du.get_latest_version_from_pypi("pypdf"))


class CheckPackageUpdateTests(unittest.TestCase):
    def test_not_ok_when_not_installed(self) -> None:
        with patch("dependency_updates.get_installed_version", return_value=None):
            result = du.check_package_update("pypdf")

        self.assertFalse(result.ok)
        self.assertFalse(result.update_available)
        self.assertIsNone(result.installed_version)

    def test_not_ok_when_pypi_lookup_fails(self) -> None:
        with (
            patch("dependency_updates.get_installed_version", return_value="1.0.0"),
            patch("dependency_updates.get_latest_version_from_pypi", return_value=None),
        ):
            result = du.check_package_update("pypdf")

        self.assertFalse(result.ok)
        self.assertIsNotNone(result.error_pl)

    def test_update_available_when_pypi_version_is_newer(self) -> None:
        with (
            patch("dependency_updates.get_installed_version", return_value="1.0.0"),
            patch("dependency_updates.get_latest_version_from_pypi", return_value="1.2.0"),
        ):
            result = du.check_package_update("pypdf")

        self.assertTrue(result.ok)
        self.assertTrue(result.update_available)
        self.assertEqual(result.installed_version, "1.0.0")
        self.assertEqual(result.latest_version, "1.2.0")

    def test_no_update_when_already_latest(self) -> None:
        with (
            patch("dependency_updates.get_installed_version", return_value="2.0.0"),
            patch("dependency_updates.get_latest_version_from_pypi", return_value="2.0.0"),
        ):
            result = du.check_package_update("pypdf")

        self.assertTrue(result.ok)
        self.assertFalse(result.update_available)

    def test_no_update_when_installed_is_newer_than_pypi_reports(self) -> None:
        # e.g. installed from a pre-release or a mirror lagging behind PyPI.
        with (
            patch("dependency_updates.get_installed_version", return_value="3.0.0"),
            patch("dependency_updates.get_latest_version_from_pypi", return_value="2.9.0"),
        ):
            result = du.check_package_update("pypdf")

        self.assertTrue(result.ok)
        self.assertFalse(result.update_available)

    def test_falls_back_to_string_comparison_on_unparseable_version(self) -> None:
        # Can't parse either string as a real version - falls back to a
        # plain inequality check so a real difference is still surfaced
        # rather than silently swallowed.
        with (
            patch("dependency_updates.get_installed_version", return_value="not-a-version"),
            patch(
                "dependency_updates.get_latest_version_from_pypi",
                return_value="also-not-a-version",
            ),
        ):
            result = du.check_package_update("weird")

        self.assertTrue(result.ok)
        self.assertTrue(result.update_available)

    def test_string_fallback_reports_no_update_when_versions_are_identical(self) -> None:
        with (
            patch("dependency_updates.get_installed_version", return_value="not-a-version"),
            patch(
                "dependency_updates.get_latest_version_from_pypi",
                return_value="not-a-version",
            ),
        ):
            result = du.check_package_update("weird")

        self.assertTrue(result.ok)
        self.assertFalse(result.update_available)


class CheckDependencyUpdatesTests(unittest.TestCase):
    def test_returns_one_result_per_package_in_order(self) -> None:
        def fake_check(name, timeout_seconds=4.0):
            return du.PackageUpdateCheck(name, "1.0", "1.0", False, True)

        with patch("dependency_updates.check_package_update", side_effect=fake_check):
            results = du.check_dependency_updates(("a", "b", "c"))

        self.assertEqual([r.package for r in results], ["a", "b", "c"])

    def test_empty_packages_returns_empty_list(self) -> None:
        self.assertEqual(du.check_dependency_updates(()), [])


class InstallPackageUpdateTests(unittest.TestCase):
    def test_reports_success_on_zero_return_code(self) -> None:
        class FakeCompleted:
            returncode = 0
            stdout = ""
            stderr = ""

        with patch("dependency_updates.subprocess.run", return_value=FakeCompleted()):
            success, message = du.install_package_update("pypdf")

        self.assertTrue(success)
        self.assertEqual(message, "")

    def test_reports_failure_with_captured_stderr(self) -> None:
        class FakeCompleted:
            returncode = 1
            stdout = ""
            stderr = "could not find a version that satisfies"

        with patch("dependency_updates.subprocess.run", return_value=FakeCompleted()):
            success, message = du.install_package_update("pypdf")

        self.assertFalse(success)
        self.assertIn("could not find a version", message)

    def test_reports_failure_on_timeout(self) -> None:
        with patch(
            "dependency_updates.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="pip", timeout=1),
        ):
            success, message = du.install_package_update("pypdf", timeout_seconds=1)

        self.assertFalse(success)
        self.assertTrue(message)

    def test_invokes_pip_upgrade_with_current_interpreter(self) -> None:
        class FakeCompleted:
            returncode = 0
            stdout = ""
            stderr = ""

        with patch(
            "dependency_updates.subprocess.run", return_value=FakeCompleted()
        ) as mock_run:
            du.install_package_update("pypdf")

        called_args = mock_run.call_args[0][0]
        self.assertEqual(
            called_args, [sys.executable, "-m", "pip", "install", "--upgrade", "pypdf"]
        )


if __name__ == "__main__":
    unittest.main()
