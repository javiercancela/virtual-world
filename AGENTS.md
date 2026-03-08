# Agent guide

High-level guide for AI agents working on this repo. See code and docs for specifics.

## Goal

Night Desk: text-only detective CLI. Deterministic Python world state; local llama.cpp models for command routing, NPC dialogue, and narration.

## Layout

- **Root:** `main.py` entrypoint, `pyproject.toml` and `uv.lock` for dependency management (uv).
- **game/** Application logic: actions, router, NPC, narrator, llama availability notices, state, world, schemas, logging, parser, llama client.
- **tests/** Unittest-based tests.
- **docs/** Design and other documentation.
- **logs/** JSONL session logs (one file per run).

## Dependencies

Managed with **uv**. No third-party runtime deps; add with `uv add <pkg>`, dev with `uv add --dev <pkg>`. Commit `uv.lock`. Run app: `uv run python main.py`; run tests: `uv run python -m unittest discover -s tests -v`.

## Conventions

- Small, focused modules; clear names; comments only for non-obvious business rules.
- Log with timestamps; log progress in loops/iterations.
- No backward compatibility unless requested.
- Update README.md for human-facing changes, AGENTS.md for structure/goal changes.
