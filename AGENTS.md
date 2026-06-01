# AGENTS.md

Instructions for Codex and future AI assistants working in this repository.

## Work Style

- Work in small, controlled implementation stages.
- Prefer a finished narrow MVP over an unfinished advanced system.
- Keep code simple, readable, and maintainable.
- Do not invent architecture beyond the requested scope.
- Before creating a new repository, project skeleton, or large file set, ask the user to confirm the exact target directory unless it is already explicitly provided.

## Required Reading Before Work

Before making changes, read:

- `AGENTS.md`
- `README.md`
- `docs/PROJECT_STATE.md`
- The relevant file in `docs/modules/`
- Code files related to the current task

Do not guess the current project state from chat history. The repository is the source of truth.

## Scope Control

- Do not change unrelated files.
- Do not refactor unrelated code unless explicitly requested.
- Do not add features outside the current task.
- Do not add network calls, APIs, AI dependencies, OCR, local LLMs, databases, or large frameworks without an explicit project decision.

## Safety Rules

Never commit:

- Real documents.
- Personal data.
- Logs.
- Local configuration files.
- Generated output files.
- Files from `private/`, `real_data/`, `output/`, `outputs/`, `exports/`, or `data/`.

Use only synthetic test data in this repository.

Reports must never contain original sensitive source values. The application must not store a replacement map containing original sensitive values.

## Documentation Rules

- Update documentation when a module or project stage changes.
- Update `docs/PROJECT_STATE.md` after meaningful changes.
- Update `docs/MODULE_INDEX.md` when modules are added or changed.
- Update the relevant `docs/modules/*.md` file.
- Update `docs/LESSONS_LEARNED.md` only when there is a reusable lesson.

## Git Rules

- Do not commit or push unless the user explicitly asks.
- Before suggesting a commit, check `git status`.
- Mention any risky or private files if they are present.

## Required Report Format

After every task, report:

1. changed files
2. diff summary
3. test results
4. implementation summary
5. known risks / limitations
6. git status

Present the result for user review before any commit.
