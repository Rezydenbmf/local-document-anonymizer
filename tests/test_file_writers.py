"""Tests for the dated-output-folder redesign's two new primitives in
file_writers.py (2026-09-22): dated_output_subdir (grouping every
anonymization run by calendar day) and the "txt" subfolder redirect the
four visible TXT/DOCX-producing path builders now use (keeping a PDF's
own folder holding only PDFs directly).
"""

import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from file_writers import (
    build_anonymized_docx_path,
    build_anonymized_image_txt_path,
    build_anonymized_pdf_txt_path,
    build_anonymized_txt_path,
    build_pdf_visual_path,
    dated_output_subdir,
)


def workspace_temp_dir():
    return tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "tests")


class DatedOutputSubdirTests(unittest.TestCase):
    def test_creates_a_ddmmyyyy_subfolder_of_output_dir(self) -> None:
        with workspace_temp_dir() as temp_dir:
            output_dir = Path(temp_dir)

            dated = dated_output_subdir(output_dir, today=date(2026, 9, 22))

            self.assertEqual(dated, output_dir / "22.09.2026")
            self.assertTrue(dated.is_dir())

    def test_same_day_reuses_the_same_folder(self) -> None:
        with workspace_temp_dir() as temp_dir:
            output_dir = Path(temp_dir)

            first = dated_output_subdir(output_dir, today=date(2026, 9, 22))
            (first / "umowa_ANON_VISUAL.pdf").write_text("x", encoding="utf-8")
            second = dated_output_subdir(output_dir, today=date(2026, 9, 22))

            self.assertEqual(first, second)
            self.assertTrue((second / "umowa_ANON_VISUAL.pdf").exists())

    def test_a_different_day_gets_its_own_folder(self) -> None:
        with workspace_temp_dir() as temp_dir:
            output_dir = Path(temp_dir)

            first = dated_output_subdir(output_dir, today=date(2026, 9, 22))
            second = dated_output_subdir(output_dir, today=date(2026, 9, 23))

            self.assertNotEqual(first, second)
            self.assertTrue(first.is_dir())
            self.assertTrue(second.is_dir())

    def test_default_today_matches_the_real_current_date(self) -> None:
        with workspace_temp_dir() as temp_dir:
            dated = dated_output_subdir(Path(temp_dir))

            self.assertEqual(dated.name, date.today().strftime("%d.%m.%Y"))  # noqa: DTZ011


class TxtSubfolderRedirectTests(unittest.TestCase):
    """The four builders that produce a visible-to-the-user TXT/DOCX
    file land in a "txt" subfolder of the folder they would otherwise
    have used - every PDF-producing builder (e.g. build_pdf_visual_path)
    is deliberately untouched, so a PDF's own folder keeps holding only
    PDFs directly."""

    def test_txt_source_output_redirects_into_txt_subfolder(self) -> None:
        with workspace_temp_dir() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            source_path = Path(temp_dir) / "document.txt"

            result = build_anonymized_txt_path(source_path, output_dir=output_dir)

            self.assertEqual(result, output_dir / "txt" / "document_ANON.txt")
            self.assertTrue((output_dir / "txt").is_dir())

    def test_docx_source_output_redirects_into_txt_subfolder(self) -> None:
        with workspace_temp_dir() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            source_path = Path(temp_dir) / "document.docx"

            result = build_anonymized_docx_path(source_path, output_dir=output_dir)

            self.assertEqual(result, output_dir / "txt" / "document_ANON.docx")

    def test_pdf_companion_txt_redirects_into_txt_subfolder(self) -> None:
        with workspace_temp_dir() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            source_path = Path(temp_dir) / "document.pdf"

            result = build_anonymized_pdf_txt_path(source_path, output_dir=output_dir)

            self.assertEqual(result, output_dir / "txt" / "document_ANON.txt")

    def test_image_ocr_txt_redirects_into_txt_subfolder(self) -> None:
        with workspace_temp_dir() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            source_path = Path(temp_dir) / "scan.png"

            result = build_anonymized_image_txt_path(source_path, output_dir=output_dir)

            self.assertEqual(result, output_dir / "txt" / "scan_ANON.txt")

    def test_none_output_dir_redirects_relative_to_the_source_folder(self) -> None:
        """output_dir=None ("same folder as source") gets the same "txt"
        redirect, for consistency - the rule is exceptionless: whatever
        folder these four builders would have used, a "txt" subfolder of
        it, always."""
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.txt"

            result = build_anonymized_txt_path(source_path)

            self.assertEqual(result, Path(temp_dir) / "txt" / "document_ANON.txt")

    def test_pdf_visual_output_is_never_redirected(self) -> None:
        with workspace_temp_dir() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            source_path = Path(temp_dir) / "document.pdf"

            result = build_pdf_visual_path(source_path, output_dir=output_dir)

            self.assertEqual(result, output_dir / "document_ANON_VISUAL.pdf")


if __name__ == "__main__":
    unittest.main()
