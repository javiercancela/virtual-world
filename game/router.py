from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

from .llama_client import LlamaServerClient, LlamaTransportError, extract_completion_text
from .schemas import RouterDecision, RouterValidationError, parse_router_payload
from .state import GameState
from .world import OBJECTS, SUPPORTED_INTENTS, canonicalize_name, visible_objects


@dataclass(slots=True)
class RouterTurn:
    decision: RouterDecision
    raw_output: str
    prompt_excerpt: str
    error: str | None = None
    used_constraint: str = "schema"


class RuleBasedRouter:
    """Deterministic fallback used in tests or when explicitly enabled."""

    def route(self, player_input: str, state: GameState) -> RouterTurn:
        lowered = player_input.strip().lower()
        decision = self._route(player_input, lowered)
        return RouterTurn(
            decision=decision,
            raw_output=json.dumps(decision.to_dict(), sort_keys=True),
            prompt_excerpt="rule-based-router",
            used_constraint="deterministic",
        )

    def _route(self, original: str, lowered: str) -> RouterDecision:
        if lowered in {"inventory", "inv", "i"}:
            return RouterDecision("inventory", None, None, None, 0.99)
        if lowered in {"help", "?"}:
            return RouterDecision("help", None, None, None, 0.99)
        if lowered in {"look", "look around", "where am i", "state"}:
            return RouterDecision("ask_state", None, None, None, 0.95)

        talk_match = re.match(r"^(talk|ask|speak)(?:\s+to)?\s+(.*)$", lowered)
        if talk_match:
            remainder = talk_match.group(2).strip()
            target = None
            utterance = original.strip()
            for separator in [" about ", " if ", " why ", " what ", ":"]:
                if separator in remainder:
                    target_candidate = remainder.split(separator, 1)[0].strip()
                    target = canonicalize_name(target_candidate)
                    break
            if target is None:
                target = canonicalize_name(remainder.split(maxsplit=1)[0]) or canonicalize_name(remainder)
            return RouterDecision("talk", target or "mara", None, utterance, 0.74)

        for intent, verbs in {
            "inspect": ["inspect", "examine", "look at", "read", "search"],
            "take": ["take", "grab", "pick up"],
            "move": ["move", "shift", "push"],
            "use": ["use", "open", "unlock"],
        }.items():
            for verb in verbs:
                if lowered.startswith(f"{verb} "):
                    remainder = lowered[len(verb):].strip()
                    if intent == "use" and " on " in remainder:
                        first, second = remainder.split(" on ", 1)
                        return RouterDecision(intent, first.strip(), second.strip(), None, 0.77)
                    return RouterDecision(intent, remainder, None, None, 0.77)

        if canonicalize_name(lowered) == "mara":
            return RouterDecision("talk", "mara", None, original.strip(), 0.60)

        return RouterDecision("unknown", None, None, None, 0.0)


class RouterModel:
    def __init__(
        self,
        *,
        endpoint: str | None = None,
        model_name: str | None = None,
        timeout_seconds: float = 12.0,
        allow_rule_fallback: bool = False,
    ) -> None:
        configured_endpoint = endpoint or os.getenv("VW_ROUTER_ENDPOINT", "http://127.0.0.1:8081/v1/completions")
        self.endpoint = self._normalize_completion_endpoint(configured_endpoint)
        self.model_name = model_name or os.getenv("VW_ROUTER_MODEL", "Qwen3-4B")
        self.client = LlamaServerClient(self.endpoint, timeout_seconds=timeout_seconds)
        self.rule_router = RuleBasedRouter()
        self.allow_rule_fallback = allow_rule_fallback or os.getenv("VW_FORCE_RULE_ROUTER", "0") == "1"

    def route(self, player_input: str, state: GameState) -> RouterTurn:
        if self.allow_rule_fallback:
            return self.rule_router.route(player_input, state)

        prompt = self._build_prompt(player_input, state)
        prompt_excerpt = prompt[:480]

        try:
            response_payload = self.client.text_completion(
                model=self.model_name,
                prompt=prompt,
                temperature=0.0,
                max_tokens=128,
            )
            raw_output = extract_completion_text(response_payload)
            decision = parse_router_payload(raw_output)
            return RouterTurn(
                decision=decision,
                raw_output=raw_output,
                prompt_excerpt=prompt_excerpt,
                used_constraint="prompted_json",
            )
        except (LlamaTransportError, RouterValidationError) as exc:
            raw_output = ""
            error_message = f"prompted_json: {exc}"

        if self.allow_rule_fallback:
            fallback_turn = self.rule_router.route(player_input, state)
            fallback_turn.error = error_message
            return fallback_turn
        return RouterTurn(
            decision=RouterDecision("unknown", None, None, None, 0.0),
            raw_output=raw_output,
            prompt_excerpt=prompt_excerpt,
            error=error_message,
            used_constraint="failed",
        )

    def _build_prompt(self, player_input: str, state: GameState) -> str:
        visible = ", ".join(visible_objects(state) + ["mara"])
        intent_list = ", ".join(SUPPORTED_INTENTS)
        return (
            "/no_think\n"
            "Return only one compact JSON object with exactly these keys in this order: "
            '"intent", "target", "secondary_target", "utterance", "confidence". '
            "Supported intents: "
            f"{intent_list}. "
            "Canonical names: "
            f"{visible}. "
            "Normalize references to canonical names when possible. "
            "Use utterance only for talk; otherwise return null. "
            "Use null for missing targets. "
            "If unsure, choose unknown with null targets and utterance. "
            f"Player input: {player_input.strip()}"
        )

    def _normalize_completion_endpoint(self, endpoint: str) -> str:
        return endpoint.replace("/v1/chat/completions", "/v1/completions")


@dataclass(slots=True)
class ValidatedAction:
    intent: str
    target: str | None
    secondary_target: str | None
    utterance: str | None
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "target": self.target,
            "secondary_target": self.secondary_target,
            "utterance": self.utterance,
            "confidence": self.confidence,
        }


KNOWN_USE_SECONDARIES = {"exit door", "steel cabinet", "mara", "visitor ledger", "brass key"}


def validate_router_decision(decision: RouterDecision) -> ValidatedAction:
    target = canonicalize_name(decision.target)
    secondary = canonicalize_name(decision.secondary_target)

    if decision.intent in {"inventory", "help", "ask_state", "unknown"}:
        target = None
        secondary = None

    if decision.intent == "talk":
        target = target or "mara"
        if target != "mara":
            return ValidatedAction("unknown", None, None, None, decision.confidence)

    if decision.intent in {"inspect", "take", "move"} and target is None:
        return ValidatedAction("unknown", None, None, None, decision.confidence)

    if decision.intent == "use" and target is None:
        return ValidatedAction("unknown", None, None, None, decision.confidence)

    if decision.intent == "use" and secondary is not None and secondary not in KNOWN_USE_SECONDARIES:
        return ValidatedAction("unknown", None, None, None, decision.confidence)

    if target is not None and target not in OBJECTS:
        return ValidatedAction("unknown", None, None, None, decision.confidence)

    return ValidatedAction(
        intent=decision.intent,
        target=target,
        secondary_target=secondary,
        utterance=decision.utterance,
        confidence=decision.confidence,
    )
