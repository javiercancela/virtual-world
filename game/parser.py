from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .actions import ActionEngine
from .logging import TurnLogger, default_log_path
from .narration import NarrationReply, NarratorModel
from .npc import NPCModel, NPCReply
from .router import RouterModel, RouterTurn, ValidatedAction, validate_router_decision
from .state import GameState
from .world import OPENING_FACTS, build_initial_state


@dataclass(slots=True)
class TurnResult:
    rendered_response: str
    validated_action: ValidatedAction
    error: str | None = None


class TurnProcessor:
    def __init__(
        self,
        *,
        state: GameState,
        router: Any,
        engine: ActionEngine,
        narrator: NarratorModel,
        npc: NPCModel,
        logger: TurnLogger,
    ) -> None:
        self.state = state
        self.router = router
        self.engine = engine
        self.narrator = narrator
        self.npc = npc
        self.logger = logger

    def opening_text(self) -> str:
        reply = self.narrator.opening_scene(self.state, OPENING_FACTS)
        return reply.text

    def process_turn(self, player_input: str) -> TurnResult:
        state_before = self.state.to_dict()
        turn_index = self.state.turn_count + 1
        router_turn = self.router.route(player_input, self.state)
        validated_action = validate_router_decision(router_turn.decision)
        outcome = self.engine.apply(self.state, validated_action)

        narrator_reply: NarrationReply | None = None
        npc_reply: NPCReply | None = None
        rendered_response = outcome.deterministic_text
        error = router_turn.error or outcome.error

        if outcome.response_mode == "narrator" and outcome.narrator_context is not None:
            narrator_reply = self.narrator.narrate(self.state, outcome.narrator_context)
            rendered_response = narrator_reply.text
            error = error or narrator_reply.error
        elif outcome.response_mode == "npc" and outcome.npc_context is not None:
            npc_reply = self.npc.generate_reply(self.state, outcome.npc_context)
            rendered_response = npc_reply.text
            error = error or npc_reply.error

        self.state.turn_count += 1
        self.state.add_transcript_line("player", player_input.strip())
        speaker = "mara" if npc_reply is not None else "narrator"
        self.state.add_transcript_line(speaker, rendered_response)
        state_after = self.state.to_dict()

        self.logger.log_turn(
            {
                "turn_index": turn_index,
                "player_input": player_input,
                "router_prompt_excerpt": router_turn.prompt_excerpt,
                "router_raw_output": router_turn.raw_output,
                "router_parsed_output": router_turn.decision.to_dict(),
                "validated_action": validated_action.to_dict(),
                "state_before": state_before,
                "state_transition": outcome.state_transition,
                "state_after": state_after,
                "npc_prompt_excerpt": npc_reply.prompt_excerpt if npc_reply else None,
                "npc_raw_output": npc_reply.raw_output if npc_reply else None,
                "narrator_prompt_excerpt": narrator_reply.prompt_excerpt if narrator_reply else None,
                "narrator_raw_output": narrator_reply.raw_output if narrator_reply else None,
                "rendered_response": rendered_response,
                "error": error,
            }
        )

        return TurnResult(rendered_response=rendered_response, validated_action=validated_action, error=error)


def build_default_processor(log_path: str | None = None) -> TurnProcessor:
    state = build_initial_state()
    return TurnProcessor(
        state=state,
        router=RouterModel(),
        engine=ActionEngine(),
        narrator=NarratorModel(),
        npc=NPCModel(),
        logger=TurnLogger(default_log_path() if log_path is None else Path(log_path)),
    )
