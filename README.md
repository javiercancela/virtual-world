# Night Desk

`Night Desk` is a small text-only detective CLI prototype. The world state is deterministic Python data, while local `llama.cpp` models handle command routing, NPC dialogue, and narration.

## What It Builds

- One fixed location: a locked security office.
- One main NPC: Mara Voss.
- One short puzzle chain: inspect the right clue, earn Mara's trust, open the cabinet, take the key, unlock the exit.
- One JSONL log entry per turn with raw model outputs and state transitions.

## Repository Layout

```text
.
├── README.md
├── pyproject.toml
├── uv.lock
├── docs/
│   └── design.md
├── game/
│   ├── __init__.py
│   ├── actions.py
│   ├── llama_client.py
│   ├── logging.py
│   ├── narration.py
│   ├── npc.py
│   ├── parser.py
│   ├── router.py
│   ├── schemas.py
│   ├── state.py
│   └── world.py
├── logs/
├── main.py
└── tests/
    ├── test_game_engine.py
    └── test_transcripts.py
```

## Python Setup

Dependencies are managed with [uv](https://docs.astral.sh/uv/). No third-party packages are required; the lockfile pins the environment.

**Prerequisites:** [Install uv](https://docs.astral.sh/uv/getting-started/installation/) (e.g. `curl -LsSf https://astral.sh/uv/install.sh | sh`).

```bash
# Create virtual environment and sync (install dependencies from lockfile)
uv sync

# Run the game
uv run python main.py
```

To add dependencies later: `uv add <package>` (or `uv add --dev <package>` for dev tools). Commit `uv.lock` for reproducible installs.

## Model Setup

The default runtime expects local `llama-server` instances with OpenAI-compatible chat endpoints.

### Required model roles

- Router: `Qwen3-4B` GGUF on a small server.
- NPC dialogue: `QwQ-32B` Q4 GGUF.
- Narrator/composer: `QwQ-32B` Q4 GGUF.

### Example `llama-server` launch commands

Run the router model on port `8081`:

```bash
./llama-server \
  -m /models/Qwen3-4B-Instruct-Q4_K_M.gguf \
  --alias Qwen3-4B \
  --port 8081
```

Run the larger dialogue/narration model on port `8082`:

```bash
./llama-server \
  -m /models/QwQ-32B-Q4_K_M.gguf \
  --alias QwQ-32B \
  --port 8082
```

You can point both NPC and narrator roles at the same `QwQ-32B` server.

### Environment variables

```bash
export VW_ROUTER_ENDPOINT=http://127.0.0.1:8081/v1/chat/completions
export VW_ROUTER_MODEL=Qwen3-4B
export VW_NPC_ENDPOINT=http://127.0.0.1:8082/v1/chat/completions
export VW_NPC_MODEL=QwQ-32B
export VW_NARRATOR_ENDPOINT=http://127.0.0.1:8082/v1/chat/completions
export VW_NARRATOR_MODEL=QwQ-32B
```

Optional development flags:

```bash
export VW_FORCE_RULE_ROUTER=1
export VW_FORCE_FALLBACK_TEXT=1
```

`VW_FORCE_RULE_ROUTER=1` enables the deterministic fallback router for offline development. The default path still targets the local models.

## Structured Router Output

The router schema lives in [game/schemas.py](/Users/javier.cancela/Code/personal/virtual-world/game/schemas.py). The router client in [game/router.py](/Users/javier.cancela/Code/personal/virtual-world/game/router.py) sends one of two constrained generation requests to `llama-server`:

1. Preferred: `response_format` with `type: json_schema`.
2. Fallback: top-level `grammar` with the bundled GBNF grammar.

If both attempts fail or parse into an invalid object, the engine classifies the turn as `unknown`, asks the player to rephrase, and logs the failure.

Example router request payload shape:

```json
{
  "model": "Qwen3-4B",
  "messages": [
    {"role": "system", "content": "You normalize text commands into compact JSON actions."},
    {"role": "user", "content": "Supported intents: talk, inspect, use, take, move, inventory, ask_state, help, unknown. Canonical names: exit door, steel cabinet, desk, visitor ledger, framed photo, coat rack, mara. Return one JSON object matching the schema. Player input: inspect ledger"}
  ],
  "temperature": 0.0,
  "max_tokens": 128,
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "router_action",
      "schema": {
        "type": "object"
      }
    }
  }
}
```

Example router result:

```json
{
  "intent": "inspect",
  "target": "visitor ledger",
  "secondary_target": null,
  "utterance": null,
  "confidence": 0.93
}
```

## Running the Game

```bash
uv run python main.py
```

Useful commands in-game:

- `look`
- `inspect ledger`
- `talk to Mara about Silas Vale`
- `use steel cabinet`
- `take brass key`
- `use brass key on exit door`
- `inventory`
- `help`
- `quit`

## Running Tests

```bash
uv run python -m unittest discover -s tests -v
```

## Logs

Logs are written to `logs/session-<timestamp>.jsonl`.

Each line includes:

- `turn_index`
- `player_input`
- `router_raw_output`
- `router_parsed_output`
- `validated_action`
- `state_before`
- `state_transition`
- `state_after`
- optional NPC/narrator prompt excerpts and raw outputs
- `rendered_response`
- `error`
