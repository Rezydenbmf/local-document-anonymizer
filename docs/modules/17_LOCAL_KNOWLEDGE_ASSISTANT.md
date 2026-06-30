# Module: Local Knowledge Assistant MVP

## Purpose

This module documents Stage 22: a local knowledge assistant MVP over approved
anonymized TXT documents.

The goal is:

```text
approved workspace -> local knowledge index -> ask question -> answer from approved context -> show sources
```

This is a local review-support tool. It is not a guarantee, official advice,
legal advice, medical advice, a cloud service, or a production RAG system.
The user must verify answers against the cited approved source files.

## Related files

- `src/knowledge_assistant.py`
- `src/knowledge_cli.py`
- `tests/test_knowledge_assistant.py`
- `docs/modules/12_APPROVED_WORKSPACE.md`
- `docs/modules/16_LOCAL_LLM_REVIEW.md`

## Public API

```python
load_approved_documents(approved_dir) -> list[ApprovedDocument]
chunk_document(document, max_chars=1200, overlap_chars=120) -> list[KnowledgeChunk]
chunk_documents(documents, max_chars=1200, overlap_chars=120) -> list[KnowledgeChunk]
build_knowledge_index(approved_dir, index_path=None, ...) -> Path
load_knowledge_index(index_path) -> list[KnowledgeChunk]
retrieve_relevant_chunks(question, chunks, top_k=3) -> list[RetrievalResult]
answer_question(question, chunks, use_ollama=False, model_name="gemma3:4b") -> KnowledgeAnswer
check_ollama_status(model_name="gemma3:4b") -> KnowledgeOllamaStatus
warm_up_ollama_model(model_name="gemma3:4b") -> KnowledgeWarmupResult
format_answer(answer) -> str
```

## Approved Document Loading

The loader reads only files matching:

```text
*_ANON.txt
```

It ignores non-ANON files, reports, approved indexes, review files, and other
workspace files. For Stage 22 it does not parse original DOCX/PDF files again.
The input must already be an anonymized TXT output that the user manually
approved.

Metadata keeps only safe basenames such as:

```text
procedure_ANON.txt
```

It must not store full local paths.

## Chunking

Chunking is deterministic and simple. Each chunk preserves:

- `source_file`
- `chunk_id`
- `chunk_index`
- `text`

Example:

```text
source_file: procedure_ANON.txt
chunk_id: procedure_ANON.txt#2
chunk_index: 2
```

The chunk text is approved anonymized text. It may be written to the local
knowledge index, so generated index files must stay local and ignored by git.

## Local Knowledge Index

The default generated index is:

```text
_KNOWLEDGE_INDEX.json
```

The index contains chunk text from approved anonymized documents plus safe
source basenames and chunk IDs. It may contain approved anonymized text, but it
must never be committed to the public repository.

`.gitignore` covers:

```text
_KNOWLEDGE_INDEX*.json
_KNOWLEDGE_INDEX*.jsonl
```

## Retrieval

Stage 22 implements a keyword scoring fallback over chunks. It does not require
Ollama, embeddings, a vector database, a server, or network access.

The fallback returns relevant chunks with source filenames and chunk IDs. If
no relevant chunks are found, the answer path returns a controlled
`no_relevant_context` status and no sources.

Ollama embeddings with `bge-m3:latest` are not implemented in this MVP. The
working fallback is preferred over an unstable first pass.

## Local Answer Generation

Optional local answer generation uses Ollama through the local generate API if
the user requests it and has a model installed. The default model name is:

```text
gemma3:4b
```

The prompt receives only the retrieved approved/anonymized chunks, not raw
source documents, private dictionaries, original source values, full paths, or
replacement maps. The prompt instructs the model to answer only from the
provided context and to avoid outside knowledge.

If Ollama is unavailable, the model is missing, the model name is not
configured, the call times out, or generation fails, the CLI still returns the
retrieved sources with a controlled message instead of crashing.

Stage 22.1 adds local model UX helpers. `check_ollama_status()` reports whether
local Ollama is reachable, whether the selected model is installed, and, when
Ollama exposes it, whether the model is currently loaded. `warm_up_ollama_model()`
sends a tiny local prompt so a model such as `gemma3:4b` can cold-start before
the user asks a real question.

The first local generation call can be slow because Ollama may need to load the
model into memory. A timeout is safe and expected in that case: the CLI keeps
the retrieved sources visible and tells the user to warm up the model or retry
with a larger timeout.

## CLI

Build an index:

```bash
python -m src.knowledge_cli build-index approved/
```

Ask without local generation:

```bash
python -m src.knowledge_cli ask approved/_KNOWLEDGE_INDEX.json "What does the procedure require?"
```

Ask with local Ollama generation if available:

```bash
python -m src.knowledge_cli ask approved/_KNOWLEDGE_INDEX.json "What does the procedure require?" --use-ollama --model gemma3:4b
```

Check local Ollama/model status:

```bash
python -m src.knowledge_cli ollama-status --model gemma3:4b
```

Warm up a local model:

```bash
python -m src.knowledge_cli warmup --model gemma3:4b
```

Use a longer generation timeout if needed:

```bash
python -m src.knowledge_cli ask approved/_KNOWLEDGE_INDEX.json "What does the procedure require?" --use-ollama --model gemma3:4b --timeout 60
```

Output always includes sources. If no relevant context is found, output says
that no relevant approved context was found.

## Safety Assumptions

- Inputs are approved anonymized TXT files only.
- The assistant does not reprocess original DOCX/PDF files.
- Source metadata uses basenames only.
- Generated knowledge index files are local artifacts and must not be
  committed.
- Answers must show source chunk IDs.
- Local model output can be wrong, incomplete, or unavailable.
- First local model calls may time out while the model cold-starts.
- The user must verify answers against the approved source files.
- No OpenAI API, cloud API, online processing, vector database server,
  authentication, web app, installer, document editor, or automatic procedure
  generation is added.

## How to Test

Run:

```bash
python -m unittest discover -s tests
```

`tests/test_knowledge_assistant.py` uses only synthetic data. It covers
approved document loading, ignoring non-ANON files, chunk metadata, index
creation, keyword retrieval, source references, controlled no-context behavior,
controlled Ollama-unavailable behavior, mocked local generation, CLI behavior,
Ollama status/warm-up behavior, timeout fallback behavior, and git ignore
coverage for generated knowledge index files.

## Known Limitations

- TXT `_ANON` files only.
- Keyword retrieval only in the MVP.
- No embeddings yet.
- No vector database.
- No GUI.
- No chat history.
- No answer quality guarantee.
- No automatic source verification beyond chunk citations.
- The index may contain approved anonymized text and must remain local.
