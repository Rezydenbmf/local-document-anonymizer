"""Answer-key schema and the policy table.

The key stores each span's ``policy_tag``; whether that tag is "must",
"optional" or "keep" is looked up in policy.json at scoring time, so a
policy change re-scores existing documents without regenerating them.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

KEY_SCHEMA = "docshield-answer-key/1"
BENCHMARK_DIR = Path(__file__).resolve().parent
POLICY_PATH = BENCHMARK_DIR / "policy.json"
EXPECT_VALUES = ("must", "optional", "keep")
GENERATOR_FILES = ("corpus.py", "layout.py", "synth.py", "generate.py")


def load_policy(path: Path = POLICY_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_expect(tag: str, policy: dict) -> str:
    """Effective treatment of a policy_tag. Unknown tags fail loudly - a
    silently ignored span would make the score lie."""
    entry = policy["tags"].get(tag)
    if entry is None:
        raise KeyError(f"policy_tag {tag!r} missing from policy.json")
    expect = entry["expect"]
    category = entry.get("only_with_category")
    if category and category not in policy.get("enabled_optional_categories", []):
        expect = "optional"
    if expect not in EXPECT_VALUES:
        raise ValueError(f"policy_tag {tag!r}: invalid expect {expect!r}")
    return expect


def generator_fingerprint() -> str:
    digest = hashlib.sha256()
    for name in GENERATOR_FILES:
        digest.update((BENCHMARK_DIR / name).read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()[:16]


def validate_key(key: dict, policy: dict) -> None:
    if key.get("schema") != KEY_SCHEMA:
        raise ValueError(f"{key.get('doc_id')}: unexpected schema {key.get('schema')!r}")
    seen = set()
    for span in key["spans"]:
        if span["id"] in seen:
            raise ValueError(f"{key['doc_id']}: duplicate span id {span['id']}")
        seen.add(span["id"])
        resolve_expect(span["policy_tag"], policy)
        if not span["chars"]:
            raise ValueError(f"{key['doc_id']} {span['id']}: no character boxes")
        if not 1 <= span["page"] <= key["pages"]:
            raise ValueError(f"{key['doc_id']} {span['id']}: page out of range")


def load_key(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
