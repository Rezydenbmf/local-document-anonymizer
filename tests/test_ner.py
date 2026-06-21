"""Tests for optional local NER foundation."""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from docx import Document


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from anonymizer import anonymize_batch, anonymize_docx_file, anonymize_file
from ner import (
    DEFAULT_NER_MODEL,
    NER_STATUS_DEPENDENCY_MISSING,
    NER_STATUS_DISABLED,
    NER_STATUS_MODEL_MISSING,
    detect_entities,
    detect_ner_support,
    prepare_ner_context,
)


def workspace_temp_dir():
    return tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "tests")


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
    def __init__(self, model: FakeNerModel | None = None, error: Exception | None = None):
        self.model = model
        self.error = error

    def load(self, model_name: str):
        if self.error is not None:
            raise self.error
        return self.model


class NerFoundationTests(unittest.TestCase):
    def test_ner_detection_reports_disabled_status(self) -> None:
        status = detect_ner_support(enabled=False)

        self.assertEqual(status["status"], NER_STATUS_DISABLED)
        self.assertEqual(status["enabled"], False)

    def test_ner_detection_handles_missing_spacy_dependency(self) -> None:
        with patch("ner._spacy_module", return_value=None):
            status = detect_ner_support(enabled=True)

        self.assertEqual(status["status"], NER_STATUS_DEPENDENCY_MISSING)
        self.assertEqual(status["model_name"], DEFAULT_NER_MODEL)

    def test_ner_detection_handles_missing_polish_model(self) -> None:
        fake_spacy = FakeSpacy(error=OSError("model not found"))

        with patch("ner._spacy_module", return_value=fake_spacy):
            status = detect_ner_support(enabled=True)

        self.assertEqual(status["status"], NER_STATUS_MODEL_MISSING)
        self.assertEqual(status["warning"], "local NER model is missing")

    def test_entity_detection_maps_model_labels_to_internal_labels(self) -> None:
        model = FakeNerModel(
            [
                ("Person Example", "persName"),
                ("Example Org", "orgName"),
                ("Warsaw Example", "placeName"),
            ]
        )
        fake_spacy = FakeSpacy(model=model)

        with patch("ner._spacy_module", return_value=fake_spacy):
            context = prepare_ner_context(enabled=True)
            entities, counters = detect_entities(
                "Person Example works for Example Org in Warsaw Example.",
                context,
            )

        self.assertEqual([entity.label for entity in entities], [
            "NER_PERSON",
            "NER_ORG",
            "NER_LOCATION",
        ])
        self.assertEqual(counters["NER_PERSON"], 1)
        self.assertEqual(counters["NER_ORG"], 1)
        self.assertEqual(counters["NER_LOCATION"], 1)

    def test_person_left_expansion_masks_simple_capitalized_previous_token(self) -> None:
        person_first = "Jan"
        person_last = "Kowalski"
        model = FakeNerModel([(person_last, "persName")])

        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.txt"
            source_path.write_text(
                f"{person_first} {person_last} wrote a note.",
                encoding="utf-8",
            )

            with patch("ner._spacy_module", return_value=FakeSpacy(model=model)):
                output_path, counters = anonymize_file(source_path, use_ner=True)

            output_text = output_path.read_text(encoding="utf-8")
            report_text = (Path(temp_dir) / "document_RAPORT.txt").read_text(
                encoding="utf-8"
            )

        self.assertEqual(output_text, "[NER_PERSON] wrote a note.")
        self.assertEqual(counters["NER_PERSON"], 1)
        self.assertNotIn(person_first, report_text)
        self.assertNotIn(person_last, report_text)

    def test_person_left_expansion_does_not_cross_lowercase_previous_word(self) -> None:
        model = FakeNerModel([("Kowalski", "persName")])

        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.txt"
            source_path.write_text("pan Kowalski wrote a note.", encoding="utf-8")

            with patch("ner._spacy_module", return_value=FakeSpacy(model=model)):
                output_path, counters = anonymize_file(source_path, use_ner=True)

            output_text = output_path.read_text(encoding="utf-8")

        self.assertEqual(output_text, "pan [NER_PERSON] wrote a note.")
        self.assertEqual(counters["NER_PERSON"], 1)

    def test_person_left_expansion_does_not_cross_placeholder(self) -> None:
        model = FakeNerModel([("Kowalski", "persName")])

        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.txt"
            source_path.write_text("[EMAIL] Kowalski wrote a note.", encoding="utf-8")

            with patch("ner._spacy_module", return_value=FakeSpacy(model=model)):
                output_path, counters = anonymize_file(source_path, use_ner=True)

            output_text = output_path.read_text(encoding="utf-8")

        self.assertEqual(output_text, "[EMAIL] [NER_PERSON] wrote a note.")
        self.assertEqual(counters["NER_PERSON"], 1)

    def test_person_left_expansion_does_not_cross_punctuation(self) -> None:
        model = FakeNerModel([("Kowalski", "persName")])

        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.txt"
            source_path.write_text("Jan, Kowalski wrote a note.", encoding="utf-8")

            with patch("ner._spacy_module", return_value=FakeSpacy(model=model)):
                output_path, counters = anonymize_file(source_path, use_ner=True)

            output_text = output_path.read_text(encoding="utf-8")

        self.assertEqual(output_text, "Jan, [NER_PERSON] wrote a note.")
        self.assertEqual(counters["NER_PERSON"], 1)

    def test_person_left_expansion_does_not_cross_all_caps_token(self) -> None:
        model = FakeNerModel([("Kowalski", "persName")])

        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.txt"
            source_path.write_text("ACME Kowalski wrote a note.", encoding="utf-8")

            with patch("ner._spacy_module", return_value=FakeSpacy(model=model)):
                output_path, counters = anonymize_file(source_path, use_ner=True)

            output_text = output_path.read_text(encoding="utf-8")

        self.assertEqual(output_text, "ACME [NER_PERSON] wrote a note.")
        self.assertEqual(counters["NER_PERSON"], 1)

    def test_person_left_expansion_does_not_cross_line_break(self) -> None:
        model = FakeNerModel([("Kowalski", "persName")])

        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.txt"
            source_path.write_text("Jan\nKowalski wrote a note.", encoding="utf-8")

            with patch("ner._spacy_module", return_value=FakeSpacy(model=model)):
                output_path, counters = anonymize_file(source_path, use_ner=True)

            output_text = output_path.read_text(encoding="utf-8")

        self.assertEqual(output_text, "Jan\n[NER_PERSON] wrote a note.")
        self.assertEqual(counters["NER_PERSON"], 1)

    def test_existing_full_person_detection_still_masks_original_span(self) -> None:
        person = "Anna Nowak"
        model = FakeNerModel([(person, "persName")])

        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.txt"
            source_path.write_text(f"{person} wrote a note.", encoding="utf-8")

            with patch("ner._spacy_module", return_value=FakeSpacy(model=model)):
                output_path, counters = anonymize_file(source_path, use_ner=True)

            output_text = output_path.read_text(encoding="utf-8")

        self.assertEqual(output_text, "[NER_PERSON] wrote a note.")
        self.assertEqual(counters["NER_PERSON"], 1)

    def test_regex_masks_email_phone_and_pesel_before_ner(self) -> None:
        model = FakeNerModel(
            [
                ("Kowalski", "persName"),
                ("[EMAIL]", "persName"),
                ("[TELEFON]", "persName"),
                ("[PESEL]", "persName"),
            ]
        )

        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.txt"
            source_path.write_text(
                "Jan Kowalski, email safe@example.test, "
                "tel. 501 222 333, PESEL 90010112345.",
                encoding="utf-8",
            )

            with patch("ner._spacy_module", return_value=FakeSpacy(model=model)):
                output_path, counters = anonymize_file(source_path, use_ner=True)

            output_text = output_path.read_text(encoding="utf-8")
            report_text = (Path(temp_dir) / "document_RAPORT.txt").read_text(
                encoding="utf-8"
            )

        self.assertIn("[NER_PERSON]", output_text)
        self.assertIn("[EMAIL]", output_text)
        self.assertIn("[TELEFON]", output_text)
        self.assertIn("[PESEL]", output_text)
        self.assertEqual(counters["NER_PERSON"], 1)
        self.assertEqual(counters["EMAIL"], 1)
        self.assertEqual(counters["TELEFON"], 1)
        self.assertEqual(counters["PESEL"], 1)
        for source_value in ("safe@example.test", "501 222 333", "90010112345"):
            self.assertNotIn(source_value, output_text)
            self.assertNotIn(source_value, report_text)

    def test_txt_workflow_anonymizes_person_org_and_location_with_safe_report(self) -> None:
        person = "Person Example"
        org = "Example Org"
        location = "Warsaw Example"
        model = FakeNerModel(
            [
                (person, "PERSON"),
                (org, "ORG"),
                (location, "GPE"),
            ]
        )

        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.txt"
            source_path.write_text(
                f"{person} met {org} in {location}. Contact safe@example.test.",
                encoding="utf-8",
            )

            with patch("ner._spacy_module", return_value=FakeSpacy(model=model)):
                output_path, counters = anonymize_file(source_path, use_ner=True)

            report_text = (Path(temp_dir) / "document_RAPORT.txt").read_text(
                encoding="utf-8"
            )
            output_text = output_path.read_text(encoding="utf-8")

        self.assertIn("[NER_PERSON]", output_text)
        self.assertIn("[NER_ORG]", output_text)
        self.assertIn("[NER_LOCATION]", output_text)
        self.assertIn("[EMAIL]", output_text)
        self.assertEqual(counters["NER_PERSON"], 1)
        self.assertEqual(counters["NER_ORG"], 1)
        self.assertEqual(counters["NER_LOCATION"], 1)
        self.assertEqual(counters["EMAIL"], 1)
        self.assertIn("NER enabled: yes", report_text)
        self.assertIn("NER status: available", report_text)
        self.assertIn("* NER_PERSON: 1", report_text)
        for source_value in (person, org, location, "safe@example.test"):
            self.assertNotIn(source_value, report_text)

    def test_ner_skips_existing_dictionary_and_regex_placeholders(self) -> None:
        private_person = "Person Private"
        org = "Example Org"
        model = FakeNerModel(
            [
                (private_person, "PERSON"),
                ("[EMAIL]", "ORG"),
                (org, "ORG"),
            ]
        )

        with workspace_temp_dir() as temp_dir:
            dictionary_path = Path(temp_dir) / "sensitive_terms.txt"
            dictionary_path.write_text(
                f"{private_person} = [PRIVATE_PERSON]\n",
                encoding="utf-8",
            )
            source_path = Path(temp_dir) / "document.txt"
            source_path.write_text(
                f"{private_person} contacted {org} at safe@example.test.",
                encoding="utf-8",
            )

            with patch("ner._spacy_module", return_value=FakeSpacy(model=model)):
                output_path, counters = anonymize_file(
                    source_path,
                    sensitive_terms_path=dictionary_path,
                    use_ner=True,
                )

            output_text = output_path.read_text(encoding="utf-8")

        self.assertIn("[PRIVATE_PERSON]", output_text)
        self.assertIn("[NER_ORG]", output_text)
        self.assertIn("[EMAIL]", output_text)
        self.assertNotIn("[NER_PERSON]", output_text)
        self.assertEqual(counters["PRIVATE_PERSON"], 1)
        self.assertEqual(counters["NER_ORG"], 1)
        self.assertEqual(counters["EMAIL"], 1)

    def test_missing_ner_dependency_does_not_crash_or_change_output(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.txt"
            source_path.write_text(
                "Person Example contacted safe@example.test.",
                encoding="utf-8",
            )

            with patch("ner._spacy_module", return_value=None):
                output_path, _ = anonymize_file(
                    source_path,
                    use_ner=True,
                )

            output_text = output_path.read_text(encoding="utf-8")
            report_text = (Path(temp_dir) / "document_RAPORT.txt").read_text(
                encoding="utf-8"
            )

        self.assertIn("Person Example", output_text)
        self.assertIn("[EMAIL]", output_text)
        self.assertIn("NER status: dependency_missing", report_text)
        self.assertNotIn("safe@example.test", report_text)

    def test_batch_summary_contains_safe_ner_status_and_counters(self) -> None:
        person = "Person Example"
        model = FakeNerModel([(person, "PERSON")])

        with workspace_temp_dir() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            output_dir = Path(temp_dir) / "output"
            source_dir.mkdir()
            output_dir.mkdir()
            source_path = source_dir / "document.txt"
            source_path.write_text(f"{person} wrote a note.", encoding="utf-8")

            with patch("ner._spacy_module", return_value=FakeSpacy(model=model)):
                result = anonymize_batch([source_path], output_dir, use_ner=True)

            summary_text = result.summary_path.read_text(encoding="utf-8")

        self.assertEqual(result.ner_status_counts["available"], 1)
        self.assertEqual(result.ner_category_counters["NER_PERSON"], 1)
        self.assertIn("Local NER:", summary_text)
        self.assertIn("* files processed with NER: 1", summary_text)
        self.assertIn("* NER_PERSON: 1", summary_text)
        self.assertIn("NER status: available", summary_text)
        self.assertNotIn(person, summary_text)
        self.assertNotIn(str(source_dir), summary_text)

    def test_docx_workflow_can_use_ner_without_requiring_real_model(self) -> None:
        person = "Person Example"
        model = FakeNerModel([(person, "PERSON")])

        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.docx"
            document = Document()
            document.add_paragraph(f"{person} wrote a note.")
            document.save(source_path)

            with patch("ner._spacy_module", return_value=FakeSpacy(model=model)):
                output_path, counters = anonymize_docx_file(
                    source_path,
                    use_ner=True,
                )

            report_text = (Path(temp_dir) / "document_RAPORT.txt").read_text(
                encoding="utf-8"
            )

        self.assertEqual(output_path.name, "document_ANON.docx")
        self.assertEqual(counters["NER_PERSON"], 1)
        self.assertIn("* NER_PERSON: 1", report_text)
        self.assertNotIn(person, report_text)


if __name__ == "__main__":
    unittest.main()
