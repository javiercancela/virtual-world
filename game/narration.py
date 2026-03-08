from __future__ import annotations

import os
from dataclasses import dataclass

from .actions import NarrationContext
from .llama_client import LlamaServerClient, LlamaTransportError, extract_chat_text
from .state import GameState
from .world import ROOM_NAME


@dataclass(slots=True)
class NarrationReply:
    text: str
    raw_output: str
    prompt_excerpt: str
    used_fallback: bool = False
    error: str | None = None


class NarratorModel:
    def __init__(
        self,
        *,
        endpoint: str | None = None,
        model_name: str | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        self.endpoint = endpoint or os.getenv("VW_NARRATOR_ENDPOINT", "http://127.0.0.1:8082/v1/chat/completions")
        self.model_name = model_name or os.getenv("VW_NARRATOR_MODEL", "QwQ-32B")
        self.client = LlamaServerClient(self.endpoint, timeout_seconds=timeout_seconds)
        self.force_fallback = os.getenv("VW_FORCE_FALLBACK_TEXT", "0") == "1"

    def narrate(self, state: GameState, context: NarrationContext) -> NarrationReply:
        prompt = self._build_prompt(state, context)
        prompt_excerpt = prompt[:560]
        if self.force_fallback:
            return NarrationReply(context.deterministic_text, context.deterministic_text, prompt_excerpt, used_fallback=True)

        try:
            payload = self.client.chat_completion(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": f"You are the concise narrator of a text-only detective game set in a single {ROOM_NAME}."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                max_tokens=140,
            )
            raw_output = extract_chat_text(payload)
            safe_text = self._post_check(raw_output, context)
            return NarrationReply(safe_text, raw_output, prompt_excerpt)
        except (LlamaTransportError, ValueError) as exc:
            return NarrationReply(
                context.deterministic_text,
                context.deterministic_text,
                prompt_excerpt,
                used_fallback=True,
                error=str(exc),
            )

    def opening_scene(self, state: GameState, facts: list[str]) -> NarrationReply:
        context = NarrationContext(
            action_name="opening_scene",
            deterministic_text=" ".join(facts),
            facts=facts,
        )
        return self.narrate(state, context)

    def _build_prompt(self, state: GameState, context: NarrationContext) -> str:
        facts = " ".join(f"- {fact}" for fact in context.facts)
        forbidden = ", ".join(context.forbidden_terms) if context.forbidden_terms else "none"
        return (
            f"Action: {context.action_name}. "
            f"Room: {state.current_location}. "
            f"Turn: {state.turn_count}. "
            "Deterministic facts to preserve: "
            f"{facts} "
            f"Forbidden terms unless already in the deterministic facts: {forbidden}. "
            "Write 1-3 sentences of atmospheric but compact text. Do not add new interactive affordances, new objects, or hidden mechanisms."
        )

    def _post_check(self, text: str, context: NarrationContext) -> str:
        cleaned = " ".join(text.strip().split())
        if not cleaned:
            raise ValueError("Narrator output was empty.")
        lowered = cleaned.lower()
        for forbidden in context.forbidden_terms:
            if forbidden and forbidden.lower() in lowered:
                raise ValueError(f"Narrator output contained forbidden term: {forbidden}")
        affordance_markers = ["you could also", "a hidden", "another room", "secret passage", "vent", "drawer"]
        if any(marker in lowered for marker in affordance_markers):
            raise ValueError("Narrator output introduced an unsupported affordance.")
        return cleaned
