"""Tests for Etap 7: stripping AcroForm signature fields from PDFs.

Real case (see notatki.txt / docs/PROJECT_STATE.md): a document to
anonymize contained an electronic signature - both its own visual
"Podpisano elektronicznie przez: ..." box and the actual signature -
that this app's regex/NER pipeline never touched, because it lives in
a form-field appearance stream, not the page's own text content. A
colleague's qpdf-based workaround removed it manually; this closes the
gap in DocShield itself using PyMuPDF (already a bundled dependency,
no new external tool needed) to delete the signature widget outright.
"""

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from anonymizer import anonymize_batch
from pdf_redaction import (
    _strip_signature_widgets,
    extract_pdf_word_pages,
    pdf_has_signature_widget,
    save_redacted_pdf_copy,
    save_word_coordinate_redacted_image_copy,
    save_word_coordinate_redacted_pdf_copy,
)


def workspace_temp_dir():
    return tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "tests")


def write_fitz_pdf_with_signature_widget(
    path: Path,
    *,
    page_count: int = 1,
    signature_page: int = 1,
    body_lines: tuple[str, ...] = ("Umowa najmu - dokument testowy.",),
) -> None:
    """A synthetic multi-page PDF with one AcroForm signature field
    (``field_type == PDF_WIDGET_TYPE_SIGNATURE``) on ``signature_page``
    (1-based). Mirrors how a real digitally-signed PDF places its
    "Podpisano elektronicznie przez: ..." visual box: a widget with its
    own appearance, not page body text."""
    import pymupdf as fitz

    document = fitz.open()
    for page_index in range(page_count):
        page = document.new_page()
        y = 72
        for line in body_lines:
            page.insert_text((72, y), line, fontsize=12)
            y += 18
        if page_index + 1 == signature_page:
            widget = fitz.Widget()
            widget.field_name = f"Signature{page_index + 1}"
            widget.field_type = fitz.PDF_WIDGET_TYPE_SIGNATURE
            widget.field_label = "Signature"
            widget.rect = fitz.Rect(72, 650, 300, 690)
            page.add_widget(widget)
    document.save(path)
    document.close()


def count_signature_widgets(path: Path) -> int:
    import pymupdf as fitz

    total = 0
    with fitz.open(path) as document:
        for page in document:
            for widget in page.widgets() or ():
                if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                    total += 1
    return total


class StripSignatureWidgetsUnitTests(unittest.TestCase):
    """Direct coverage for _strip_signature_widgets, independent of
    which higher-level save_* function calls it."""

    def test_default_is_a_no_op_even_with_a_real_signature_present(self) -> None:
        """The user's own explicit decision (2026-09-18): "usuwanie
        podpisu to osobna opcja - nie dziala automatycznie". The gate
        lives inside this shared helper (not only at its callers' call
        sites), so this is the lowest-level guarantee that off-by-default
        actually holds."""
        import pymupdf as fitz

        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "signed.pdf"
            write_fitz_pdf_with_signature_widget(source_path)

            with fitz.open(source_path) as document:
                removed = _strip_signature_widgets(fitz, document)
                remaining = sum(1 for _ in (document[0].widgets() or ()))

        self.assertEqual(removed, 0)
        self.assertEqual(remaining, 1)

    def test_removes_a_signature_widget_and_returns_its_count(self) -> None:
        import pymupdf as fitz

        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "signed.pdf"
            write_fitz_pdf_with_signature_widget(source_path)

            with fitz.open(source_path) as document:
                removed = _strip_signature_widgets(
                    fitz, document, strip_signatures=True
                )
                remaining = sum(
                    1
                    for page in document
                    for widget in (page.widgets() or ())
                    if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE
                )

        self.assertEqual(removed, 1)
        self.assertEqual(remaining, 0)

    def test_no_signature_field_is_a_harmless_no_op(self) -> None:
        import pymupdf as fitz

        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "plain.pdf"
            document = fitz.open()
            page = document.new_page()
            page.insert_text((72, 72), "No signature here.", fontsize=12)
            document.save(source_path)
            document.close()

            with fitz.open(source_path) as document:
                removed = _strip_signature_widgets(
                    fitz, document, strip_signatures=True
                )

        self.assertEqual(removed, 0)

    def test_non_signature_form_fields_are_left_alone(self) -> None:
        """A text or checkbox form field is not PII to redact by itself -
        only the signature field type is in scope."""
        import pymupdf as fitz

        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "form.pdf"
            document = fitz.open()
            page = document.new_page()
            widget = fitz.Widget()
            widget.field_name = "Comment"
            widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
            widget.field_label = "Comment"
            widget.rect = fitz.Rect(72, 650, 300, 690)
            page.add_widget(widget)
            document.save(source_path)
            document.close()

            with fitz.open(source_path) as document:
                removed = _strip_signature_widgets(
                    fitz, document, strip_signatures=True
                )
                remaining = sum(1 for _ in (document[0].widgets() or ()))

        self.assertEqual(removed, 0)
        self.assertEqual(remaining, 1)

    def test_active_pages_leaves_out_of_scope_signature_untouched(self) -> None:
        import pymupdf as fitz

        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "signed_page_two.pdf"
            write_fitz_pdf_with_signature_widget(
                source_path, page_count=2, signature_page=2
            )

            with fitz.open(source_path) as document:
                removed = _strip_signature_widgets(
                    fitz,
                    document,
                    active_pages=frozenset({1}),
                    strip_signatures=True,
                )
                remaining = sum(
                    1
                    for page in document
                    for widget in (page.widgets() or ())
                    if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE
                )

        self.assertEqual(removed, 0)
        self.assertEqual(remaining, 1)

    def test_multiple_signature_widgets_on_one_page_are_all_removed(self) -> None:
        """A co-signed document (a real, common case - a contract with two
        signers) can place more than one signature widget on the same
        page. Regression guard for a real crash this exact fixture
        caught: deleting from a *materialized* widget list raised
        PyMuPDF's FzErrorArgument ("annotation not bound to any page")
        on the second delete, for a document opened from a file path
        (every real caller's case) - fixed by re-querying widgets fresh
        after each deletion (see _strip_signature_widgets)."""
        import gc

        import pymupdf as fitz

        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "co_signed.pdf"
            document = fitz.open()
            page = document.new_page()
            page.insert_text((72, 72), "Umowa dwustronna.", fontsize=12)
            for index, y in enumerate((500, 600)):
                widget = fitz.Widget()
                widget.field_name = f"Signature{index + 1}"
                widget.field_type = fitz.PDF_WIDGET_TYPE_SIGNATURE
                widget.field_label = f"Signature{index + 1}"
                widget.rect = fitz.Rect(72, y, 300, y + 40)
                page.add_widget(widget)
            document.save(source_path)
            document.close()

            with fitz.open(source_path) as document:
                removed = _strip_signature_widgets(
                    fitz, document, strip_signatures=True
                )
                remaining = sum(1 for _ in (document[0].widgets() or ()))
            # A closed fitz.Document can still hold the source file's OS
            # handle open for a moment on Windows - gc.collect() nudges
            # that release before this block's own TemporaryDirectory
            # cleanup tries to delete the same file.
            gc.collect()

        self.assertEqual(removed, 2)
        self.assertEqual(remaining, 0)


class PdfHasSignatureWidgetTests(unittest.TestCase):
    """Coverage for the magic-pen sidebar's "should I even show the
    toggle" gate (ComparisonWindow._document_has_signature_widget)."""

    def test_true_for_a_document_with_a_signature_widget(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "signed.pdf"
            write_fitz_pdf_with_signature_widget(source_path)
            self.assertTrue(pdf_has_signature_widget(source_path))

    def test_false_for_a_plain_document(self) -> None:
        import pymupdf as fitz

        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "plain.pdf"
            document = fitz.open()
            page = document.new_page()
            page.insert_text((72, 72), "No signature here.", fontsize=12)
            document.save(source_path)
            document.close()
            self.assertFalse(pdf_has_signature_widget(source_path))

    def test_false_for_a_non_signature_form_field(self) -> None:
        import pymupdf as fitz

        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "form.pdf"
            document = fitz.open()
            page = document.new_page()
            widget = fitz.Widget()
            widget.field_name = "Comment"
            widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
            widget.field_label = "Comment"
            widget.rect = fitz.Rect(72, 650, 300, 690)
            page.add_widget(widget)
            document.save(source_path)
            document.close()
            self.assertFalse(pdf_has_signature_widget(source_path))

    def test_false_for_a_missing_file_never_raises(self) -> None:
        with workspace_temp_dir() as temp_dir:
            missing_path = Path(temp_dir) / "does_not_exist.pdf"
            self.assertFalse(pdf_has_signature_widget(missing_path))

    def test_active_pages_excludes_a_signature_on_an_out_of_scope_page(
        self,
    ) -> None:
        """Regression guard for a real bug code review caught: without
        the same active_pages/_page_in_scope filtering
        _strip_signature_widgets itself applies, this gate would show the
        magic-pen toggle for a document whose Etap 5 page range excludes
        the only page carrying a signature - and flipping that toggle
        would then be a guaranteed no-op."""
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "signed_page_two.pdf"
            write_fitz_pdf_with_signature_widget(
                source_path, page_count=2, signature_page=2
            )
            self.assertFalse(
                pdf_has_signature_widget(
                    source_path, active_pages=frozenset({1})
                )
            )
            self.assertTrue(
                pdf_has_signature_widget(
                    source_path, active_pages=frozenset({2})
                )
            )
            self.assertTrue(pdf_has_signature_widget(source_path))

    def test_false_for_a_corrupt_non_pdf_file_never_raises(self) -> None:
        with workspace_temp_dir() as temp_dir:
            bad_path = Path(temp_dir) / "not_a_pdf.pdf"
            bad_path.write_text("this is not a pdf", encoding="utf-8")
            self.assertFalse(pdf_has_signature_widget(bad_path))


class SaveWordCoordinateRedactedPdfCopySignatureTests(unittest.TestCase):
    """The default (_ANON_VISUAL.pdf) output path."""

    def test_signature_widget_is_left_alone_by_default(self) -> None:
        """Etap 7 is an explicit per-task opt-in, per the user's own
        decision (2026-09-18): "usuwanie podpisu to osobna opcja - nie
        dziala automatycznie". strip_signatures defaults to False."""
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "signed.pdf"
            write_fitz_pdf_with_signature_widget(source_path)
            word_pages = extract_pdf_word_pages(source_path)

            result = save_word_coordinate_redacted_pdf_copy(
                source_path,
                word_pages=word_pages,
                spans=[],
                output_dir=temp_dir,
            )

            output_path = Path(temp_dir) / result["output_name"]
            remaining = count_signature_widgets(output_path)
        self.assertEqual(result["signature_fields_removed"], 0)
        self.assertEqual(remaining, 1)

    def test_signature_widget_is_stripped_when_opted_in(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "signed.pdf"
            write_fitz_pdf_with_signature_widget(source_path)
            word_pages = extract_pdf_word_pages(source_path)

            result = save_word_coordinate_redacted_pdf_copy(
                source_path,
                word_pages=word_pages,
                spans=[],
                output_dir=temp_dir,
                strip_signatures=True,
            )

            output_path = Path(temp_dir) / result["output_name"]
            remaining = count_signature_widgets(output_path)
        self.assertEqual(result["signature_fields_removed"], 1)
        self.assertEqual(remaining, 0)

    def test_active_pages_protects_an_out_of_scope_signature(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "signed_page_two.pdf"
            write_fitz_pdf_with_signature_widget(
                source_path, page_count=2, signature_page=2
            )
            word_pages = extract_pdf_word_pages(source_path)

            result = save_word_coordinate_redacted_pdf_copy(
                source_path,
                word_pages=word_pages,
                spans=[],
                strip_signatures=True,
                output_dir=temp_dir,
                active_pages=frozenset({1}),
            )

            output_path = Path(temp_dir) / result["output_name"]
            remaining = count_signature_widgets(output_path)
        self.assertEqual(result["signature_fields_removed"], 0)
        self.assertEqual(remaining, 1)

    def test_scanned_image_input_never_carries_a_signature_widget(self) -> None:
        """save_word_coordinate_redacted_image_copy wraps a standalone
        image in a synthetic, freshly-built single-page PDF before
        delegating here - it can never inherit an AcroForm from anywhere,
        since there is no source PDF to inherit one from. Verified
        directly rather than only trusted from the code's own comment."""
        import pymupdf as fitz

        with workspace_temp_dir() as temp_dir:
            source_image = Path(temp_dir) / "scan.png"
            pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 200, 100))
            pixmap.set_rect(pixmap.irect, (255, 255, 255))
            pixmap.save(source_image)

            result = save_word_coordinate_redacted_image_copy(
                source_image,
                word_pages=[],
                spans=[],
                output_dir=temp_dir,
            )

            output_path = Path(temp_dir) / result["output_name"]
            remaining = count_signature_widgets(output_path)
        self.assertEqual(result["signature_fields_removed"], 0)
        self.assertEqual(remaining, 0)


class SaveRedactedPdfCopySignatureTests(unittest.TestCase):
    """The experimental "original layout redaction" output path."""

    def test_signature_widget_is_left_alone_by_default(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "signed.pdf"
            write_fitz_pdf_with_signature_widget(source_path)

            result = save_redacted_pdf_copy(source_path, output_dir=temp_dir)

            output_path = Path(temp_dir) / result["output_name"]
            remaining = count_signature_widgets(output_path)
        self.assertEqual(result["signature_fields_removed"], 0)
        self.assertEqual(remaining, 1)

    def test_signature_widget_is_stripped_when_opted_in(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "signed.pdf"
            write_fitz_pdf_with_signature_widget(source_path)

            result = save_redacted_pdf_copy(
                source_path, output_dir=temp_dir, strip_signatures=True
            )

            output_path = Path(temp_dir) / result["output_name"]
            remaining = count_signature_widgets(output_path)
        self.assertEqual(result["signature_fields_removed"], 1)
        self.assertEqual(remaining, 0)


class SignatureRemovalEndToEndTests(unittest.TestCase):
    def test_anonymize_batch_leaves_the_signature_by_default(self) -> None:
        """The user's own explicit decision (2026-09-18): this must never
        run automatically. anonymize_batch's default (no strip_signatures
        argument) must leave a signature widget untouched."""
        with workspace_temp_dir() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            output_dir = Path(temp_dir) / "output"
            source_dir.mkdir()
            output_dir.mkdir()
            source_path = source_dir / "umowa.pdf"
            write_fitz_pdf_with_signature_widget(
                source_path,
                body_lines=("PESEL 00000000000 w tresci umowy.",),
            )

            anonymize_batch([source_path], output_dir)

            visual_pdf = output_dir / "umowa_ANON_VISUAL.pdf"
            self.assertTrue(visual_pdf.exists())
            remaining = count_signature_widgets(visual_pdf)
        self.assertEqual(remaining, 1)

    def test_anonymize_batch_removes_the_signature_when_opted_in(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            output_dir = Path(temp_dir) / "output"
            source_dir.mkdir()
            output_dir.mkdir()
            source_path = source_dir / "umowa.pdf"
            write_fitz_pdf_with_signature_widget(
                source_path,
                body_lines=("PESEL 00000000000 w tresci umowy.",),
            )

            batch_result = anonymize_batch(
                [source_path], output_dir, strip_signatures=True
            )

            visual_pdf = output_dir / "umowa_ANON_VISUAL.pdf"
            self.assertTrue(visual_pdf.exists())
            self.assertEqual(count_signature_widgets(visual_pdf), 0)
            warning = str(
                batch_result.results[0].get("pdf_redaction_warning", "")
            )
        self.assertEqual(warning, "")

    def test_sidecar_freezes_the_strip_signatures_choice(self) -> None:
        """Regeneration through the magic-pen path must reuse the choice
        frozen at first-anonymization time, not silently default back to
        off (or on) - mirrors the existing active_pages/active_labels
        sidecar-freeze tests in tests/test_category_selection.py."""
        from anonymizer import (
            category_selection_path,
            load_signature_stripping_selection,
        )

        with workspace_temp_dir() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            output_dir = Path(temp_dir) / "output"
            source_dir.mkdir()
            output_dir.mkdir()
            source_path = source_dir / "umowa.pdf"
            write_fitz_pdf_with_signature_widget(source_path)

            anonymize_batch([source_path], output_dir, strip_signatures=True)

            visual_pdf = output_dir / "umowa_ANON_VISUAL.pdf"
            frozen = load_signature_stripping_selection(
                category_selection_path(visual_pdf)
            )
        self.assertTrue(frozen)


if __name__ == "__main__":
    unittest.main()
