"""Tests for optional local Ollama LLM review."""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from anonymizer import anonymize_batch, anonymize_file
from llm_review import (
    LLM_CATEGORY_CONTACT_DATA,
    LLM_CATEGORY_PERSON,
    LLM_RISK_HIGH,
    LLM_RISK_WARNING,
    LLM_STATUS_AVAILABLE,
    LLM_STATUS_COMPLETED,
    LLM_STATUS_DISABLED,
    LLM_STATUS_INVALID_RESPONSE,
    LLM_STATUS_MODEL_MISSING,
    LLM_STATUS_NO_MODEL_CONFIGURED,
    LLM_STATUS_OLLAMA_NOT_FOUND,
    LLM_STATUS_PROCESSING_ERROR,
    LLM_STATUS_SERVICE_UNAVAILABLE,
    LLM_STATUS_TIMEOUT,
    _build_ollama_generate_payload,
    _build_review_prompt,
    build_llm_review_metadata,
    detect_ollama_availability,
    list_installed_models,
    parse_llm_review_response,
    run_llm_review,
    validate_configured_model,
)
from report import build_batch_summary_text, build_report_text


def workspace_temp_dir():
    return tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "tests")


def completed(stdout: str = "", returncode: int = 0):
    import subprocess

    return subprocess.CompletedProcess(
        args=["ollama"],
        returncode=returncode,
        stdout=stdout,
        stderr="",
    )


class LlmReviewTests(unittest.TestCase):
    def test_ollama_availability_detection_reports_available(self) -> None:
        with patch("llm_review._subprocess_run", return_value=completed("ollama version")):
            availability = detect_ollama_availability()

        self.assertEqual(availability.status, LLM_STATUS_AVAILABLE)

    def test_ollama_availability_detection_handles_missing_command(self) -> None:
        with patch("llm_review._subprocess_run", side_effect=FileNotFoundError()):
            availability = detect_ollama_availability()

        self.assertEqual(availability.status, LLM_STATUS_OLLAMA_NOT_FOUND)

    def test_ollama_availability_detection_handles_service_unavailable(self) -> None:
        with patch("llm_review._subprocess_run", return_value=completed(returncode=1)):
            availability = detect_ollama_availability()

        self.assertEqual(availability.status, LLM_STATUS_SERVICE_UNAVAILABLE)

    def test_no_model_configured_is_controlled(self) -> None:
        result = validate_configured_model("")

        self.assertEqual(result["status"], LLM_STATUS_NO_MODEL_CONFIGURED)
        self.assertEqual(result["used"], False)

    def test_configured_model_missing_is_controlled(self) -> None:
        side_effects = [
            completed("ollama version"),
            completed("NAME ID SIZE MODIFIED\nother-model:latest abc 1GB now\n"),
        ]
        with patch("llm_review._subprocess_run", side_effect=side_effects):
            result = validate_configured_model("local-model:latest")

        self.assertEqual(result["status"], LLM_STATUS_MODEL_MISSING)
        self.assertEqual(result["model_name"], "local-model:latest")

    def test_installed_model_listing_parses_safe_names(self) -> None:
        output = (
            "NAME ID SIZE MODIFIED\n"
            "gemma3:4b abc 3GB now\n"
            "bielik:latest def 1GB now\n"
            "llama3.1 xyz 2GB now\n"
        )
        with patch("llm_review._subprocess_run", return_value=completed(output)):
            status, models = list_installed_models()

        self.assertEqual(status, LLM_STATUS_AVAILABLE)
        self.assertEqual(models, ["gemma3:4b", "bielik:latest", "llama3.1"])

    def test_successful_mocked_llm_review_parses_structured_output(self) -> None:
        side_effects = [
            completed("ollama version"),
            completed("NAME ID SIZE MODIFIED\nlocal-model abc 1GB now\n"),
        ]

        with patch("llm_review._subprocess_run", side_effect=side_effects), patch(
            "llm_review._ollama_api_generate",
            return_value=(
                '{"risk_level":"warning",'
                '"possible_residual_categories":["PERSON_LIKE"],'
                '"manual_review_required":true}'
            ),
        ):
            result = run_llm_review(
                "Already anonymized [EMAIL] text.",
                enabled=True,
                model_name="local-model",
            )

        self.assertEqual(result["status"], LLM_STATUS_COMPLETED)
        self.assertEqual(result["used"], True)
        self.assertEqual(result["risk_level"], LLM_RISK_WARNING)
        self.assertEqual(result["possible_residual_categories"], [LLM_CATEGORY_PERSON])

    def test_review_prompt_strips_bom_from_anonymized_text(self) -> None:
        prompt = _build_review_prompt("\ufeffZażółć [EMAIL].")

        self.assertIn("Zażółć [EMAIL].", prompt)
        self.assertNotIn("\ufeff", prompt)
        self.assertIn("Return one JSON object only.", prompt)
        self.assertIn("Do not return markdown.", prompt)
        self.assertIn("manual_review_required must be a boolean.", prompt)

    def test_ollama_generate_payload_uses_strict_json_schema(self) -> None:
        payload = _build_ollama_generate_payload(
            "\ufeffZażółć gęślą jaźń [EMAIL].",
            model_name="gemma3:4b",
        )

        self.assertEqual(payload["model"], "gemma3:4b")
        self.assertEqual(payload["stream"], False)
        self.assertEqual(payload["options"], {"temperature": 0})
        self.assertNotIn("\ufeff", str(payload["prompt"]))
        self.assertIn("Zażółć gęślą jaźń [EMAIL].", str(payload["prompt"]))
        self.assertIsInstance(payload["format"], dict)
        self.assertEqual(payload["format"]["type"], "object")
        self.assertEqual(payload["format"]["additionalProperties"], False)
        self.assertEqual(
            payload["format"]["required"],
            ["risk_level", "possible_residual_categories", "manual_review_required"],
        )
        self.assertEqual(
            payload["format"]["properties"]["risk_level"]["enum"],
            ["ok", "warning", "high_risk", "unknown"],
        )

    def test_timeout_handling_is_controlled(self) -> None:
        side_effects = [
            completed("ollama version"),
            completed("NAME ID SIZE MODIFIED\nlocal-model abc 1GB now\n"),
        ]
        with patch("llm_review._subprocess_run", side_effect=side_effects), patch(
            "llm_review._ollama_api_generate",
            side_effect=TimeoutError(),
        ):
            result = run_llm_review(
                "Already anonymized text.",
                enabled=True,
                model_name="local-model",
            )

        self.assertEqual(result["status"], LLM_STATUS_TIMEOUT)

    def test_encoding_failure_becomes_controlled_status_without_leakage(self) -> None:
        side_effects = [
            completed("ollama version"),
            completed("NAME ID SIZE MODIFIED\nlocal-model abc 1GB now\n"),
        ]

        with patch("llm_review._subprocess_run", side_effect=side_effects), patch(
            "llm_review._ollama_api_generate",
            side_effect=UnicodeEncodeError("charmap", "\ufeffZażółć", 0, 1, "cannot encode"),
        ):
            result = run_llm_review(
                "\ufeffZażółć gęślą jaźń [EMAIL].",
                enabled=True,
                model_name="local-model",
            )

        self.assertEqual(result["status"], LLM_STATUS_PROCESSING_ERROR)
        self.assertEqual(result["used"], False)
        self.assertEqual(result["warning"], "local LLM review failed safely")
        serialized = repr(result)
        self.assertNotIn("Zażółć", serialized)
        self.assertNotIn("\ufeff", serialized)
        self.assertNotIn("cannot encode", serialized)

    def test_invalid_response_handling_is_controlled(self) -> None:
        result = parse_llm_review_response("not json", "local-model")

        self.assertEqual(result["status"], LLM_STATUS_INVALID_RESPONSE)
        self.assertEqual(result["used"], True)

    def test_structured_response_accepts_json_markdown_fence(self) -> None:
        result = parse_llm_review_response(
            "```json\n"
            '{"risk_level":"high_risk",'
            '"possible_residual_categories":["PERSON_LIKE","CONTACT_DATA_LIKE"],'
            '"manual_review_required":true}'
            "\n```",
            "gemma3:4b",
        )

        self.assertEqual(result["status"], LLM_STATUS_COMPLETED)
        self.assertEqual(result["risk_level"], LLM_RISK_HIGH)
        self.assertEqual(
            result["possible_residual_categories"],
            [LLM_CATEGORY_PERSON, LLM_CATEGORY_CONTACT_DATA],
        )
        self.assertEqual(result["model_name"], "gemma3:4b")

    def test_structured_response_accepts_plain_markdown_fence(self) -> None:
        result = parse_llm_review_response(
            "```\n"
            '{"risk_level":"warning",'
            '"possible_residual_categories":["PERSON_LIKE"],'
            '"manual_review_required":true}'
            "\n```",
            "gemma3:4b",
        )

        self.assertEqual(result["status"], LLM_STATUS_COMPLETED)
        self.assertEqual(result["risk_level"], LLM_RISK_WARNING)
        self.assertEqual(result["possible_residual_categories"], [LLM_CATEGORY_PERSON])

    def test_structured_response_rejects_fence_with_extra_prose(self) -> None:
        result = parse_llm_review_response(
            "Here is the JSON:\n"
            "```json\n"
            '{"risk_level":"warning",'
            '"possible_residual_categories":["PERSON_LIKE"],'
            '"manual_review_required":true}'
            "\n```",
            "gemma3:4b",
        )

        self.assertEqual(result["status"], LLM_STATUS_INVALID_RESPONSE)

    def test_structured_response_rejects_unknown_categories(self) -> None:
        result = parse_llm_review_response(
            '{"risk_level":"warning",'
            '"possible_residual_categories":["RAW_VALUE"],'
            '"manual_review_required":true}',
            "local-model",
        )

        self.assertEqual(result["status"], LLM_STATUS_INVALID_RESPONSE)

    def test_structured_response_rejects_extra_content_fields(self) -> None:
        result = parse_llm_review_response(
            '{"risk_level":"warning",'
            '"possible_residual_categories":[],'
            '"manual_review_required":true,'
            '"snippet":"Synthetic copied text"}',
            "local-model",
        )

        self.assertEqual(result["status"], LLM_STATUS_INVALID_RESPONSE)

    def test_llm_risk_level_mapping_accepts_high_risk(self) -> None:
        result = parse_llm_review_response(
            '{"llm_risk_level":"high_risk",'
            '"possible_residual_categories":["CONTACT_DATA_LIKE"],'
            '"manual_review_required":true}',
            "local-model",
        )

        self.assertEqual(result["status"], LLM_STATUS_COMPLETED)
        self.assertEqual(result["risk_level"], LLM_RISK_HIGH)
        self.assertEqual(
            result["possible_residual_categories"],
            [LLM_CATEGORY_CONTACT_DATA],
        )

    def test_report_includes_safe_llm_metadata_only(self) -> None:
        raw_prompt = "Analyze only this already-anonymized text"
        raw_response = '{"risk_level":"warning"}'
        source_text = "Synthetic Person Example"
        report_text = build_report_text(
            counters={"EMAIL": 1},
            input_extension=".txt",
            output_extension=".txt",
            llm_review_result=build_llm_review_metadata(
                enabled=True,
                used=True,
                status=LLM_STATUS_COMPLETED,
                model_name="bielik:latest",
                risk_level=LLM_RISK_WARNING,
                possible_residual_categories=[LLM_CATEGORY_PERSON],
                manual_review_required=True,
            ),
        )

        self.assertIn("Local LLM review:", report_text)
        self.assertIn("LLM review used: yes", report_text)
        self.assertIn("LLM model: bielik:latest", report_text)
        self.assertIn("* PERSON_LIKE", report_text)
        self.assertNotIn(raw_prompt, report_text)
        self.assertNotIn(raw_response, report_text)
        self.assertNotIn(source_text, report_text)

    def test_fenced_response_does_not_leak_raw_response_to_report(self) -> None:
        raw_response = (
            "```json\n"
            '{"risk_level":"warning",'
            '"possible_residual_categories":["PERSON_LIKE"],'
            '"manual_review_required":true}'
            "\n```"
        )
        result = parse_llm_review_response(raw_response, "gemma3:4b")

        report_text = build_report_text(
            counters={},
            input_extension=".txt",
            output_extension=".txt",
            llm_review_result=result,
        )

        self.assertIn("LLM review status: completed", report_text)
        self.assertIn("* PERSON_LIKE", report_text)
        self.assertNotIn("```", report_text)
        self.assertNotIn("risk_level", report_text)
        self.assertNotIn("possible_residual_categories", report_text)
        self.assertNotIn(raw_response, report_text)

    def test_batch_summary_includes_safe_llm_status_and_counters(self) -> None:
        summary_text = build_batch_summary_text(
            input_count=1,
            success_count=1,
            error_count=0,
            counters={},
            audit_status_counts={"ok": 1, "warning": 0, "not run": 0},
            results=[
                {
                    "input_name": "document.txt",
                    "status": "success",
                    "output_name": "document_ANON.txt",
                    "report_name": "document_RAPORT.txt",
                    "audit_status": "ok",
                    "risk_level": "ok",
                    "llm_review_used": True,
                    "llm_review_status": LLM_STATUS_COMPLETED,
                    "llm_risk_level": LLM_RISK_WARNING,
                }
            ],
            llm_review_status_counts={LLM_STATUS_COMPLETED: 1},
            llm_review_risk_level_counts={LLM_RISK_WARNING: 1},
            llm_review_category_counters={LLM_CATEGORY_PERSON: 1},
        )

        self.assertIn("Local LLM review:", summary_text)
        self.assertIn("* LLM review attempts: 1", summary_text)
        self.assertIn("* LLM attempted but failed safely: 0", summary_text)
        self.assertIn("* completed: 1", summary_text)
        self.assertIn("* warning: 1", summary_text)
        self.assertIn("* PERSON_LIKE: 1", summary_text)
        self.assertIn("LLM prompts stored: no", summary_text)
        self.assertIn("Raw LLM responses stored: no", summary_text)

    def test_batch_summary_counts_invalid_response_as_attempted_failed_not_skipped(self) -> None:
        summary_text = build_batch_summary_text(
            input_count=1,
            success_count=1,
            error_count=0,
            counters={},
            audit_status_counts={"ok": 1, "warning": 0, "not run": 0},
            results=[
                {
                    "input_name": "document.txt",
                    "status": "success",
                    "output_name": "document_ANON.txt",
                    "report_name": "document_RAPORT.txt",
                    "audit_status": "ok",
                    "risk_level": "ok",
                    "llm_review_used": True,
                    "llm_review_status": LLM_STATUS_INVALID_RESPONSE,
                    "llm_risk_level": "unknown",
                }
            ],
            llm_review_status_counts={LLM_STATUS_INVALID_RESPONSE: 1},
            llm_review_risk_level_counts={"unknown": 1},
            llm_review_category_counters={},
        )

        self.assertIn("* LLM review attempts: 1", summary_text)
        self.assertIn("* LLM attempted but failed safely: 1", summary_text)
        self.assertIn("* LLM unavailable, disabled, or skipped: 0", summary_text)
        self.assertIn("* invalid_response: 1", summary_text)

    def test_batch_summary_counts_timeout_as_attempted_failed_not_skipped(self) -> None:
        summary_text = build_batch_summary_text(
            input_count=1,
            success_count=1,
            error_count=0,
            counters={},
            audit_status_counts={"ok": 1, "warning": 0, "not run": 0},
            results=[
                {
                    "input_name": "document.txt",
                    "status": "success",
                    "output_name": "document_ANON.txt",
                    "report_name": "document_RAPORT.txt",
                    "audit_status": "ok",
                    "risk_level": "ok",
                    "llm_review_used": False,
                    "llm_review_status": LLM_STATUS_TIMEOUT,
                    "llm_risk_level": "unknown",
                }
            ],
            llm_review_status_counts={LLM_STATUS_TIMEOUT: 1},
            llm_review_risk_level_counts={"unknown": 1},
            llm_review_category_counters={},
        )

        self.assertIn("* LLM review attempts: 1", summary_text)
        self.assertIn("* LLM attempted but failed safely: 1", summary_text)
        self.assertIn("* LLM unavailable, disabled, or skipped: 0", summary_text)
        self.assertIn("* timeout: 1", summary_text)

    def test_batch_summary_counts_skipped_statuses_as_unavailable(self) -> None:
        summary_text = build_batch_summary_text(
            input_count=3,
            success_count=3,
            error_count=0,
            counters={},
            audit_status_counts={"ok": 3, "warning": 0, "not run": 0},
            results=[
                {
                    "input_name": "a.txt",
                    "status": "success",
                    "output_name": "a_ANON.txt",
                    "report_name": "a_RAPORT.txt",
                    "audit_status": "ok",
                    "risk_level": "ok",
                    "llm_review_status": LLM_STATUS_DISABLED,
                },
                {
                    "input_name": "b.txt",
                    "status": "success",
                    "output_name": "b_ANON.txt",
                    "report_name": "b_RAPORT.txt",
                    "audit_status": "ok",
                    "risk_level": "ok",
                    "llm_review_status": LLM_STATUS_NO_MODEL_CONFIGURED,
                },
                {
                    "input_name": "c.txt",
                    "status": "success",
                    "output_name": "c_ANON.txt",
                    "report_name": "c_RAPORT.txt",
                    "audit_status": "ok",
                    "risk_level": "ok",
                    "llm_review_status": LLM_STATUS_MODEL_MISSING,
                },
            ],
            llm_review_status_counts={
                LLM_STATUS_DISABLED: 1,
                LLM_STATUS_NO_MODEL_CONFIGURED: 1,
                LLM_STATUS_MODEL_MISSING: 1,
            },
            llm_review_risk_level_counts={"unknown": 3},
            llm_review_category_counters={},
        )

        self.assertIn("* LLM review attempts: 0", summary_text)
        self.assertIn("* LLM attempted but failed safely: 0", summary_text)
        self.assertIn("* LLM unavailable, disabled, or skipped: 3", summary_text)

    def test_no_crash_when_llm_review_is_unavailable(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.txt"
            source_path.write_text("Contact safe@example.test.", encoding="utf-8")

            with patch(
                "anonymizer.run_llm_review",
                return_value=build_llm_review_metadata(
                    enabled=True,
                    used=False,
                    status=LLM_STATUS_OLLAMA_NOT_FOUND,
                    model_name="local-model",
                ),
            ):
                output_path, counters = anonymize_file(
                    source_path,
                    use_llm_review=True,
                    llm_model_name="local-model",
                )

            output_exists = output_path.exists()
            report_text = (Path(temp_dir) / "document_RAPORT.txt").read_text(
                encoding="utf-8"
            )

        self.assertEqual(counters, {"EMAIL": 1})
        self.assertTrue(output_exists)
        self.assertIn("LLM review status: ollama_not_found", report_text)

    def test_llm_review_receives_anonymized_output_only(self) -> None:
        raw_source = "safe@example.test"
        captured_texts: list[str] = []

        def fake_review(text: str, **_kwargs):
            captured_texts.append(text)
            return build_llm_review_metadata(
                enabled=True,
                used=True,
                status=LLM_STATUS_COMPLETED,
                model_name="local-model",
            )

        with workspace_temp_dir() as temp_dir:
            source_path = Path(temp_dir) / "document.txt"
            source_path.write_text(f"Contact {raw_source}.", encoding="utf-8")

            with patch("anonymizer.run_llm_review", side_effect=fake_review):
                output_path, _ = anonymize_file(
                    source_path,
                    use_llm_review=True,
                    llm_model_name="local-model",
                )
            output_text = output_path.read_text(encoding="utf-8")

        self.assertEqual(captured_texts, ["Contact [EMAIL]."])
        self.assertNotIn(raw_source, captured_texts[0])
        self.assertEqual(output_text, "Contact [EMAIL].")

    def test_batch_result_aggregates_residual_categories(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            output_dir = Path(temp_dir) / "output"
            source_dir.mkdir()
            output_dir.mkdir()
            source_path = source_dir / "document.txt"
            source_path.write_text("Contact safe@example.test.", encoding="utf-8")

            with patch(
                "anonymizer.run_llm_review",
                return_value=build_llm_review_metadata(
                    enabled=True,
                    used=True,
                    status=LLM_STATUS_COMPLETED,
                    model_name="local-model",
                    risk_level=LLM_RISK_WARNING,
                    possible_residual_categories=[LLM_CATEGORY_PERSON],
                ),
            ):
                result = anonymize_batch(
                    [source_path],
                    output_dir,
                    use_llm_review=True,
                    llm_model_name="local-model",
                )

            summary_text = result.summary_path.read_text(encoding="utf-8")

        self.assertEqual(result.llm_review_status_counts[LLM_STATUS_COMPLETED], 1)
        self.assertEqual(result.llm_review_risk_level_counts[LLM_RISK_WARNING], 1)
        self.assertEqual(result.llm_review_category_counters[LLM_CATEGORY_PERSON], 1)
        self.assertIn("* PERSON_LIKE: 1", summary_text)
        self.assertNotIn("safe@example.test", summary_text)

    def test_processing_error_report_and_summary_stay_safe(self) -> None:
        with workspace_temp_dir() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            output_dir = Path(temp_dir) / "output"
            source_dir.mkdir()
            output_dir.mkdir()
            source_path = source_dir / "document.txt"
            source_path.write_text(
                "\ufeffZażółć gęślą jaźń safe@example.test.",
                encoding="utf-8",
            )

            safe_result = build_llm_review_metadata(
                enabled=True,
                used=False,
                status=LLM_STATUS_PROCESSING_ERROR,
                model_name="local-model",
                warning="local LLM review failed safely",
            )
            with patch("anonymizer.run_llm_review", return_value=safe_result):
                output_path, _ = anonymize_file(
                    source_path,
                    output_dir=output_dir,
                    use_llm_review=True,
                    llm_model_name="local-model",
                )
                batch_result = anonymize_batch(
                    [source_path],
                    output_dir,
                    use_llm_review=True,
                    llm_model_name="local-model",
                )

            report_text = (output_dir / "document_RAPORT.txt").read_text(encoding="utf-8")
            summary_text = batch_result.summary_path.read_text(encoding="utf-8")
            output_text = output_path.read_text(encoding="utf-8")

        self.assertIn("LLM review status: processing_error", report_text)
        self.assertIn("LLM warning: local LLM review failed safely", report_text)
        self.assertIn("* processing_error: 1", summary_text)
        self.assertIn("* LLM review attempts: 1", summary_text)
        self.assertIn("* LLM attempted but failed safely: 1", summary_text)
        self.assertIn("* LLM unavailable, disabled, or skipped: 0", summary_text)
        self.assertNotIn("Zażółć", report_text)
        self.assertNotIn("Zażółć", summary_text)
        self.assertNotIn("safe@example.test", report_text)
        self.assertNotIn("safe@example.test", summary_text)
        self.assertNotIn("Already-anonymized text:", report_text)
        self.assertNotIn("Already-anonymized text:", summary_text)
        self.assertIn("[EMAIL]", output_text)


if __name__ == "__main__":
    unittest.main()
