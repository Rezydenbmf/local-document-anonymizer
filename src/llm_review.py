"""Optional local Ollama-assisted review for already-anonymized text."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
import socket
import subprocess
from typing import Any
from urllib import error, request


LLM_STATUS_DISABLED = "disabled"
LLM_STATUS_AVAILABLE = "available"
LLM_STATUS_UNAVAILABLE = "unavailable"
LLM_STATUS_OLLAMA_NOT_FOUND = "ollama_not_found"
LLM_STATUS_SERVICE_UNAVAILABLE = "service_unavailable"
LLM_STATUS_NO_MODEL_CONFIGURED = "no_model_configured"
LLM_STATUS_MODEL_MISSING = "model_missing"
LLM_STATUS_TIMEOUT = "timeout"
LLM_STATUS_INVALID_RESPONSE = "invalid_response"
LLM_STATUS_PROCESSING_ERROR = "processing_error"
LLM_STATUS_COMPLETED = "completed"
LLM_REVIEW_STATUSES = (
    LLM_STATUS_DISABLED,
    LLM_STATUS_AVAILABLE,
    LLM_STATUS_UNAVAILABLE,
    LLM_STATUS_OLLAMA_NOT_FOUND,
    LLM_STATUS_SERVICE_UNAVAILABLE,
    LLM_STATUS_NO_MODEL_CONFIGURED,
    LLM_STATUS_MODEL_MISSING,
    LLM_STATUS_TIMEOUT,
    LLM_STATUS_INVALID_RESPONSE,
    LLM_STATUS_PROCESSING_ERROR,
    LLM_STATUS_COMPLETED,
)

LLM_RISK_OK = "ok"
LLM_RISK_WARNING = "warning"
LLM_RISK_HIGH = "high_risk"
LLM_RISK_UNKNOWN = "unknown"
LLM_RISK_LEVELS = (
    LLM_RISK_OK,
    LLM_RISK_WARNING,
    LLM_RISK_HIGH,
    LLM_RISK_UNKNOWN,
)

LLM_CATEGORY_PERSON = "PERSON_LIKE"
LLM_CATEGORY_ORGANIZATION = "ORGANIZATION_LIKE"
LLM_CATEGORY_LOCATION = "LOCATION_LIKE"
LLM_CATEGORY_ADDRESS = "ADDRESS_CONTEXT"
LLM_CATEGORY_CASE_REFERENCE = "CASE_REFERENCE_LIKE"
LLM_CATEGORY_CONTACT_DATA = "CONTACT_DATA_LIKE"
LLM_CATEGORY_OTHER = "OTHER_SENSITIVE_CONTEXT"
LLM_RESIDUAL_CATEGORIES = (
    LLM_CATEGORY_PERSON,
    LLM_CATEGORY_ORGANIZATION,
    LLM_CATEGORY_LOCATION,
    LLM_CATEGORY_ADDRESS,
    LLM_CATEGORY_CASE_REFERENCE,
    LLM_CATEGORY_CONTACT_DATA,
    LLM_CATEGORY_OTHER,
)

DEFAULT_LLM_REVIEW_TIMEOUT_SECONDS = 30
OLLAMA_COMMAND = "ollama"
OLLAMA_GENERATE_API_URL = "http://127.0.0.1:11434/api/generate"
UTF8_BOM = "\ufeff"


@dataclass(frozen=True)
class OllamaAvailability:
    """Safe local Ollama availability metadata."""

    status: str
    warning: str = ""


def _subprocess_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
    return subprocess.run(args, **kwargs)


def _safe_model_name(model_name: object) -> str:
    text = str(model_name or "").strip()
    if not text:
        return ""
    if re.fullmatch(r"[A-Za-z0-9_.:/-]+", text):
        return text
    return "local_model"


def _normalize_review_text(value: object) -> str:
    """Normalize already-anonymized text before sending it to local Ollama."""
    if not isinstance(value, str):
        raise TypeError("anonymized_text must be a string")
    return value.replace(UTF8_BOM, "")


def _json_request_schema() -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "risk_level",
            "possible_residual_categories",
            "manual_review_required",
        ],
        "properties": {
            "risk_level": {
                "type": "string",
                "enum": list(LLM_RISK_LEVELS),
            },
            "possible_residual_categories": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": list(LLM_RESIDUAL_CATEGORIES),
                },
            },
            "manual_review_required": {
                "type": "boolean",
            },
        },
    }


def build_llm_review_metadata(
    *,
    enabled: bool,
    used: bool,
    status: str,
    model_name: str = "",
    risk_level: str = LLM_RISK_UNKNOWN,
    possible_residual_categories: list[str] | tuple[str, ...] | None = None,
    manual_review_required: bool = True,
    warning: str = "",
) -> dict[str, object]:
    """Build safe LLM-review metadata for reports, summaries, and GUI status."""
    if status not in LLM_REVIEW_STATUSES:
        status = LLM_STATUS_UNAVAILABLE
    if risk_level not in LLM_RISK_LEVELS:
        risk_level = LLM_RISK_UNKNOWN

    categories: list[str] = []
    for category in possible_residual_categories or ():
        if category in LLM_RESIDUAL_CATEGORIES and category not in categories:
            categories.append(category)

    return {
        "enabled": bool(enabled),
        "used": bool(used),
        "status": status,
        "model_name": _safe_model_name(model_name),
        "risk_level": risk_level,
        "possible_residual_categories": categories,
        "manual_review_required": bool(manual_review_required),
        "warning": str(warning or ""),
    }


def detect_ollama_availability(
    *,
    command: str = OLLAMA_COMMAND,
    timeout_seconds: int = 5,
) -> OllamaAvailability:
    """Detect whether the local Ollama command/service is reachable."""
    try:
        completed = _subprocess_run(
            [command, "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
    except FileNotFoundError:
        return OllamaAvailability(
            LLM_STATUS_OLLAMA_NOT_FOUND,
            "local Ollama command not found",
        )
    except subprocess.TimeoutExpired:
        return OllamaAvailability(LLM_STATUS_TIMEOUT, "local Ollama check timed out")
    except Exception:
        return OllamaAvailability(
            LLM_STATUS_SERVICE_UNAVAILABLE,
            "local Ollama service unavailable",
        )

    if completed.returncode != 0:
        return OllamaAvailability(
            LLM_STATUS_SERVICE_UNAVAILABLE,
            "local Ollama service unavailable",
        )
    return OllamaAvailability(LLM_STATUS_AVAILABLE)


def list_installed_models(
    *,
    command: str = OLLAMA_COMMAND,
    timeout_seconds: int = 5,
) -> tuple[str, list[str]]:
    """Return a controlled status and local model names from `ollama list`."""
    try:
        completed = _subprocess_run(
            [command, "list"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
    except FileNotFoundError:
        return LLM_STATUS_OLLAMA_NOT_FOUND, []
    except subprocess.TimeoutExpired:
        return LLM_STATUS_TIMEOUT, []
    except Exception:
        return LLM_STATUS_SERVICE_UNAVAILABLE, []

    if completed.returncode != 0:
        return LLM_STATUS_SERVICE_UNAVAILABLE, []

    models: list[str] = []
    for line in str(completed.stdout or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.lower().startswith("name "):
            continue
        model_name = _safe_model_name(stripped.split()[0])
        if model_name:
            models.append(model_name)
    return LLM_STATUS_AVAILABLE, models


def validate_configured_model(
    model_name: str | None,
    *,
    command: str = OLLAMA_COMMAND,
    timeout_seconds: int = 5,
) -> dict[str, object]:
    """Validate the optional configured local model without downloading it."""
    safe_model_name = _safe_model_name(model_name)
    if not safe_model_name:
        return build_llm_review_metadata(
            enabled=True,
            used=False,
            status=LLM_STATUS_NO_MODEL_CONFIGURED,
            manual_review_required=True,
        )

    availability = detect_ollama_availability(
        command=command,
        timeout_seconds=timeout_seconds,
    )
    if availability.status != LLM_STATUS_AVAILABLE:
        return build_llm_review_metadata(
            enabled=True,
            used=False,
            status=availability.status,
            model_name=safe_model_name,
            manual_review_required=True,
            warning=availability.warning,
        )

    list_status, models = list_installed_models(
        command=command,
        timeout_seconds=timeout_seconds,
    )
    if list_status != LLM_STATUS_AVAILABLE:
        return build_llm_review_metadata(
            enabled=True,
            used=False,
            status=list_status,
            model_name=safe_model_name,
            manual_review_required=True,
            warning="local Ollama model list unavailable",
        )
    if safe_model_name not in models:
        return build_llm_review_metadata(
            enabled=True,
            used=False,
            status=LLM_STATUS_MODEL_MISSING,
            model_name=safe_model_name,
            manual_review_required=True,
            warning="configured local Ollama model is missing",
        )

    return build_llm_review_metadata(
        enabled=True,
        used=False,
        status=LLM_STATUS_AVAILABLE,
        model_name=safe_model_name,
        manual_review_required=True,
    )


def _build_review_prompt(anonymized_text: str) -> str:
    normalized_text = _normalize_review_text(anonymized_text)
    return (
        "Analyze only this already-anonymized text for possible residual "
        "sensitive context.\n"
        "Return one JSON object only.\n"
        "Do not return markdown.\n"
        "Do not return prose.\n"
        "Do not quote, copy, summarize, or repeat any input text.\n"
        "Do not include source_text, raw_text, quotes, snippets, "
        "explanations, or extra keys.\n"
        "Use exactly these keys: risk_level, possible_residual_categories, "
        "manual_review_required.\n"
        "Allowed risk_level values: ok, warning, high_risk, unknown.\n"
        "Allowed possible_residual_categories values: "
        f"{', '.join(LLM_RESIDUAL_CATEGORIES)}. "
        "manual_review_required must be a boolean.\n\n"
        "Already-anonymized text:\n"
        f"{normalized_text}"
    )


def _build_ollama_generate_payload(
    anonymized_text: str,
    *,
    model_name: str,
) -> dict[str, object]:
    return {
        "model": model_name,
        "prompt": _build_review_prompt(anonymized_text),
        "stream": False,
        "format": _json_request_schema(),
        "options": {
            "temperature": 0,
        },
    }


def _ollama_api_generate(
    payload: dict[str, object],
    *,
    timeout_seconds: int,
    api_url: str = OLLAMA_GENERATE_API_URL,
) -> str:
    request_body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    http_request = request.Request(
        api_url,
        data=request_body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with request.urlopen(http_request, timeout=timeout_seconds) as response:
        response_text = response.read().decode("utf-8", errors="replace")

    try:
        parsed = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise ValueError("local Ollama API returned invalid JSON") from exc

    if not isinstance(parsed, dict):
        raise ValueError("local Ollama API returned a non-object payload")

    model_response = parsed.get("response")
    if not isinstance(model_response, str):
        raise ValueError("local Ollama API response text missing")

    return model_response


def _normalize_llm_response_json_text(response_text: str) -> str:
    """Allow local models to wrap the full JSON object in markdown fences."""
    text = str(response_text or "").strip()
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def parse_llm_review_response(response_text: str, model_name: str = "") -> dict[str, object]:
    """Parse strict safe JSON returned by the local model."""
    try:
        parsed = json.loads(_normalize_llm_response_json_text(response_text))
    except json.JSONDecodeError:
        return build_llm_review_metadata(
            enabled=True,
            used=True,
            status=LLM_STATUS_INVALID_RESPONSE,
            model_name=model_name,
            manual_review_required=True,
        )

    if not isinstance(parsed, dict):
        return build_llm_review_metadata(
            enabled=True,
            used=True,
            status=LLM_STATUS_INVALID_RESPONSE,
            model_name=model_name,
            manual_review_required=True,
        )

    allowed_keys = {
        "risk_level",
        "llm_risk_level",
        "possible_residual_categories",
        "manual_review_required",
    }
    if any(key not in allowed_keys for key in parsed):
        return build_llm_review_metadata(
            enabled=True,
            used=True,
            status=LLM_STATUS_INVALID_RESPONSE,
            model_name=model_name,
            manual_review_required=True,
        )

    risk_level = parsed.get("llm_risk_level", parsed.get("risk_level", LLM_RISK_UNKNOWN))
    if risk_level not in LLM_RISK_LEVELS:
        return build_llm_review_metadata(
            enabled=True,
            used=True,
            status=LLM_STATUS_INVALID_RESPONSE,
            model_name=model_name,
            manual_review_required=True,
        )

    raw_categories = parsed.get("possible_residual_categories", [])
    if raw_categories is None:
        raw_categories = []
    if not isinstance(raw_categories, list):
        return build_llm_review_metadata(
            enabled=True,
            used=True,
            status=LLM_STATUS_INVALID_RESPONSE,
            model_name=model_name,
            manual_review_required=True,
        )
    categories: list[str] = []
    for category in raw_categories:
        if category not in LLM_RESIDUAL_CATEGORIES:
            return build_llm_review_metadata(
                enabled=True,
                used=True,
                status=LLM_STATUS_INVALID_RESPONSE,
                model_name=model_name,
                manual_review_required=True,
            )
        if category not in categories:
            categories.append(category)

    manual_review_required = parsed.get("manual_review_required", True)
    if not isinstance(manual_review_required, bool):
        return build_llm_review_metadata(
            enabled=True,
            used=True,
            status=LLM_STATUS_INVALID_RESPONSE,
            model_name=model_name,
            manual_review_required=True,
        )

    return build_llm_review_metadata(
        enabled=True,
        used=True,
        status=LLM_STATUS_COMPLETED,
        model_name=model_name,
        risk_level=str(risk_level),
        possible_residual_categories=categories,
        manual_review_required=manual_review_required,
    )


def run_llm_review(
    anonymized_text: str,
    *,
    enabled: bool = False,
    model_name: str | None = None,
    command: str = OLLAMA_COMMAND,
    timeout_seconds: int = DEFAULT_LLM_REVIEW_TIMEOUT_SECONDS,
    api_url: str = OLLAMA_GENERATE_API_URL,
) -> dict[str, object]:
    """Run optional local LLM review on already-anonymized text only."""
    safe_model_name = _safe_model_name(model_name)
    if not enabled:
        return build_llm_review_metadata(
            enabled=False,
            used=False,
            status=LLM_STATUS_DISABLED,
            model_name=safe_model_name,
            manual_review_required=True,
        )
    validation = validate_configured_model(
        safe_model_name,
        command=command,
        timeout_seconds=timeout_seconds,
    )
    if validation["status"] != LLM_STATUS_AVAILABLE:
        return validation

    payload = _build_ollama_generate_payload(
        anonymized_text,
        model_name=safe_model_name,
    )
    try:
        response_text = _ollama_api_generate(
            payload,
            timeout_seconds=timeout_seconds,
            api_url=api_url,
        )
    except (TimeoutError, socket.timeout):
        return build_llm_review_metadata(
            enabled=True,
            used=False,
            status=LLM_STATUS_TIMEOUT,
            model_name=safe_model_name,
            manual_review_required=True,
            warning="local LLM review timed out",
        )
    except error.HTTPError:
        return build_llm_review_metadata(
            enabled=True,
            used=False,
            status=LLM_STATUS_SERVICE_UNAVAILABLE,
            model_name=safe_model_name,
            manual_review_required=True,
            warning="local Ollama service unavailable",
        )
    except error.URLError as exc:
        if isinstance(exc.reason, (TimeoutError, socket.timeout)):
            return build_llm_review_metadata(
                enabled=True,
                used=False,
                status=LLM_STATUS_TIMEOUT,
                model_name=safe_model_name,
                manual_review_required=True,
                warning="local LLM review timed out",
            )
        return build_llm_review_metadata(
            enabled=True,
            used=False,
            status=LLM_STATUS_SERVICE_UNAVAILABLE,
            model_name=safe_model_name,
            manual_review_required=True,
            warning="local Ollama service unavailable",
        )
    except UnicodeError:
        return build_llm_review_metadata(
            enabled=True,
            used=False,
            status=LLM_STATUS_PROCESSING_ERROR,
            model_name=safe_model_name,
            manual_review_required=True,
            warning="local LLM review failed safely",
        )
    except ValueError:
        return build_llm_review_metadata(
            enabled=True,
            used=True,
            status=LLM_STATUS_INVALID_RESPONSE,
            model_name=safe_model_name,
            manual_review_required=True,
        )
    except Exception:
        return build_llm_review_metadata(
            enabled=True,
            used=False,
            status=LLM_STATUS_PROCESSING_ERROR,
            model_name=safe_model_name,
            manual_review_required=True,
            warning="local LLM review failed safely",
        )

    return parse_llm_review_response(response_text, safe_model_name)
