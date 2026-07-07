"""Tests for Stage 4 text-based PDF input and Stage 23 visual redaction."""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from anonymizer import (
    PDF_OUTPUT_MODE_ORIGINAL_REDACTION,
    PDF_OUTPUT_MODE_VISUAL,
    _pdf_detection_spans_for_word_pages,
    anonymize_pdf_file,
)
from file_readers import extract_text, read_pdf_file
from file_writers import (
    build_anonymized_pdf_path,
    build_anonymized_pdf_txt_path,
    build_original_redacted_pdf_path,
    build_pdf_review_path,
    build_pdf_visual_path,
    build_review_checklist_path,
    save_anonymized_copy,
    save_anonymized_pdf_txt_copy,
)
from pdf_redaction import PdfWordPage, save_redacted_pdf_copy


class FakeEntity:
    def __init__(self, start: int, end: int, label: str) -> None:
        self.start_char = start
        self.end_char = end
        self.label_ = label


class FakeDoc:
    def __init__(self, ents: list[FakeEntity]) -> None:
        self.ents = ents


class FakeNerModel:
    def __init__(self, rules: list[tuple[str, str]]) -> None:
        self.rules = rules

    def __call__(self, text: str) -> FakeDoc:
        entities: list[FakeEntity] = []
        for value, label in self.rules:
            start = text.find(value)
            if start >= 0:
                entities.append(FakeEntity(start, start + len(value), label))
        return FakeDoc(entities)


class FakeSpacy:
    def __init__(self, model: FakeNerModel) -> None:
        self.model = model

    def load(self, model_name: str):
        return self.model


def workspace_temp_dir():
    return tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "tests")


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _normalized_extracted_text(text: str) -> str:
    normalized = text.replace("\u00a0", " ").replace("\u00ad", "-")
    normalized = normalized.replace("\u2013", "-").replace("\u2014", "-")
    normalized = " ".join(normalized.split())
    return normalized


def _write_pdf(path: Path, objects: list[bytes]) -> None:
    content = bytearray(b"%PDF-1.4\n")
    offsets = [0]

    for index, obj in enumerate(objects, start=1):
        offsets.append(len(content))
        content.extend(f"{index} 0 obj\n".encode("ascii"))
        content.extend(obj)
        content.extend(b"\nendobj\n")

    xref_start = len(content)
    content.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    content.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        content.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    content.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF\n"
        ).encode("ascii")
    )

    path.write_bytes(content)


def write_text_pdf(path: Path, text: str) -> None:
    escaped_text = _escape_pdf_text(text)
    stream = f"BT /F1 12 Tf 72 720 Td ({escaped_text}) Tj ET\n".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(stream)).encode("ascii")
        + b" >>\nstream\n"
        + stream
        + b"endstream",
    ]
    _write_pdf(path, objects)


def write_text_pdf_lines(path: Path, lines: list[str]) -> None:
    commands = ["BT /F1 12 Tf 14 TL 72 720 Td"]
    for line in lines:
        commands.append(f"({_escape_pdf_text(line)}) Tj")
        commands.append("T*")
    commands.append("ET")
    stream = ("\n".join(commands) + "\n").encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(stream)).encode("ascii")
        + b" >>\nstream\n"
        + stream
        + b"endstream",
    ]
    _write_pdf(path, objects)


def write_blank_pdf(path: Path) -> None:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << >> >>"
        ),
    ]
    _write_pdf(path, objects)


def write_fitz_text_pdf(path: Path, lines: list[str]) -> None:
    import fitz

    document = fitz.open()
    page = document.new_page()
    y = 72
    for line in lines:
        page.insert_text((72, y), line, fontsize=12)
        y += 18
    document.save(path)
    document.close()


def unicode_test_font_path() -> Path | None:
    for font_path in (
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/calibri.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
    ):
        if font_path.exists():
            return font_path
    return None


def write_fitz_unicode_text_pdf(path: Path, lines: list[str]) -> bool:
    import fitz

    font_path = unicode_test_font_path()
    if font_path is None:
        return False
    document = fitz.open()
    page = document.new_page()
    page.insert_font(fontname="stage24unicode", fontfile=str(font_path))
    y = 72
    for line in lines:
        page.insert_text((72, y), line, fontsize=12, fontname="stage24unicode")
        y += 18
    document.save(path)
    document.close()
    return True


class PdfIoTests(unittest.TestCase):
    def test_reads_simple_text_based_pdf_with_synthetic_data(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.pdf"
            source_text = "Contact tester@example.test on 2026-06-01."
            write_text_pdf(source_path, source_text)

            self.assertEqual(read_pdf_file(source_path).strip(), source_text)
            self.assertEqual(extract_text(source_path).strip(), source_text)

    def test_pdf_without_extractable_text_fails_clearly(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "blank.pdf"
            write_blank_pdf(source_path)

            with self.assertRaisesRegex(ValueError, "no extractable text"):
                read_pdf_file(source_path)

    def test_pdf_output_filename_is_anon_txt(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.pdf"
            write_text_pdf(source_path, "Synthetic PDF content.")

            self.assertEqual(
                build_anonymized_pdf_txt_path(source_path),
                Path(temp_dir) / "document_ANON.txt",
            )
            self.assertEqual(
                save_anonymized_copy(source_path, "Anonymized PDF text."),
                str(Path(temp_dir) / "document_ANON.txt"),
            )
            self.assertEqual(
                build_anonymized_pdf_path(source_path),
                Path(temp_dir) / "document_ANON.pdf",
            )
            self.assertEqual(
                build_pdf_review_path(source_path),
                Path(temp_dir) / "document_ANON_REVIEW.pdf",
            )
            self.assertEqual(
                build_pdf_visual_path(source_path),
                Path(temp_dir) / "document_ANON_VISUAL.pdf",
            )
            self.assertEqual(
                build_review_checklist_path(source_path),
                Path(temp_dir) / "document_REVIEW_CHECKLIST.txt",
            )
            self.assertEqual(
                build_original_redacted_pdf_path(source_path),
                Path(temp_dir) / "document_ORIGINAL_REDACTED.pdf",
            )

    def test_saves_pdf_anonymized_text_as_txt_copy(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.pdf"
            write_text_pdf(source_path, "Contact tester@example.test.")

            output_path = save_anonymized_pdf_txt_copy(
                source_path, "Contact [EMAIL]."
            )

            self.assertEqual(output_path, Path(temp_dir) / "document_ANON.txt")
            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                "Contact [EMAIL].",
            )

    def test_original_pdf_file_is_not_modified(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.pdf"
            write_text_pdf(source_path, "Original synthetic value: tester@example.test.")
            original_bytes = source_path.read_bytes()

            save_anonymized_pdf_txt_copy(source_path, "Original synthetic value: [EMAIL].")

            self.assertEqual(source_path.read_bytes(), original_bytes)

    def test_anonymizes_pdf_file_and_writes_txt_visual_and_auxiliary_review_pdf(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.pdf"
            source_email = "safe@example.test"
            write_text_pdf(
                source_path,
                f"{source_email} 00000000000 +48 123 456 789 2026-06-01",
            )

            output_path, counters = anonymize_pdf_file(source_path)
            visual_pdf_path = Path(temp_dir) / "document_ANON_VISUAL.pdf"
            review_pdf_path = Path(temp_dir) / "document_ANON_REVIEW.pdf"
            checklist_path = Path(temp_dir) / "document_REVIEW_CHECKLIST.txt"

            self.assertEqual(output_path, Path(temp_dir) / "document_ANON.txt")
            self.assertEqual(
                output_path.read_text(encoding="utf-8").strip(),
                "[EMAIL] [PESEL] [TELEFON] [DATA]",
            )
            self.assertEqual(
                counters, {"EMAIL": 1, "PESEL": 1, "TELEFON": 1, "DATA": 1}
            )
            self.assertTrue(visual_pdf_path.exists())
            self.assertTrue(review_pdf_path.exists())
            self.assertTrue(checklist_path.exists())
            self.assertFalse((Path(temp_dir) / "document_ORIGINAL_REDACTED.pdf").exists())
            self.assert_redacted_pdf_does_not_expose_text(
                visual_pdf_path,
                (source_email, "00000000000", "+48 123 456 789", "2026-06-01"),
            )
            self.assert_pdf_exposes_text(
                review_pdf_path,
                ("Source page 1", "[EMAIL]", "[PESEL]", "[TELEFON]", "[DATA]"),
            )
            self.assert_redacted_pdf_does_not_expose_text(
                review_pdf_path,
                (source_email, "00000000000", "+48 123 456 789", "2026-06-01"),
            )
            report_text = (Path(temp_dir) / "document_RAPORT.txt").read_text(
                encoding="utf-8"
            )
            checklist_text = checklist_path.read_text(encoding="utf-8")
            self.assertIn("PDF text extraction used: text_layer", report_text)
            self.assertIn("Visual PDF created: yes", report_text)
            self.assertIn("Visual PDF output: document_ANON_VISUAL.pdf", report_text)
            self.assertIn("Redaction mapping: word_coordinates", report_text)
            self.assertIn("Review PDF created: yes", report_text)
            self.assertIn("Review PDF type: rebuilt_from_anonymized_text", report_text)
            self.assertIn("Layout-preserving original redaction used: yes", report_text)
            self.assertIn("Review checklist created: yes", report_text)
            self.assertIn("Review checklist output: document_REVIEW_CHECKLIST.txt", report_text)
            self.assertIn("Review PDF note: rebuilt from anonymized text", report_text)
            self.assertIn("Source file: document.pdf", checklist_text)
            self.assertIn("PDF text extraction mode: text_layer", checklist_text)
            self.assertIn("Main visual PDF created: yes", checklist_text)
            self.assertIn("Main visual PDF output: document_ANON_VISUAL.pdf", checklist_text)
            self.assertIn("Main visual PDF mapping: word_coordinates", checklist_text)
            self.assertIn("PDF review PDF layout: not_layout_preserving", checklist_text)
            self.assertIn("PDF review PDF suitability: auxiliary simple text review only", checklist_text)
            self.assertIn("Source page 1:", checklist_text)
            self.assertIn("[EMAIL] x1", checklist_text)
            self.assertIn("[PESEL] x1", checklist_text)
            self.assertNotIn(source_email, checklist_text)
            self.assertNotIn(str(source_path), checklist_text)

    def test_pdf_dictionary_path_flow_replaces_terms(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_term = "Person One Example"
            dictionary_path = Path(temp_dir) / "sensitive_terms.txt"
            dictionary_path.write_text(
                f"{source_term} = [IMIE NAZWISKO]\n",
                encoding="utf-8",
            )
            source_path = Path(temp_dir) / "document.pdf"
            write_text_pdf(
                source_path,
                f"{source_term} contacted tester@example.test.",
            )

            output_path, counters = anonymize_pdf_file(
                source_path,
                sensitive_terms_path=dictionary_path,
            )
            report_text = (Path(temp_dir) / "document_RAPORT.txt").read_text(
                encoding="utf-8"
            )

            self.assertEqual(output_path, Path(temp_dir) / "document_ANON.txt")
            self.assertEqual(
                output_path.read_text(encoding="utf-8").strip(),
                "[IMIE NAZWISKO] contacted [EMAIL].",
            )
            self.assertEqual(counters, {"IMIE NAZWISKO": 1, "EMAIL": 1})
            self.assertIn("Dictionary status: loaded", report_text)
            self.assertIn("PDF redaction status: completed", report_text)
            self.assertIn("PDF true redaction used: yes", report_text)
            self.assertIn("Visual PDF output: document_ANON_VISUAL.pdf", report_text)
            self.assertIn("Review PDF created: yes", report_text)
            self.assertNotIn(source_term, report_text)
            self.assert_redacted_pdf_does_not_expose_text(
                Path(temp_dir) / "document_ANON_VISUAL.pdf",
                (source_term, "tester@example.test"),
            )
            self.assert_redacted_pdf_does_not_expose_text(
                Path(temp_dir) / "document_ANON_REVIEW.pdf",
                (source_term, "tester@example.test"),
            )

    def test_pdf_result_does_not_return_map_or_source_values(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "safe_input.pdf"
            source_values = {
                "safe@example.test",
                "00000000000",
                "+48 123 456 789",
                "2026-06-01",
            }
            write_text_pdf(
                source_path,
                "safe@example.test 00000000000 +48 123 456 789 2026-06-01",
            )

            output_path, counters = anonymize_pdf_file(source_path)

            returned_text = repr((output_path, counters))
            output_text = output_path.read_text(encoding="utf-8")
            for source_value in source_values:
                self.assertNotIn(source_value, returned_text)
                self.assertNotIn(source_value, repr(counters))
                self.assertNotIn(source_value, output_text)

            self.assertEqual(
                counters, {"EMAIL": 1, "PESEL": 1, "TELEFON": 1, "DATA": 1}
            )
            self.assertTrue(all(isinstance(count, int) for count in counters.values()))

    def test_pdf_redaction_handles_person_name_typo_pattern(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.pdf"
            typo_value = "Jan-Kowalski Nowak"
            write_text_pdf(source_path, f"Reviewer {typo_value}.")

            output_path, counters = anonymize_pdf_file(source_path)
            visual_pdf_path = Path(temp_dir) / "document_ANON_VISUAL.pdf"
            review_pdf_path = Path(temp_dir) / "document_ANON_REVIEW.pdf"
            report_text = (Path(temp_dir) / "document_RAPORT.txt").read_text(
                encoding="utf-8"
            )

            self.assertEqual(output_path.read_text(encoding="utf-8").strip(), "Reviewer [PERSON_NAME_TYPO].")
            self.assertEqual(counters, {"PERSON_NAME_TYPO": 1})
            self.assertTrue(visual_pdf_path.exists())
            self.assertTrue(review_pdf_path.exists())
            self.assertIn("PDF redaction status: completed", report_text)
            self.assertIn("* PERSON_NAME_TYPO: 1", report_text)
            self.assert_pdf_exposes_text(review_pdf_path, ("[PERSON_NAME_TYPO]",))
            self.assert_redacted_pdf_does_not_expose_text(visual_pdf_path, (typo_value,))
            self.assert_redacted_pdf_does_not_expose_text(review_pdf_path, (typo_value,))

    def test_pdf_redaction_does_not_cover_plain_address_words(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.pdf"
            write_fitz_text_pdf(
                source_path,
                [
                    "Adres Testowy Warszawa",
                    "Email safe@example.test",
                ],
            )

            output_path, counters = anonymize_pdf_file(source_path)
            visual_pdf_path = Path(temp_dir) / "document_ANON_VISUAL.pdf"
            review_pdf_path = Path(temp_dir) / "document_ANON_REVIEW.pdf"

            self.assertEqual(counters, {"EMAIL": 1})
            self.assertIn(
                "Adres Testowy Warszawa",
                output_path.read_text(encoding="utf-8"),
            )
            self.assert_redacted_pdf_does_not_expose_text(
                visual_pdf_path,
                ("safe@example.test",),
            )
            self.assert_pdf_exposes_text(
                visual_pdf_path,
                ("Adres", "Testowy", "Warszawa"),
            )
            self.assert_redacted_pdf_does_not_expose_text(
                review_pdf_path,
                ("safe@example.test",),
            )
            self.assert_pdf_exposes_text(
                review_pdf_path,
                ("Adres", "Testowy", "Warszawa"),
            )

    def test_visual_pdf_skips_single_token_health_false_positive_people(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "health_terms.pdf"
            safe_terms = (
                "Ospa",
                "Salmonella",
                "Streptococcus",
                "GUS",
                "WHO",
                "ECDC",
                "POLIO",
                "Haemophilus",
                "WZW B",
                "Polsce",
            )
            write_fitz_text_pdf(
                source_path,
                [
                    " ".join(safe_terms),
                    "Person Jan Kowalski",
                    "Person Anna Nowak",
                    "Email safe@example.test",
                ],
            )
            model = FakeNerModel(
                [
                    ("Ospa", "persName"),
                    ("Salmonella", "persName"),
                    ("Streptococcus", "persName"),
                    ("GUS", "orgName"),
                    ("WHO", "orgName"),
                    ("ECDC", "orgName"),
                    ("POLIO", "persName"),
                    ("Haemophilus", "persName"),
                    ("WZW B", "persName"),
                    ("Polsce", "persName"),
                    ("Jan Kowalski", "persName"),
                    ("Anna Nowak", "persName"),
                ]
            )

            with patch("ner._spacy_module", return_value=FakeSpacy(model)):
                output_path, counters = anonymize_pdf_file(source_path, use_ner=True)

            visual_pdf_path = Path(temp_dir) / "health_terms_ANON_VISUAL.pdf"
            report_text = (Path(temp_dir) / "health_terms_RAPORT.txt").read_text(
                encoding="utf-8"
            )
            output_text = output_path.read_text(encoding="utf-8")

            for safe_term in safe_terms:
                self.assertIn(safe_term, output_text)
            self.assertEqual(counters["NER_PERSON"], 2)
            self.assertIn("* PUBLIC_INSTITUTION_PHRASE: 3", report_text)
            self.assertIn("* SCIENTIFIC_NAME: 6", report_text)
            self.assertIn("* SINGLE_TOKEN_PERSON_SKIPPED: 1", report_text)
            self.assert_pdf_exposes_text(visual_pdf_path, safe_terms)
            self.assert_redacted_pdf_does_not_expose_text(
                visual_pdf_path,
                ("Jan Kowalski", "Anna Nowak", "safe@example.test"),
            )

    def test_visual_pdf_applies_allowlist_before_redaction_rectangles(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "unicode_health_terms.pdf"
            safe_terms = (
                "Wojew\u00f3dzkiej Stacji Sanitarno-Epidemiologicznej",
                "ojew\u00f3dzkiej Stacji Sanitarno-Epidemiologicznej",
                "odra",
                "WZW B",
                "POLIO",
                "Haemophilus",
                "Neisseria",
                "B\u0141ONICA",
                "T\u0119\u017cec-B\u0142onica",
            )
            created = write_fitz_unicode_text_pdf(
                source_path,
                [
                    safe_terms[0],
                    safe_terms[1],
                    " ".join(safe_terms[2:]),
                    "mgr inz. Adam Testowy",
                    "Participant Jan",
                    "Kowalski signed",
                    "Person Anna Nowak",
                    "Email safe@example.test",
                    "PESEL 00000000000",
                    "Kontakt tel. 123 456 789",
                ],
            )
            if not created:
                self.skipTest("No Unicode-capable test font available")
            model = FakeNerModel(
                [
                    (safe_terms[0], "orgName"),
                    (safe_terms[1], "orgName"),
                    ("odra", "persName"),
                    ("WZW B", "persName"),
                    ("POLIO", "persName"),
                    ("Haemophilus", "persName"),
                    ("Neisseria", "persName"),
                    ("B\u0141ONICA", "persName"),
                    ("T\u0119\u017cec-B\u0142onica", "persName"),
                    ("Adam Testowy", "persName"),
                    ("Jan Kowalski", "persName"),
                    ("Anna Nowak", "persName"),
                ]
            )

            with patch("ner._spacy_module", return_value=FakeSpacy(model)):
                output_path, counters = anonymize_pdf_file(source_path, use_ner=True)

            visual_pdf_path = Path(temp_dir) / "unicode_health_terms_ANON_VISUAL.pdf"
            report_text = (
                Path(temp_dir) / "unicode_health_terms_RAPORT.txt"
            ).read_text(encoding="utf-8")
            output_text = output_path.read_text(encoding="utf-8")
            normalized_output_text = _normalized_extracted_text(output_text)

            for safe_term in (
                "Stacji Sanitarno-Epidemiologicznej",
                "odra",
                "WZW B",
                "POLIO",
                "Haemophilus",
                "Neisseria",
            ):
                self.assertIn(safe_term, normalized_output_text)
            self.assertEqual(counters["NER_PERSON"], 3)
            self.assertEqual(counters["EMAIL"], 1)
            self.assertEqual(counters["PESEL"], 1)
            self.assertEqual(counters["TELEFON"], 1)
            self.assertIn("* PUBLIC_INSTITUTION_PHRASE: 2", report_text)
            self.assertIn("* SCIENTIFIC_NAME: 7", report_text)
            self.assert_pdf_exposes_normalized_text(
                visual_pdf_path,
                (
                    "Stacji Sanitarno-Epidemiologicznej",
                    "odra",
                    "WZW B",
                    "POLIO",
                    "Haemophilus",
                    "Neisseria",
                ),
            )
            self.assert_redacted_pdf_does_not_expose_text(
                visual_pdf_path,
                (
                    "Adam Testowy",
                    "Jan",
                    "Kowalski",
                    "Anna Nowak",
                    "safe@example.test",
                    "00000000000",
                    "123 456 789",
                ),
            )

    def test_visual_span_builder_excludes_unicode_allowlisted_ner_terms(self) -> None:
        safe_terms = (
            "Wojew\u00f3dzkiej Stacji Sanitarno-Epidemiologicznej",
            "Wojew\u00f3dzka Stacja Sanitarno\u2013Epidemiologiczna",
            "ojew\u00f3dzkiej Stacji Sanitarno-Epidemiologicznej",
            "odra",
            "WZW B",
            "POLIO",
            "Haemophilus",
            "Haemophilus influenzae",
            "Neisseria",
            "Neisseria meningitidis",
            "B\u0141ONICA",
            "B\u0142onica",
            "T\u0119\u017cec-B\u0142onica",
            "B\u0142onica-T\u0119\u017cec-Krztusiec",
        )
        strong_terms = (
            "Jan Kowalski",
            "Anna Nowak",
            "mgr in\u017c. Adam Testowy",
            "safe@example.test",
            "00000000000",
            "tel. 123 456 789",
        )
        page_text = "\n".join([*safe_terms, *strong_terms])
        model = FakeNerModel(
            [(term, "orgName") for term in safe_terms[:3]]
            + [(term, "persName") for term in safe_terms[3:]]
            + [
                ("Jan Kowalski", "persName"),
                ("Anna Nowak", "persName"),
                ("Adam Testowy", "persName"),
            ]
        )

        with patch("ner._spacy_module", return_value=FakeSpacy(model)):
            from ner import prepare_ner_context

            context = prepare_ner_context(enabled=True)
            spans = _pdf_detection_spans_for_word_pages(
                [PdfWordPage(page_number=1, text=page_text, words=())],
                sensitive_terms=None,
                ner_context=context,
            )

        span_values = [page_text[span.start_offset:span.end_offset] for span in spans]
        for safe_term in safe_terms:
            self.assertNotIn(safe_term, span_values)
        for redacted_term in (
            "Jan Kowalski",
            "Anna Nowak",
            "Adam Testowy",
            "safe@example.test",
            "00000000000",
            "123 456 789",
        ):
            self.assertIn(redacted_term, span_values)

    def test_visual_span_builder_excludes_short_domain_terms_for_all_ner_labels(self) -> None:
        safe_terms = (
            "Odra",
            "WZW B",
            "POLIO",
            "Haemophilus",
            "B\u0141ONICA",
            "T\u0119\u017cec-B\u0142onica",
        )
        labels_to_try = ("persName", "orgName", "placeName", "MISC")

        for model_label in labels_to_try:
            with self.subTest(model_label=model_label):
                page_text = "\n".join(
                    [
                        *safe_terms,
                        "Jan Kowalski",
                        "mgr in\u017c. Adam Testowy",
                        "Kontakt tel. 123 456 789",
                        "safe@example.test",
                        "00000000000",
                    ]
                )
                model = FakeNerModel(
                    [(term, model_label) for term in safe_terms]
                    + [
                        ("Jan Kowalski", "persName"),
                        ("Adam Testowy", "persName"),
                    ]
                )

                with patch("ner._spacy_module", return_value=FakeSpacy(model)):
                    from ner import prepare_ner_context

                    context = prepare_ner_context(enabled=True)
                    spans = _pdf_detection_spans_for_word_pages(
                        [PdfWordPage(page_number=1, text=page_text, words=())],
                        sensitive_terms=None,
                        ner_context=context,
                    )

                span_values = [
                    page_text[span.start_offset:span.end_offset] for span in spans
                ]
                for safe_term in safe_terms:
                    self.assertNotIn(safe_term, span_values)
                for redacted_term in (
                    "Jan Kowalski",
                    "Adam Testowy",
                    "123 456 789",
                    "safe@example.test",
                    "00000000000",
                ):
                    self.assertIn(redacted_term, span_values)

    def test_visual_pdf_keeps_public_institution_phrase_but_dictionary_can_override(self) -> None:
        with workspace_temp_dir() as temp_dir:
            public_source = Path(temp_dir) / "public.pdf"
            public_phrase = "Minister Zdrowia"
            write_fitz_text_pdf(public_source, [public_phrase, "Email safe@example.test"])
            model = FakeNerModel([(public_phrase, "orgName")])

            with patch("ner._spacy_module", return_value=FakeSpacy(model)):
                public_output, public_counters = anonymize_pdf_file(
                    public_source,
                    use_ner=True,
                )

            public_visual = Path(temp_dir) / "public_ANON_VISUAL.pdf"
            public_report = (Path(temp_dir) / "public_RAPORT.txt").read_text(
                encoding="utf-8"
            )
            self.assertNotIn("NER_ORG", public_counters)
            self.assertIn(public_phrase, public_output.read_text(encoding="utf-8"))
            self.assertIn("* PUBLIC_INSTITUTION_PHRASE: 1", public_report)
            self.assert_pdf_exposes_text(public_visual, (public_phrase,))

            dictionary_path = Path(temp_dir) / "sensitive_terms.txt"
            dictionary_path.write_text(
                f"{public_phrase} = [PRIVATE_ORG]\n",
                encoding="utf-8",
            )
            private_source = Path(temp_dir) / "private.pdf"
            write_fitz_text_pdf(private_source, [public_phrase])

            private_output, private_counters = anonymize_pdf_file(
                private_source,
                sensitive_terms_path=dictionary_path,
            )

            self.assertEqual(private_counters, {"PRIVATE_ORG": 1})
            self.assertEqual(
                private_output.read_text(encoding="utf-8").strip(),
                "[PRIVATE_ORG]",
            )
            self.assert_redacted_pdf_does_not_expose_text(
                Path(temp_dir) / "private_ANON_VISUAL.pdf",
                (public_phrase,),
            )

    def test_visual_pdf_keeps_table_numbers_but_redacts_explicit_contact_phone(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "phone_table.pdf"
            write_fitz_text_pdf(
                source_path,
                [
                    "Tabela zachorowania 43 595 oraz 123 456 789",
                    "Kontakt tel. 987 654 321",
                ],
            )

            output_path, counters = anonymize_pdf_file(source_path)

            visual_pdf_path = Path(temp_dir) / "phone_table_ANON_VISUAL.pdf"
            report_text = (Path(temp_dir) / "phone_table_RAPORT.txt").read_text(
                encoding="utf-8"
            )
            checklist_text = (
                Path(temp_dir) / "phone_table_REVIEW_CHECKLIST.txt"
            ).read_text(encoding="utf-8")
            output_text = output_path.read_text(encoding="utf-8")

            self.assertEqual(counters, {"TELEFON": 1})
            self.assertIn("Tabela zachorowania 43 595 oraz 123 456 789", output_text)
            self.assertIn("Kontakt tel. [TELEFON]", output_text)
            self.assertIn("Weak phone-like numeric values skipped: 1", report_text)
            self.assertIn("Weak phone-like numeric values skipped: 1", checklist_text)
            self.assert_pdf_exposes_text(visual_pdf_path, ("43", "595", "123 456 789"))
            self.assert_redacted_pdf_does_not_expose_text(
                visual_pdf_path,
                ("987 654 321",),
            )

    def test_pdf_redaction_reports_broad_ner_outside_default_safe_scope(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "stage23_synthetic.pdf"
            deterministic_source_values = (
                "Jan-Kowalski Kowalski",
                "safe@example.test",
                "+48 123 456 789",
                "00000000000",
                "2026-06-01",
            )
            write_text_pdf_lines(
                source_path,
                [
                    "Patient Jan-Kowalski Kowalski",
                    "Signature: Jan Nowakowski",
                    "Email safe@example.test",
                    "Phone +48 123 456 789",
                    "PESEL 00000000000",
                    "Date 2026-06-01",
                    "Address: Testowa 12, 00-001 Warszawa",
                    "Organization: Example Test Clinic",
                ],
            )
            model = FakeNerModel(
                [
                    ("Jan Nowakowski", "persName"),
                    ("Example Test Clinic", "orgName"),
                    ("Warszawa", "placeName"),
                ]
            )

            with patch("ner._spacy_module", return_value=FakeSpacy(model)):
                output_path, counters = anonymize_pdf_file(
                    source_path,
                    use_ner=True,
                    pdf_output_mode=PDF_OUTPUT_MODE_ORIGINAL_REDACTION,
                )

            report_text = (Path(temp_dir) / "stage23_synthetic_RAPORT.txt").read_text(
                encoding="utf-8"
            )
            redacted_pdf_path = Path(temp_dir) / "stage23_synthetic_ORIGINAL_REDACTED.pdf"

            self.assertTrue(redacted_pdf_path.exists())
            self.assertIn("[NER_ORG]", output_path.read_text(encoding="utf-8"))
            self.assertIn("[NER_LOCATION]", output_path.read_text(encoding="utf-8"))
            self.assertEqual(counters["PERSON_NAME_TYPO"], 1)
            self.assertEqual(counters["NER_PERSON"], 1)
            self.assertEqual(counters["NER_ORG"], 1)
            self.assertEqual(counters["NER_LOCATION"], 1)
            self.assertIn("PDF redaction status: completed_with_warnings", report_text)
            self.assertIn("PDF redaction scope: safe", report_text)
            self.assertIn("Layout-preserving original redaction used: yes", report_text)
            self.assertIn("Layout-preserving original redaction experimental: yes", report_text)
            self.assertIn("PDF detected categories:", report_text)
            self.assertIn("TXT anonymized categories:", report_text)
            self.assertIn("PDF redacted categories:", report_text)
            self.assertIn("Detected but not PDF-redacted categories:", report_text)
            self.assertIn("NER categories not PDF-redacted by current PDF scope:", report_text)
            self.assertIn(
                "PDF safe scope rule: NER_PERSON uses conservative exact-span redaction",
                report_text,
            )
            self.assertIn("* POSTAL_CODE: 1", report_text)
            self.assertIn("* NER_PERSON: 1", report_text)
            self.assertIn("* NER_ORG: 1", report_text)
            self.assertIn("* NER_LOCATION: 1", report_text)
            self.assertIn("PDF redaction warning:", report_text)
            self.assertIn(
                "PDF safe scope note: Safe PDF scope redacts conservative exact NER_PERSON spans by default;",
                report_text,
            )
            self.assert_redacted_pdf_does_not_expose_text(
                redacted_pdf_path,
                (*deterministic_source_values, "Jan Nowakowski"),
            )
            self.assert_pdf_exposes_text(
                redacted_pdf_path,
                ("Example Test Clinic", "Warszawa"),
            )

    def test_safe_pdf_redaction_reports_skipped_short_ner_person_span(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "short_person.pdf"
            write_fitz_text_pdf(
                source_path,
                [
                    "Witness Jan",
                    "Email safe@example.test",
                ],
            )
            model = FakeNerModel([("Jan", "persName")])

            with patch("ner._spacy_module", return_value=FakeSpacy(model)):
                output_path, counters = anonymize_pdf_file(
                    source_path,
                    use_ner=True,
                    pdf_output_mode=PDF_OUTPUT_MODE_ORIGINAL_REDACTION,
                )

            report_text = (Path(temp_dir) / "short_person_RAPORT.txt").read_text(
                encoding="utf-8"
            )
            redacted_pdf_path = Path(temp_dir) / "short_person_ORIGINAL_REDACTED.pdf"

            self.assertIn("[NER_PERSON]", output_path.read_text(encoding="utf-8"))
            self.assertEqual(counters["NER_PERSON"], 1)
            self.assertIn("PDF redaction scope: safe", report_text)
            self.assertIn("NER categories not PDF-redacted by current PDF scope:", report_text)
            self.assertIn("* NER_PERSON: 1", report_text)
            self.assertNotIn("PDF redacted categories:\n* NER_PERSON: 1", report_text)
            self.assert_redacted_pdf_does_not_expose_text(
                redacted_pdf_path,
                ("safe@example.test",),
            )

    def test_safe_original_redaction_skips_ner_person_split_across_lines(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "linebreak_person.pdf"
            write_fitz_text_pdf(
                source_path,
                [
                    "Participant Jan",
                    "Kowalski startowal w konkursie",
                    "Email safe@example.test",
                ],
            )
            model = FakeNerModel([("Jan Kowalski", "persName")])

            with patch("ner._spacy_module", return_value=FakeSpacy(model)):
                output_path, counters = anonymize_pdf_file(
                    source_path,
                    use_ner=True,
                    pdf_output_mode=PDF_OUTPUT_MODE_ORIGINAL_REDACTION,
                )

            report_text = (Path(temp_dir) / "linebreak_person_RAPORT.txt").read_text(
                encoding="utf-8"
            )
            redacted_pdf_path = Path(temp_dir) / "linebreak_person_ORIGINAL_REDACTED.pdf"

            self.assertIn("[NER_PERSON]", output_path.read_text(encoding="utf-8"))
            self.assertEqual(counters["NER_PERSON"], 1)
            self.assertIn("NER line-break person candidates handled: 1", report_text)
            blocks_line = next(
                line
                for line in report_text.splitlines()
                if line.startswith("PDF redaction blocks:")
            )
            block_count = int(blocks_line.rsplit(":", 1)[1].strip())
            self.assertLessEqual(block_count, 3)
            self.assert_redacted_pdf_does_not_expose_text(
                redacted_pdf_path,
                ("safe@example.test", "Jan", "Kowalski"),
            )

    def test_default_visual_redaction_uses_exact_ner_spans_without_word_explosion(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "visual_ner.pdf"
            write_fitz_text_pdf(
                source_path,
                [
                    "Header Alpha Alpha Alpha",
                    "Organization Example Test Clinic",
                    "Location Warszawa",
                    "Email safe@example.test",
                    "Footer Alpha Alpha Alpha",
                ],
            )
            model = FakeNerModel(
                [
                    ("Example Test Clinic", "orgName"),
                    ("Warszawa", "placeName"),
                ]
            )

            with patch("ner._spacy_module", return_value=FakeSpacy(model)):
                output_path, counters = anonymize_pdf_file(
                    source_path,
                    use_ner=True,
                    pdf_output_mode=PDF_OUTPUT_MODE_VISUAL,
                )

            report_text = (Path(temp_dir) / "visual_ner_RAPORT.txt").read_text(
                encoding="utf-8"
            )
            visual_pdf_path = Path(temp_dir) / "visual_ner_ANON_VISUAL.pdf"

            self.assertTrue(visual_pdf_path.exists())
            self.assertIn("[NER_ORG]", output_path.read_text(encoding="utf-8"))
            self.assertIn("[NER_LOCATION]", output_path.read_text(encoding="utf-8"))
            self.assertEqual(counters["NER_ORG"], 1)
            self.assertEqual(counters["NER_LOCATION"], 1)
            self.assertIn("Visual PDF type: original_layout_word_coordinate_redaction", report_text)
            self.assertIn("Redaction mapping: word_coordinates", report_text)
            self.assertIn("* NER_ORG: 1", report_text)
            self.assertIn("* NER_LOCATION: 1", report_text)
            blocks_line = next(
                line
                for line in report_text.splitlines()
                if line.startswith("PDF redaction blocks:")
            )
            block_count = int(blocks_line.rsplit(":", 1)[1].strip())
            self.assertLessEqual(block_count, 4)
            self.assert_redacted_pdf_does_not_expose_text(
                visual_pdf_path,
                ("Example Test Clinic", "Warszawa", "safe@example.test"),
            )
            self.assert_pdf_exposes_text(visual_pdf_path, ("Header", "Alpha", "Footer"))

    def test_default_visual_redaction_handles_person_name_split_across_lines(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "visual_linebreak_person.pdf"
            write_fitz_text_pdf(
                source_path,
                [
                    "Participant Jan",
                    "Kowalski signed",
                    "Footer visible",
                ],
            )
            model = FakeNerModel([("Jan Kowalski", "persName")])

            with patch("ner._spacy_module", return_value=FakeSpacy(model)):
                output_path, counters = anonymize_pdf_file(source_path, use_ner=True)

            visual_pdf_path = Path(temp_dir) / "visual_linebreak_person_ANON_VISUAL.pdf"
            report_text = (
                Path(temp_dir) / "visual_linebreak_person_RAPORT.txt"
            ).read_text(encoding="utf-8")

            self.assertIn("[NER_PERSON]", output_path.read_text(encoding="utf-8"))
            self.assertEqual(counters["NER_PERSON"], 1)
            self.assertIn("NER line-break person candidates handled: 1", report_text)
            self.assert_redacted_pdf_does_not_expose_text(
                visual_pdf_path,
                ("Jan", "Kowalski"),
            )
            self.assert_pdf_exposes_text(visual_pdf_path, ("Footer",))

    def test_strict_pdf_redaction_scope_includes_selected_ner_terms(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "strict_scope.pdf"
            write_text_pdf_lines(
                source_path,
                [
                    "Email safe@example.test",
                    "Organization: Example Test Clinic",
                    "Location: Warszawa",
                ],
            )
            model = FakeNerModel(
                [
                    ("Example Test Clinic", "orgName"),
                    ("Warszawa", "placeName"),
                ]
            )

            with patch("ner._spacy_module", return_value=FakeSpacy(model)):
                output_path, counters = anonymize_pdf_file(
                    source_path,
                    use_ner=True,
                    pdf_redaction_scope="strict",
                    pdf_output_mode=PDF_OUTPUT_MODE_ORIGINAL_REDACTION,
                )

            report_text = (Path(temp_dir) / "strict_scope_RAPORT.txt").read_text(
                encoding="utf-8"
            )
            redacted_pdf_path = Path(temp_dir) / "strict_scope_ORIGINAL_REDACTED.pdf"

            self.assertIn("[NER_ORG]", output_path.read_text(encoding="utf-8"))
            self.assertEqual(counters["NER_ORG"], 1)
            self.assertEqual(counters["NER_LOCATION"], 1)
            self.assertIn("PDF redaction scope: strict", report_text)
            self.assertIn("PDF strict scope warning:", report_text)
            self.assertIn("* NER_ORG: 1", report_text)
            self.assertIn("* NER_LOCATION: 1", report_text)
            self.assertNotIn("PDF safe scope note:", report_text)
            self.assert_redacted_pdf_does_not_expose_text(
                redacted_pdf_path,
                ("safe@example.test", "Example Test Clinic", "Warszawa"),
            )

    def test_pdf_redaction_deduplicates_repeated_exact_terms(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.pdf"
            write_fitz_text_pdf(source_path, ["Organization: Example Test Clinic"])

            result = save_redacted_pdf_copy(
                source_path,
                extra_redaction_terms=[
                    ("NER_ORG", "Example Test Clinic"),
                    ("NER_ORG", "Example Test Clinic"),
                    ("NER_ORG", "Example Test Clinic"),
                ],
            )

            self.assertEqual(result["redaction_count"], 1)
            self.assertEqual(result["counters"], {"NER_ORG": 1})
            self.assertEqual(result["output_name"], "document_ORIGINAL_REDACTED.pdf")

    def test_rebuilt_review_pdf_contains_only_anonymized_text(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "review.pdf"
            write_text_pdf_lines(
                source_path,
                [
                    "Contact first@example.test",
                    "Date 2026-06-01",
                ],
            )

            output_path, counters = anonymize_pdf_file(source_path)
            visual_pdf_path = Path(temp_dir) / "review_ANON_VISUAL.pdf"
            review_pdf_path = Path(temp_dir) / "review_ANON_REVIEW.pdf"
            original_redacted_path = Path(temp_dir) / "review_ORIGINAL_REDACTED.pdf"
            report_text = (Path(temp_dir) / "review_RAPORT.txt").read_text(
                encoding="utf-8"
            )

            self.assertEqual(output_path, Path(temp_dir) / "review_ANON.txt")
            self.assertEqual(counters, {"EMAIL": 1, "DATA": 1})
            self.assertTrue(visual_pdf_path.exists())
            self.assertTrue(review_pdf_path.exists())
            self.assertFalse(original_redacted_path.exists())
            self.assert_redacted_pdf_does_not_expose_text(
                visual_pdf_path,
                ("first@example.test", "2026-06-01"),
            )
            self.assert_pdf_exposes_text(
                review_pdf_path,
                ("Source page 1", "[EMAIL]", "[DATA]"),
            )
            self.assert_redacted_pdf_does_not_expose_text(
                review_pdf_path,
                ("first@example.test", "2026-06-01"),
            )
            self.assertIn("Review PDF type: rebuilt_from_anonymized_text", report_text)
            self.assertIn("Layout-preserving original redaction used: yes", report_text)

    def assert_redacted_pdf_does_not_expose_text(
        self,
        pdf_path: Path,
        source_values: tuple[str, ...],
    ) -> None:
        import fitz

        with fitz.open(pdf_path) as document:
            redacted_text = "\n".join(page.get_text("text") for page in document)
        redacted_bytes = pdf_path.read_bytes()
        for source_value in source_values:
            self.assertNotIn(source_value, redacted_text)
            self.assertNotIn(source_value.encode("utf-8"), redacted_bytes)

    def assert_pdf_exposes_text(
        self,
        pdf_path: Path,
        source_values: tuple[str, ...],
    ) -> None:
        import fitz

        with fitz.open(pdf_path) as document:
            redacted_text = "\n".join(page.get_text("text") for page in document)
        for source_value in source_values:
            self.assertIn(source_value, redacted_text)

    def assert_pdf_exposes_normalized_text(
        self,
        pdf_path: Path,
        source_values: tuple[str, ...],
    ) -> None:
        import fitz

        with fitz.open(pdf_path) as document:
            redacted_text = "\n".join(page.get_text("text") for page in document)
        normalized_text = _normalized_extracted_text(redacted_text)
        for source_value in source_values:
            self.assertIn(source_value, normalized_text)


if __name__ == "__main__":
    unittest.main()
