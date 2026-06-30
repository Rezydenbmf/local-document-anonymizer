import contextlib
import io
import json
import subprocess
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from src.knowledge_assistant import (
    ANSWER_STATUS_COMPLETED,
    ANSWER_STATUS_GENERATION_UNAVAILABLE,
    ANSWER_STATUS_NO_CONTEXT,
    ANSWER_STATUS_TIMEOUT,
    OLLAMA_STATUS_MODEL_NOT_LOADED,
    WARMUP_STATUS_TIMEOUT,
    WARMUP_STATUS_UNAVAILABLE,
    ApprovedDocument,
    KnowledgeChunk,
    answer_question,
    build_knowledge_index,
    check_ollama_status,
    chunk_document,
    format_answer,
    load_approved_documents,
    load_knowledge_index,
    retrieve_relevant_chunks,
    warm_up_ollama_model,
)
from src.knowledge_cli import main as knowledge_cli_main


REPO_ROOT = Path(__file__).resolve().parents[1]


class KnowledgeAssistantTests(TestCase):
    def test_loads_only_approved_anon_txt_files_with_safe_basenames(self):
        with tempfile.TemporaryDirectory() as tmp:
            approved = Path(tmp)
            (approved / "procedure_ANON.txt").write_text(
                "Approved anonymized procedure text.",
                encoding="utf-8",
            )
            (approved / "draft.txt").write_text("Ignore me.", encoding="utf-8")
            (approved / "notes_RAPORT.txt").write_text("Ignore report.", encoding="utf-8")
            (approved / "_APPROVED_INDEX.txt").write_text("Ignore index.", encoding="utf-8")

            documents = load_approved_documents(approved)

        self.assertEqual(1, len(documents))
        self.assertEqual("procedure_ANON.txt", documents[0].source_file)
        self.assertNotIn(str(approved), documents[0].source_file)
        self.assertEqual("Approved anonymized procedure text.", documents[0].text)

    def test_chunk_document_preserves_safe_source_and_chunk_numbers(self):
        document = ApprovedDocument(
            source_file="procedure_ANON.txt",
            text=(
                "First approved paragraph has several safe words. "
                "Second approved paragraph has more safe words. "
                "Third approved paragraph has final safe words."
            ),
        )

        chunks = chunk_document(document, max_chars=100, overlap_chars=0)

        self.assertGreaterEqual(len(chunks), 2)
        self.assertEqual("procedure_ANON.txt", chunks[0].source_file)
        self.assertEqual("procedure_ANON.txt#1", chunks[0].chunk_id)
        self.assertEqual(1, chunks[0].chunk_index)
        self.assertEqual("procedure_ANON.txt#2", chunks[1].chunk_id)

    def test_build_and_load_knowledge_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            approved = Path(tmp)
            index_path = approved / "_KNOWLEDGE_INDEX.json"
            (approved / "policy_ANON.txt").write_text(
                "Approved retention policy uses quarterly review.",
                encoding="utf-8",
            )

            written = build_knowledge_index(approved, index_path=index_path)
            loaded = load_knowledge_index(written)
            payload = json.loads(index_path.read_text(encoding="utf-8"))

        self.assertEqual(index_path, written)
        self.assertEqual(1, payload["document_count"])
        self.assertEqual(1, payload["chunk_count"])
        self.assertEqual("policy_ANON.txt", loaded[0].source_file)
        self.assertEqual("policy_ANON.txt#1", loaded[0].chunk_id)
        self.assertNotIn(str(approved), json.dumps(payload))

    def test_retrieval_fallback_returns_sources_by_relevance(self):
        chunks = [
            KnowledgeChunk("policy_ANON.txt", "policy_ANON.txt#1", 1, "Quarterly retention review is required."),
            KnowledgeChunk("notes_ANON.txt", "notes_ANON.txt#1", 1, "Invoices are archived monthly."),
        ]

        results = retrieve_relevant_chunks("When is retention review required?", chunks, top_k=1)

        self.assertEqual(1, len(results))
        self.assertEqual("policy_ANON.txt#1", results[0].chunk.chunk_id)
        self.assertGreater(results[0].score, 0)

    def test_answer_without_ollama_returns_controlled_sources_only_message(self):
        chunks = [
            KnowledgeChunk("policy_ANON.txt", "policy_ANON.txt#1", 1, "Quarterly retention review is required."),
        ]

        answer = answer_question("retention review", chunks, use_ollama=False)
        rendered = format_answer(answer)

        self.assertEqual(ANSWER_STATUS_GENERATION_UNAVAILABLE, answer.status)
        self.assertEqual(("policy_ANON.txt#1",), answer.sources)
        self.assertIn("Sources:", rendered)
        self.assertIn("- policy_ANON.txt#1", rendered)
        self.assertIn("Verify answers against sources", rendered)

    def test_answer_with_no_context_is_controlled(self):
        chunks = [
            KnowledgeChunk("policy_ANON.txt", "policy_ANON.txt#1", 1, "Quarterly retention review is required."),
        ]

        answer = answer_question("unrelated payroll topic", chunks, use_ollama=False)

        self.assertEqual(ANSWER_STATUS_NO_CONTEXT, answer.status)
        self.assertEqual("No relevant approved context was found.", answer.answer)
        self.assertEqual((), answer.sources)

    def test_answer_with_mocked_ollama_generation(self):
        chunks = [
            KnowledgeChunk("policy_ANON.txt", "policy_ANON.txt#1", 1, "Quarterly retention review is required."),
        ]

        with patch("src.knowledge_assistant.validate_configured_model") as validate_model:
            with patch("src.knowledge_assistant._ollama_generate_answer") as generate_answer:
                validate_model.return_value = {"status": "available"}
                generate_answer.return_value = "Review is required quarterly."

                answer = answer_question(
                    "When is retention review required?",
                    chunks,
                    use_ollama=True,
                    model_name="gemma3:4b",
                )

        self.assertEqual(ANSWER_STATUS_COMPLETED, answer.status)
        self.assertEqual("Review is required quarterly.", answer.answer)
        self.assertEqual(("policy_ANON.txt#1",), answer.sources)
        self.assertEqual("gemma3:4b", answer.model_name)

    def test_answer_when_ollama_model_missing_does_not_crash(self):
        chunks = [
            KnowledgeChunk("policy_ANON.txt", "policy_ANON.txt#1", 1, "Quarterly retention review is required."),
        ]

        with patch("src.knowledge_assistant.validate_configured_model") as validate_model:
            validate_model.return_value = {"status": "model_missing"}

            answer = answer_question(
                "retention review",
                chunks,
                use_ollama=True,
                model_name="missing-model",
            )

        self.assertEqual(ANSWER_STATUS_GENERATION_UNAVAILABLE, answer.status)
        self.assertEqual(("policy_ANON.txt#1",), answer.sources)
        self.assertEqual("model_missing", answer.warning)

    def test_answer_timeout_mentions_warmup_and_preserves_sources(self):
        chunks = [
            KnowledgeChunk("policy_ANON.txt", "policy_ANON.txt#1", 1, "Quarterly retention review is required."),
        ]

        with patch("src.knowledge_assistant.validate_configured_model") as validate_model:
            with patch("src.knowledge_assistant._ollama_generate_answer") as generate_answer:
                validate_model.return_value = {"status": "available"}
                generate_answer.side_effect = TimeoutError()

                answer = answer_question(
                    "retention review",
                    chunks,
                    use_ollama=True,
                    model_name="gemma3:4b",
                    timeout_seconds=1,
                )

        self.assertEqual(ANSWER_STATUS_TIMEOUT, answer.status)
        self.assertEqual(("policy_ANON.txt#1",), answer.sources)
        self.assertIn("warmup", answer.answer)
        self.assertEqual("model_timed_out_try_warmup", answer.warning)

    def test_ollama_status_unavailable_is_controlled(self):
        with patch("src.knowledge_assistant.detect_ollama_availability") as detect:
            detect.return_value.status = "ollama_not_found"
            detect.return_value.warning = "local Ollama command not found"

            status = check_ollama_status(model_name="gemma3:4b")

        self.assertEqual("ollama_not_found", status.status)
        self.assertEqual("ollama_not_found", status.ollama_status)
        self.assertFalse(status.model_available)
        self.assertEqual("gemma3:4b", status.model_name)

    def test_ollama_status_detects_installed_but_not_loaded_model(self):
        with patch("src.knowledge_assistant.detect_ollama_availability") as detect:
            with patch("src.knowledge_assistant.list_installed_models") as list_models:
                with patch("src.knowledge_assistant._list_loaded_ollama_models") as loaded_models:
                    detect.return_value.status = "available"
                    detect.return_value.warning = ""
                    list_models.return_value = ("available", ["gemma3:4b"])
                    loaded_models.return_value = ("available", [])

                    status = check_ollama_status(model_name="gemma3:4b")

        self.assertEqual(OLLAMA_STATUS_MODEL_NOT_LOADED, status.status)
        self.assertTrue(status.model_available)
        self.assertFalse(status.model_loaded)
        self.assertIn("first answer may be slow", status.warning)

    def test_warmup_model_missing_is_controlled(self):
        with patch("src.knowledge_assistant.validate_configured_model") as validate_model:
            validate_model.return_value = {"status": "model_missing"}

            result = warm_up_ollama_model(model_name="missing-model")

        self.assertEqual(WARMUP_STATUS_UNAVAILABLE, result.status)
        self.assertEqual("model_missing", result.warning)

    def test_warmup_timeout_is_controlled(self):
        with patch("src.knowledge_assistant.validate_configured_model") as validate_model:
            with patch("src.knowledge_assistant._ollama_generate_answer") as generate_answer:
                validate_model.return_value = {"status": "available"}
                generate_answer.side_effect = TimeoutError()

                result = warm_up_ollama_model(model_name="gemma3:4b", timeout_seconds=1)

        self.assertEqual(WARMUP_STATUS_TIMEOUT, result.status)
        self.assertEqual("gemma3:4b", result.model_name)
        self.assertIn("timed out", result.warning)

    def test_cli_build_index_and_ask_without_ollama(self):
        with tempfile.TemporaryDirectory() as tmp:
            approved = Path(tmp)
            index_path = approved / "_KNOWLEDGE_INDEX.json"
            (approved / "policy_ANON.txt").write_text(
                "Approved retention policy uses quarterly review.",
                encoding="utf-8",
            )

            with contextlib.redirect_stdout(io.StringIO()):
                build_result = knowledge_cli_main(
                    ["build-index", str(approved), "--index", str(index_path)]
                )
                ask_result = knowledge_cli_main(
                    ["ask", str(index_path), "retention review", "--timeout", "2"]
                )

        self.assertEqual(0, build_result)
        self.assertEqual(0, ask_result)

    def test_cli_ollama_status_command(self):
        with patch("src.knowledge_cli.check_ollama_status") as status_check:
            status_check.return_value.status = "model_not_loaded"
            status_check.return_value.ollama_status = "available"
            status_check.return_value.model_name = "gemma3:4b"
            status_check.return_value.model_available = True
            status_check.return_value.model_loaded = False
            status_check.return_value.warning = "model is installed but not currently loaded"

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = knowledge_cli_main(["ollama-status", "--model", "gemma3:4b"])

        self.assertEqual(0, result)
        self.assertIn("Status: model_not_loaded", output.getvalue())
        self.assertIn("Model loaded: no", output.getvalue())

    def test_cli_warmup_command(self):
        with patch("src.knowledge_cli.warm_up_ollama_model") as warmup:
            warmup.return_value.status = "timeout"
            warmup.return_value.model_name = "gemma3:4b"
            warmup.return_value.warning = "model warm-up timed out"

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = knowledge_cli_main(["warmup", "--model", "gemma3:4b", "--timeout", "1"])

        self.assertEqual(0, result)
        self.assertIn("Status: timeout", output.getvalue())
        self.assertIn("model warm-up timed out", output.getvalue())

    def test_knowledge_index_files_are_gitignored(self):
        for ignored_path in ("_KNOWLEDGE_INDEX.json", "_KNOWLEDGE_INDEX.jsonl"):
            result = subprocess.run(
                ["git", "check-ignore", "-q", ignored_path],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, result.returncode)
