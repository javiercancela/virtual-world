from __future__ import annotations

import os
from dataclasses import dataclass

from .actions import NPCContext
from .llama_client import LlamaServerClient, LlamaTransportError, extract_chat_text
from .state import GameState
from .world import NPC_NAME, ROOM_NAME


@dataclass(slots=True)
class NPCReply:
    text: str
    raw_output: str
    prompt_excerpt: str
    used_fallback: bool = False
    error: str | None = None


class NPCModel:
    def __init__(
        self,
        *,
        endpoint: str | None = None,
        model_name: str | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        self.endpoint = endpoint or os.getenv("VW_NPC_ENDPOINT", "http://127.0.0.1:8082/v1/chat/completions")
        self.model_name = model_name or os.getenv("VW_NPC_MODEL", "QwQ-32B")
        self.client = LlamaServerClient(self.endpoint, timeout_seconds=timeout_seconds)
        self.force_fallback = os.getenv("VW_FORCE_FALLBACK_TEXT", "0") == "1"

    def generate_reply(self, state: GameState, context: NPCContext) -> NPCReply:
        prompt = self._build_prompt(state, context)
        prompt_excerpt = prompt[:560]
        if self.force_fallback:
            return NPCReply(context.deterministic_text, context.deterministic_text, prompt_excerpt, used_fallback=True)

        try:
            payload = self.client.chat_completion(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": f"You are {NPC_NAME}, speaking inside a locked {ROOM_NAME}."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.6,
                max_tokens=120,
            )
            raw_output = extract_chat_text(payload)
            safe_text = self._post_check(raw_output, context)
            return NPCReply(safe_text, raw_output, prompt_excerpt)
        except (LlamaTransportError, ValueError) as exc:
            return NPCReply(
                context.deterministic_text,
                context.deterministic_text,
                prompt_excerpt,
                used_fallback=True,
                error=str(exc),
            )

    def _build_prompt(self, state: GameState, context: NPCContext) -> str:
        transcript_lines = [f"{line.speaker}: {line.text}" for line in state.recent_transcript[-6:]]
        transcript_summary = " | ".join(transcript_lines) if transcript_lines else "no prior conversation"
        facts = " ".join(f"- {fact}" for fact in context.allowed_facts)
        forbidden = ", ".join(context.forbidden_terms) if context.forbidden_terms else "none"
        return (
            f"Identity: {NPC_NAME}, suspicious but controlled night supervisor. "
            f"Current phase: {context.phase}. "
            f"Recent conversation: {transcript_summary}. "
            f"Player just said: {context.recent_player_line or '(no utterance)'}. "
            "Allowed world facts: "
            f"{facts} "
            f"Forbidden reveals: {forbidden}. "
            "Rules: stay in character, 1-3 sentences, no new facts, no new objects, no puzzle changes. "
            "If the player has not met the reveal condition, stay evasive and point back toward the ledger."
        )

    def _post_check(self, text: str, context: NPCContext) -> str:
        cleaned = " ".join(text.strip().split())
        if not cleaned:
            raise ValueError("NPC output was empty.")
        lowered = cleaned.lower()
        for forbidden in context.forbidden_terms:
            if forbidden and forbidden.lower() in lowered:
                raise ValueError(f"NPC output contained forbidden term: {forbidden}")
        return cleaned
