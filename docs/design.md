# Design Notes

## Architecture

The prototype is built around a deterministic state machine.

- [game/world.py](/Users/javier.cancela/Code/personal/virtual-world/game/world.py): handcrafted room, objects, aliases, puzzle constants, and initial state.
- [game/state.py](/Users/javier.cancela/Code/personal/virtual-world/game/state.py): typed game state and transcript buffer.
- [game/actions.py](/Users/javier.cancela/Code/personal/virtual-world/game/actions.py): validated state transitions. This is the source of truth.
- [game/router.py](/Users/javier.cancela/Code/personal/virtual-world/game/router.py): router model wrapper plus validation and fallback behavior.
- [game/npc.py](/Users/javier.cancela/Code/personal/virtual-world/game/npc.py): bounded NPC dialogue generation.
- [game/narration.py](/Users/javier.cancela/Code/personal/virtual-world/game/narration.py): bounded environment narration.
- [game/parser.py](/Users/javier.cancela/Code/personal/virtual-world/game/parser.py): sequential turn orchestration and logging.
- [game/logging.py](/Users/javier.cancela/Code/personal/virtual-world/game/logging.py): JSONL writer.

## World Design

The room is a single security office with six inspectable elements and one NPC.

Puzzle chain:

1. Inspect the visitor ledger.
2. Learn that the suspicious alias is `Silas Vale`.
3. Talk to Mara and prove you noticed the alias.
4. Mara reveals the steel cabinet code: `417`.
5. Open the cabinet.
6. Take the brass key.
7. Unlock the exit door.

The puzzle truth never lives in prompts. Prompts only receive facts already computed by the engine.

## Deterministic State

The state stores:

- current location
- discovered clues
- inventory
- object state flags
- conversation flags
- puzzle flags
- turn count
- escape/game-over flags
- recent transcript buffer

Models cannot mutate any of these directly.

## Router Constraints

The router uses a short mechanical prompt and a strict schema defined in [game/schemas.py](/Users/javier.cancela/Code/personal/virtual-world/game/schemas.py).

Flow:

1. Send player input and canonical object names.
2. Ask `llama-server` for constrained JSON.
3. Parse and validate the payload.
4. Canonicalize targets.
5. Reject invalid or unknown targets before they reach the engine.

If schema-constrained generation fails, the code retries with GBNF grammar. If that also fails, the action becomes `unknown` and the turn is logged safely.

## NPC Safety Boundaries

Mara's reply phase is decided deterministically in [game/actions.py](/Users/javier.cancela/Code/personal/virtual-world/game/actions.py).

The NPC model only gets:

- current conversation phase
- a short recent transcript summary
- explicit allowed facts
- explicit forbidden terms
- a style constraint

If the returned text includes a forbidden term such as the cabinet code before trust is earned, the code falls back to a deterministic line.

## Narrator Safety Boundaries

The narrator receives deterministic action facts and rewrites them into compact flavor text.

Guardrails:

- forbidden-term check for unrevealed secrets
- rejection of common unsupported affordance phrases such as hidden passages or extra rooms
- deterministic fallback text on transport or validation failure

## Logging Design

Every turn is written as one JSON object on one line.

The log stores enough to debug coherence issues:

- raw router output
- parsed router action
- validated action
- state snapshots before and after
- a compact state-transition record
- model prompt excerpts
- raw model text
- final rendered response
- any error string

## Known Limitations

- The post-checks for NPC and narrator are conservative but shallow. They catch obvious secret leaks, not every possible invented detail.
- The default runtime assumes `llama-server` is already running.
- The single-room design keeps scope tight; there is no save system and no multi-room navigation.
