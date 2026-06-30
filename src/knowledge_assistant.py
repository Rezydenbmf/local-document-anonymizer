"""Local knowledge assistant over approved anonymized TXT documents."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import re
import socket
from pathlib import Path
from typing import Any, Iterable
from urllib import error, request

try:  # pragma: no cover - exercised through package/script compatibility.
    from .llm_review import (
        LLM_STATUS_OLLAMA_NOT_FOUND,
        LLM_STATUS_MODEL_MISSING,
        LLM_STATUS_NO_MODEL_CONFIGURED,
        LLM_STATUS_AVAILABLE,
        LLM_STATUS_SERVICE_UNAVAILABLE,
        LLM_STATUS_TIMEOUT,
        LLM_STATUS_UNAVAILABLE,
        OLLAMA_COMMAND,
        OLLAMA_GENERATE_API_URL,
        _safe_model_name,
        detect_ollama_availability,
        list_installed_models,
        validate_configured_model,
    )
except ImportError:  # pragma: no cover
    from llm_review import (  # type: ignore
        LLM_STATUS_OLLAMA_NOT_FOUND,
        LLM_STATUS_MODEL_MISSING,
        LLM_STATUS_NO_MODEL_CONFIGURED,
        LLM_STATUS_AVAILABLE,
        LLM_STATUS_SERVICE_UNAVAILABLE,
        LLM_STATUS_TIMEOUT,
        LLM_STATUS_UNAVAILABLE,
        OLLAMA_COMMAND,
        OLLAMA_GENERATE_API_URL,
        _safe_model_name,
        detect_ollama_availability,
        list_installed_models,
        validate_configured_model,
    )


KNOWLEDGE_INDEX_FILENAME = "_KNOWLEDGE_INDEX.json"
DEFAULT_CHUNK_MAX_CHARS = 1200
DEFAULT_CHUNK_OVERLAP_CHARS = 120
DEFAULT_TOP_K = 3
DEFAULT_KNOWLEDGE_MODEL = "gemma3:4b"
MIN_QUERY_TOKEN_LENGTH = 2

ANSWER_STATUS_COMPLETED = "completed"
ANSWER_STATUS_NO_CONTEXT = "no_relevant_context"
ANSWER_STATUS_GENERATION_UNAVAILABLE = "generation_unavailable"
ANSWER_STATUS_TIMEOUT = LLM_STATUS_TIMEOUT
ANSWER_STATUS_PROCESSING_ERROR = "processing_error"
OLLAMA_STATUS_READY = "ready"
OLLAMA_STATUS_MODEL_NOT_LOADED = "model_not_loaded"
OLLAMA_STATUS_MODEL_UNKNOWN = "model_status_unknown"
WARMUP_STATUS_COMPLETED = "completed"
WARMUP_STATUS_TIMEOUT = LLM_STATUS_TIMEOUT
WARMUP_STATUS_UNAVAILABLE = "unavailable"
WARMUP_STATUS_PROCESSING_ERROR = "processing_error"


@dataclass(frozen=True)
class ApprovedDocument:
    """Approved anonymized TXT document loaded with safe metadata only."""

    source_file: str
    text: str


@dataclass(frozen=True)
class KnowledgeChunk:
    """Searchable text chunk with safe source metadata."""

    source_file: str
    chunk_id: str
    chunk_index: int
    text: str


@dataclass(frozen=True)
class RetrievalResult:
    """Keyword retrieval result."""

    chunk: KnowledgeChunk
    score: float


@dataclass(frozen=True)
class KnowledgeAnswer:
    """Controlled local assistant answer."""

    status: str
    answer: str
    sources: tuple[str, ...]
    model_name: str = ""
    warning: str = ""


@dataclass(frozen=True)
class KnowledgeOllamaStatus:
    """Safe local Ollama/model status for CLI display."""

    status: str
    ollama_status: str
    model_name: str = ""
    model_available: bool = False
    model_loaded: bool | None = None
    warning: str = ""


@dataclass(frozen=True)
class KnowledgeWarmupResult:
    """Controlled local model warm-up result."""

    status: str
    model_name: str
    warning: str = ""


def _safe_source_basename(path: Path | str) -> str:
    return Path(path).name


def load_approved_documents(approved_dir: Path | str) -> list[ApprovedDocument]:
    """Load only approved anonymized TXT files from a local approved folder."""
    folder = Path(approved_dir)
    if not folder.exists() or not folder.is_dir():
        raise FileNotFoundError("approved workspace folder not found")

    documents: list[ApprovedDocument] = []
    for path in sorted(folder.glob("*_ANON.txt"), key=lambda item: item.name.lower()):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8-sig")
        documents.append(
            ApprovedDocument(
                source_file=_safe_source_basename(path),
                text=text,
            )
        )
    return documents


def chunk_document(
    document: ApprovedDocument,
    *,
    max_chars: int = DEFAULT_CHUNK_MAX_CHARS,
    overlap_chars: int = DEFAULT_CHUNK_OVERLAP_CHARS,
) -> list[KnowledgeChunk]:
    """Split an approved anonymized document into deterministic chunks."""
    if max_chars < 100:
        raise ValueError("max_chars must be at least 100")
    if overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("overlap_chars must be non-negative and smaller than max_chars")

    text = document.text.strip()
    if not text:
        return []

    chunks: list[KnowledgeChunk] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            boundary = max(
                text.rfind("\n\n", start, end),
                text.rfind("\n", start, end),
                text.rfind(". ", start, end),
                text.rfind(" ", start, end),
            )
            if boundary > start + max_chars // 2:
                end = boundary + 1
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunk_index = len(chunks) + 1
            chunk_id = f"{document.source_file}#{chunk_index}"
            chunks.append(
                KnowledgeChunk(
                    source_file=document.source_file,
                    chunk_id=chunk_id,
                    chunk_index=chunk_index,
                    text=chunk_text,
                )
            )
        if end >= len(text):
            break
        start = max(end - overlap_chars, 0)
    return chunks


def chunk_documents(
    documents: Iterable[ApprovedDocument],
    *,
    max_chars: int = DEFAULT_CHUNK_MAX_CHARS,
    overlap_chars: int = DEFAULT_CHUNK_OVERLAP_CHARS,
) -> list[KnowledgeChunk]:
    chunks: list[KnowledgeChunk] = []
    for document in documents:
        chunks.extend(
            chunk_document(
                document,
                max_chars=max_chars,
                overlap_chars=overlap_chars,
            )
        )
    return chunks


def _chunk_to_json(chunk: KnowledgeChunk) -> dict[str, object]:
    return {
        "source_file": chunk.source_file,
        "chunk_id": chunk.chunk_id,
        "chunk_index": chunk.chunk_index,
        "text": chunk.text,
    }


def _chunk_from_json(value: object) -> KnowledgeChunk:
    if not isinstance(value, dict):
        raise ValueError("knowledge index chunk must be an object")
    source_file = str(value.get("source_file", ""))
    chunk_id = str(value.get("chunk_id", ""))
    chunk_index = value.get("chunk_index")
    text = value.get("text")
    if not source_file or not chunk_id or not isinstance(chunk_index, int) or not isinstance(text, str):
        raise ValueError("knowledge index chunk is missing required fields")
    if Path(source_file).name != source_file or Path(chunk_id.split("#", 1)[0]).name != chunk_id.split("#", 1)[0]:
        raise ValueError("knowledge index chunk contains unsafe path metadata")
    return KnowledgeChunk(
        source_file=source_file,
        chunk_id=chunk_id,
        chunk_index=chunk_index,
        text=text,
    )


def build_knowledge_index(
    approved_dir: Path | str,
    *,
    index_path: Path | str | None = None,
    max_chars: int = DEFAULT_CHUNK_MAX_CHARS,
    overlap_chars: int = DEFAULT_CHUNK_OVERLAP_CHARS,
) -> Path:
    """Build a local JSON knowledge index from approved anonymized TXT files."""
    folder = Path(approved_dir)
    documents = load_approved_documents(folder)
    chunks = chunk_documents(
        documents,
        max_chars=max_chars,
        overlap_chars=overlap_chars,
    )
    target = Path(index_path) if index_path is not None else folder / KNOWLEDGE_INDEX_FILENAME
    payload = {
        "index_version": 1,
        "source_policy": "approved anonymized *_ANON.txt files only",
        "document_count": len(documents),
        "chunk_count": len(chunks),
        "chunks": [_chunk_to_json(chunk) for chunk in chunks],
    }
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return target


def load_knowledge_index(index_path: Path | str) -> list[KnowledgeChunk]:
    """Load a local JSON knowledge index."""
    payload = json.loads(Path(index_path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("knowledge index must contain a JSON object")
    chunks = payload.get("chunks", [])
    if not isinstance(chunks, list):
        raise ValueError("knowledge index chunks must be a list")
    return [_chunk_from_json(chunk) for chunk in chunks]


def _tokenize(text: str) -> list[str]:
    return [
        token.lower()
        for token in re.findall(r"[\wąćęłńóśźżĄĆĘŁŃÓŚŹŻ]+", text, flags=re.UNICODE)
        if len(token) >= MIN_QUERY_TOKEN_LENGTH
    ]


def retrieve_relevant_chunks(
    question: str,
    chunks: Iterable[KnowledgeChunk],
    *,
    top_k: int = DEFAULT_TOP_K,
) -> list[RetrievalResult]:
    """Return keyword-scored relevant chunks without requiring Ollama."""
    query_tokens = _tokenize(question)
    if not query_tokens or top_k <= 0:
        return []
    query_counts: dict[str, int] = {}
    for token in query_tokens:
        query_counts[token] = query_counts.get(token, 0) + 1

    results: list[RetrievalResult] = []
    for chunk in chunks:
        chunk_tokens = _tokenize(chunk.text)
        if not chunk_tokens:
            continue
        chunk_counts: dict[str, int] = {}
        for token in chunk_tokens:
            chunk_counts[token] = chunk_counts.get(token, 0) + 1

        score = 0.0
        for token, query_count in query_counts.items():
            count = chunk_counts.get(token, 0)
            if count:
                score += (1 + math.log(count)) * query_count

        if score > 0:
            length_penalty = 1 + math.log(len(chunk_tokens))
            results.append(RetrievalResult(chunk=chunk, score=score / length_penalty))

    return sorted(
        results,
        key=lambda result: (-result.score, result.chunk.source_file.lower(), result.chunk.chunk_index),
    )[:top_k]


def _build_answer_prompt(question: str, results: list[RetrievalResult]) -> str:
    context_lines: list[str] = []
    for result in results:
        context_lines.append(f"[{result.chunk.chunk_id}]\n{result.chunk.text}")
    context = "\n\n".join(context_lines)
    return (
        "You are a local knowledge assistant for approved anonymized documents.\n"
        "Answer only from the provided approved context.\n"
        "If the answer is not present in the context, say that no relevant approved context was found.\n"
        "Do not use outside knowledge.\n"
        "Do not provide legal, medical, or official advice.\n"
        "Keep the answer concise and tell the user to verify it against the cited sources.\n\n"
        f"Question:\n{question.strip()}\n\n"
        f"Approved context:\n{context}"
    )


def _ollama_generate_answer(
    prompt: str,
    *,
    model_name: str,
    timeout_seconds: int,
    api_url: str = OLLAMA_GENERATE_API_URL,
) -> str:
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0},
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    http_request = request.Request(
        api_url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with request.urlopen(http_request, timeout=timeout_seconds) as response:
        response_text = response.read().decode("utf-8", errors="replace")
    parsed = json.loads(response_text)
    if not isinstance(parsed, dict) or not isinstance(parsed.get("response"), str):
        raise ValueError("local Ollama API response text missing")
    return str(parsed["response"]).strip()


def _list_loaded_ollama_models(
    *,
    timeout_seconds: int,
    api_url: str = "http://127.0.0.1:11434/api/ps",
) -> tuple[str, list[str]]:
    http_request = request.Request(api_url, method="GET")
    try:
        with request.urlopen(http_request, timeout=timeout_seconds) as response:
            response_text = response.read().decode("utf-8", errors="replace")
        parsed = json.loads(response_text)
    except (TimeoutError, socket.timeout):
        return LLM_STATUS_TIMEOUT, []
    except error.URLError as exc:
        if isinstance(exc.reason, (TimeoutError, socket.timeout)):
            return LLM_STATUS_TIMEOUT, []
        return LLM_STATUS_SERVICE_UNAVAILABLE, []
    except (ValueError, UnicodeError, json.JSONDecodeError):
        return ANSWER_STATUS_PROCESSING_ERROR, []
    except Exception:
        return LLM_STATUS_SERVICE_UNAVAILABLE, []

    if not isinstance(parsed, dict):
        return ANSWER_STATUS_PROCESSING_ERROR, []
    models = parsed.get("models", [])
    if not isinstance(models, list):
        return ANSWER_STATUS_PROCESSING_ERROR, []

    loaded: list[str] = []
    for item in models:
        if not isinstance(item, dict):
            continue
        name = _safe_model_name(item.get("name") or item.get("model"))
        if name:
            loaded.append(name)
    return LLM_STATUS_AVAILABLE, loaded


def check_ollama_status(
    *,
    model_name: str = DEFAULT_KNOWLEDGE_MODEL,
    command: str = OLLAMA_COMMAND,
    timeout_seconds: int = 5,
    ps_api_url: str = "http://127.0.0.1:11434/api/ps",
) -> KnowledgeOllamaStatus:
    """Return safe local Ollama/model status without downloading anything."""
    safe_model_name = _safe_model_name(model_name)
    availability = detect_ollama_availability(
        command=command,
        timeout_seconds=timeout_seconds,
    )
    if availability.status != LLM_STATUS_AVAILABLE:
        return KnowledgeOllamaStatus(
            status=availability.status,
            ollama_status=availability.status,
            model_name=safe_model_name,
            warning=availability.warning or "local Ollama is unavailable",
        )

    if not safe_model_name:
        return KnowledgeOllamaStatus(
            status=LLM_STATUS_NO_MODEL_CONFIGURED,
            ollama_status=LLM_STATUS_AVAILABLE,
            warning="no local model name configured",
        )

    model_list_status, installed_models = list_installed_models(
        command=command,
        timeout_seconds=timeout_seconds,
    )
    if model_list_status != LLM_STATUS_AVAILABLE:
        return KnowledgeOllamaStatus(
            status=model_list_status,
            ollama_status=LLM_STATUS_AVAILABLE,
            model_name=safe_model_name,
            warning="local Ollama model list unavailable",
        )
    if safe_model_name not in installed_models:
        return KnowledgeOllamaStatus(
            status=LLM_STATUS_MODEL_MISSING,
            ollama_status=LLM_STATUS_AVAILABLE,
            model_name=safe_model_name,
            model_available=False,
            warning="configured local Ollama model is missing",
        )

    loaded_status, loaded_models = _list_loaded_ollama_models(
        timeout_seconds=timeout_seconds,
        api_url=ps_api_url,
    )
    if loaded_status == LLM_STATUS_AVAILABLE:
        model_loaded = safe_model_name in loaded_models
        return KnowledgeOllamaStatus(
            status=OLLAMA_STATUS_READY if model_loaded else OLLAMA_STATUS_MODEL_NOT_LOADED,
            ollama_status=LLM_STATUS_AVAILABLE,
            model_name=safe_model_name,
            model_available=True,
            model_loaded=model_loaded,
            warning=(
                "model is loaded"
                if model_loaded
                else "model is installed but not currently loaded; first answer may be slow"
            ),
        )

    return KnowledgeOllamaStatus(
        status=OLLAMA_STATUS_MODEL_UNKNOWN,
        ollama_status=LLM_STATUS_AVAILABLE,
        model_name=safe_model_name,
        model_available=True,
        model_loaded=None,
        warning="model is installed; loaded-model status could not be checked",
    )


def warm_up_ollama_model(
    *,
    model_name: str = DEFAULT_KNOWLEDGE_MODEL,
    command: str = OLLAMA_COMMAND,
    timeout_seconds: int = 20,
    api_url: str = OLLAMA_GENERATE_API_URL,
) -> KnowledgeWarmupResult:
    """Send a tiny local prompt so a model can cold-start before answering."""
    safe_model_name = _safe_model_name(model_name)
    validation = validate_configured_model(
        safe_model_name,
        command=command,
        timeout_seconds=min(timeout_seconds, 5),
    )
    if validation["status"] != LLM_STATUS_AVAILABLE:
        return KnowledgeWarmupResult(
            status=WARMUP_STATUS_UNAVAILABLE,
            model_name=safe_model_name,
            warning=str(validation.get("status") or LLM_STATUS_UNAVAILABLE),
        )

    try:
        _ollama_generate_answer(
            "Reply with OK only.",
            model_name=safe_model_name,
            timeout_seconds=timeout_seconds,
            api_url=api_url,
        )
    except (TimeoutError, socket.timeout):
        return KnowledgeWarmupResult(
            status=WARMUP_STATUS_TIMEOUT,
            model_name=safe_model_name,
            warning="model warm-up timed out; try again or use a longer timeout",
        )
    except error.HTTPError:
        return KnowledgeWarmupResult(
            status=WARMUP_STATUS_UNAVAILABLE,
            model_name=safe_model_name,
            warning=LLM_STATUS_SERVICE_UNAVAILABLE,
        )
    except error.URLError as exc:
        if isinstance(exc.reason, (TimeoutError, socket.timeout)):
            return KnowledgeWarmupResult(
                status=WARMUP_STATUS_TIMEOUT,
                model_name=safe_model_name,
                warning="model warm-up timed out; try again or use a longer timeout",
            )
        return KnowledgeWarmupResult(
            status=WARMUP_STATUS_UNAVAILABLE,
            model_name=safe_model_name,
            warning=LLM_STATUS_SERVICE_UNAVAILABLE,
        )
    except Exception:
        return KnowledgeWarmupResult(
            status=WARMUP_STATUS_PROCESSING_ERROR,
            model_name=safe_model_name,
            warning="model warm-up failed safely",
        )

    return KnowledgeWarmupResult(
        status=WARMUP_STATUS_COMPLETED,
        model_name=safe_model_name,
        warning="model warm-up completed",
    )


def answer_question(
    question: str,
    chunks: Iterable[KnowledgeChunk],
    *,
    top_k: int = DEFAULT_TOP_K,
    use_ollama: bool = False,
    model_name: str = DEFAULT_KNOWLEDGE_MODEL,
    command: str = OLLAMA_COMMAND,
    timeout_seconds: int = 30,
    api_url: str = OLLAMA_GENERATE_API_URL,
) -> KnowledgeAnswer:
    """Answer from retrieved approved context with optional local Ollama."""
    results = retrieve_relevant_chunks(question, chunks, top_k=top_k)
    sources = tuple(result.chunk.chunk_id for result in results)
    if not results:
        return KnowledgeAnswer(
            status=ANSWER_STATUS_NO_CONTEXT,
            answer="No relevant approved context was found.",
            sources=(),
            model_name=_safe_model_name(model_name),
            warning="Verify approved source documents manually.",
        )

    safe_model_name = _safe_model_name(model_name)
    if not use_ollama:
        return KnowledgeAnswer(
            status=ANSWER_STATUS_GENERATION_UNAVAILABLE,
            answer=(
                "Local answer generation is unavailable or disabled. "
                "Review the retrieved approved chunks manually."
            ),
            sources=sources,
            model_name=safe_model_name,
            warning="Local generation was not used; sources are retrieval results only.",
        )

    validation = validate_configured_model(
        safe_model_name,
        command=command,
        timeout_seconds=min(timeout_seconds, 5),
    )
    if validation["status"] != LLM_STATUS_AVAILABLE:
        status = str(validation.get("status") or LLM_STATUS_UNAVAILABLE)
        return KnowledgeAnswer(
            status=ANSWER_STATUS_GENERATION_UNAVAILABLE,
            answer=(
                "Local answer generation is unavailable. "
                "Review the retrieved approved chunks manually."
            ),
            sources=sources,
            model_name=safe_model_name,
            warning=status,
        )

    try:
        generated = _ollama_generate_answer(
            _build_answer_prompt(question, results),
            model_name=safe_model_name,
            timeout_seconds=timeout_seconds,
            api_url=api_url,
        )
    except (TimeoutError, socket.timeout):
        return KnowledgeAnswer(
            status=ANSWER_STATUS_TIMEOUT,
            answer=(
                "Local answer generation timed out, possibly while the model was loading. "
                "Try `python -m src.knowledge_cli warmup --model "
                f"{safe_model_name}` or increase `--timeout`. "
                "Review the retrieved approved chunks manually."
            ),
            sources=sources,
            model_name=safe_model_name,
            warning="model_timed_out_try_warmup",
        )
    except error.HTTPError:
        return KnowledgeAnswer(
            status=ANSWER_STATUS_GENERATION_UNAVAILABLE,
            answer="Local answer generation is unavailable. Review the retrieved approved chunks manually.",
            sources=sources,
            model_name=safe_model_name,
            warning=LLM_STATUS_SERVICE_UNAVAILABLE,
        )
    except error.URLError as exc:
        warning = LLM_STATUS_TIMEOUT if isinstance(exc.reason, (TimeoutError, socket.timeout)) else LLM_STATUS_SERVICE_UNAVAILABLE
        status = ANSWER_STATUS_TIMEOUT if warning == LLM_STATUS_TIMEOUT else ANSWER_STATUS_GENERATION_UNAVAILABLE
        return KnowledgeAnswer(
            status=status,
            answer=(
                "Local answer generation is unavailable or timed out. "
                "If this is a first local model call, try warm-up first. "
                "Review the retrieved approved chunks manually."
            ),
            sources=sources,
            model_name=safe_model_name,
            warning=warning,
        )
    except (UnicodeError, ValueError, json.JSONDecodeError):
        return KnowledgeAnswer(
            status=ANSWER_STATUS_PROCESSING_ERROR,
            answer="Local answer generation failed safely. Review the retrieved approved chunks manually.",
            sources=sources,
            model_name=safe_model_name,
            warning=ANSWER_STATUS_PROCESSING_ERROR,
        )

    if not generated:
        generated = "The local model returned an empty answer. Verify the cited approved sources manually."

    return KnowledgeAnswer(
        status=ANSWER_STATUS_COMPLETED,
        answer=generated,
        sources=sources,
        model_name=safe_model_name,
        warning="Verify the answer against the cited approved sources.",
    )


def format_answer(answer: KnowledgeAnswer) -> str:
    """Format the controlled answer for CLI output."""
    lines = [
        "Local Knowledge Assistant MVP",
        "Use approved anonymized documents only. Verify answers against sources.",
        "",
        f"Status: {answer.status}",
        f"Answer: {answer.answer}",
        "",
        "Sources:",
    ]
    if answer.sources:
        lines.extend(f"- {source}" for source in answer.sources)
    else:
        lines.append("- none")
    if answer.model_name:
        lines.append(f"Model: {answer.model_name}")
    if answer.warning:
        lines.append(f"Warning: {answer.warning}")
    return "\n".join(lines)
