"""CLI for the local knowledge assistant MVP."""

from __future__ import annotations

import argparse
from pathlib import Path

try:  # pragma: no cover - package/script compatibility.
    from .knowledge_assistant import (
        DEFAULT_KNOWLEDGE_MODEL,
        build_knowledge_index,
        answer_question,
        check_ollama_status,
        format_answer,
        load_knowledge_index,
        warm_up_ollama_model,
    )
except ImportError:  # pragma: no cover
    from knowledge_assistant import (  # type: ignore
        DEFAULT_KNOWLEDGE_MODEL,
        build_knowledge_index,
        answer_question,
        check_ollama_status,
        format_answer,
        load_knowledge_index,
        warm_up_ollama_model,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Local Knowledge Assistant MVP for approved anonymized TXT documents.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser(
        "build-index",
        help="Build _KNOWLEDGE_INDEX.json from approved *_ANON.txt files.",
    )
    build_parser.add_argument("approved_dir", help="Approved workspace folder.")
    build_parser.add_argument(
        "--index",
        default="",
        help="Optional index output path. Defaults to approved/_KNOWLEDGE_INDEX.json.",
    )
    build_parser.add_argument("--chunk-size", type=int, default=1200)
    build_parser.add_argument("--chunk-overlap", type=int, default=120)

    ask_parser = subparsers.add_parser(
        "ask",
        help="Ask a question against a local knowledge index.",
    )
    ask_parser.add_argument("index", help="Path to _KNOWLEDGE_INDEX.json.")
    ask_parser.add_argument("question", help="Question to answer from approved context.")
    ask_parser.add_argument("--top-k", type=int, default=3)
    ask_parser.add_argument(
        "--use-ollama",
        action="store_true",
        help="Use local Ollama answer generation if available.",
    )
    ask_parser.add_argument(
        "--model",
        default=DEFAULT_KNOWLEDGE_MODEL,
        help="Local Ollama model name. Default: gemma3:4b.",
    )
    ask_parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help=(
            "Local Ollama generation timeout in seconds. First model load may "
            "need more time; use warmup first if it times out."
        ),
    )

    status_parser = subparsers.add_parser(
        "ollama-status",
        help="Check local Ollama and selected model status.",
    )
    status_parser.add_argument(
        "--model",
        default=DEFAULT_KNOWLEDGE_MODEL,
        help="Local Ollama model name. Default: gemma3:4b.",
    )
    status_parser.add_argument("--timeout", type=int, default=5)

    warmup_parser = subparsers.add_parser(
        "warmup",
        help="Send a tiny local prompt to warm up a selected Ollama model.",
    )
    warmup_parser.add_argument(
        "--model",
        default=DEFAULT_KNOWLEDGE_MODEL,
        help="Local Ollama model name. Default: gemma3:4b.",
    )
    warmup_parser.add_argument("--timeout", type=int, default=20)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "build-index":
        index_path = build_knowledge_index(
            Path(args.approved_dir),
            index_path=Path(args.index) if args.index else None,
            max_chars=args.chunk_size,
            overlap_chars=args.chunk_overlap,
        )
        print(f"Knowledge index written: {index_path.name}")
        print("Source policy: approved anonymized *_ANON.txt files only.")
        return 0

    if args.command == "ask":
        chunks = load_knowledge_index(Path(args.index))
        answer = answer_question(
            args.question,
            chunks,
            top_k=args.top_k,
            use_ollama=args.use_ollama,
            model_name=args.model,
            timeout_seconds=args.timeout,
        )
        print(format_answer(answer))
        return 0

    if args.command == "ollama-status":
        status = check_ollama_status(
            model_name=args.model,
            timeout_seconds=args.timeout,
        )
        print("Local Knowledge Assistant Ollama status")
        print(f"Status: {status.status}")
        print(f"Ollama: {status.ollama_status}")
        if status.model_name:
            print(f"Model: {status.model_name}")
            print(f"Model available: {'yes' if status.model_available else 'no'}")
            loaded = "unknown" if status.model_loaded is None else ("yes" if status.model_loaded else "no")
            print(f"Model loaded: {loaded}")
        if status.warning:
            print(f"Warning: {status.warning}")
        return 0

    if args.command == "warmup":
        result = warm_up_ollama_model(
            model_name=args.model,
            timeout_seconds=args.timeout,
        )
        print("Local Knowledge Assistant model warm-up")
        print(f"Status: {result.status}")
        print(f"Model: {result.model_name}")
        if result.warning:
            print(f"Warning: {result.warning}")
        return 0

    parser.error("unknown command")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
