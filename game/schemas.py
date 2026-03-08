from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .world import SUPPORTED_INTENTS


ROUTER_ACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "intent": {"type": "string", "enum": SUPPORTED_INTENTS},
        "target": {"type": ["string", "null"]},
        "secondary_target": {"type": ["string", "null"]},
        "utterance": {"type": ["string", "null"]},
        "confidence": {"type": "number"},
    },
    "required": ["intent", "target", "secondary_target", "utterance", "confidence"],
    "additionalProperties": False,
}

ROUTER_ACTION_GBNF = r'''
root ::= ws object ws
object ::= "{" ws
    "\"intent\"" ws ":" ws intent ws "," ws
    "\"target\"" ws ":" ws nullable_string ws "," ws
    "\"secondary_target\"" ws ":" ws nullable_string ws "," ws
    "\"utterance\"" ws ":" ws nullable_string ws "," ws
    "\"confidence\"" ws ":" ws number ws
"}" 
intent ::= "\"talk\"" | "\"inspect\"" | "\"use\"" | "\"take\"" | "\"move\"" | "\"inventory\"" | "\"ask_state\"" | "\"help\"" | "\"unknown\""
nullable_string ::= string | "null"
string ::= "\"" chars "\""
chars ::= "" | char chars
char ::= [^"\\\x00-\x1F] | "\\" escape
escape ::= ["\\/bfnrt] | "u" hex hex hex hex
hex ::= [0-9a-fA-F]
number ::= int frac? exp?
int ::= "-"? digit1to9 digits? | "0"
digits ::= digit digits | ""
digit ::= [0-9]
digit1to9 ::= [1-9]
frac ::= "." digits1
exp ::= [eE] [+-]? digits1
digits1 ::= digit digits
ws ::= [ \t\n\r]*
'''.strip()


class RouterValidationError(ValueError):
    """Raised when a router payload fails schema validation."""


@dataclass(slots=True)
class RouterDecision:
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


@dataclass(slots=True)
class TextReply:
    text: str


def parse_router_payload(raw_text: str) -> RouterDecision:
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RouterValidationError(f"Router output was not valid JSON: {exc}") from exc
    return validate_router_payload(payload)


def validate_router_payload(payload: Any) -> RouterDecision:
    if not isinstance(payload, dict):
        raise RouterValidationError("Router output must be a JSON object.")

    extra_keys = set(payload) - set(ROUTER_ACTION_SCHEMA["properties"])
    if extra_keys:
        raise RouterValidationError(f"Unexpected router keys: {sorted(extra_keys)}")

    missing_keys = [
        key for key in ROUTER_ACTION_SCHEMA["required"] if key not in payload
    ]
    if missing_keys:
        raise RouterValidationError(f"Missing router keys: {missing_keys}")

    intent = payload["intent"]
    if intent not in SUPPORTED_INTENTS:
        raise RouterValidationError(f"Unsupported intent: {intent}")

    target = payload["target"]
    secondary_target = payload["secondary_target"]
    utterance = payload["utterance"]
    confidence = payload["confidence"]

    for field_name, field_value in {
        "target": target,
        "secondary_target": secondary_target,
        "utterance": utterance,
    }.items():
        if field_value is not None and not isinstance(field_value, str):
            raise RouterValidationError(f"{field_name} must be a string or null.")

    if not isinstance(confidence, (int, float)):
        raise RouterValidationError("confidence must be numeric.")

    return RouterDecision(
        intent=intent,
        target=target.strip() if isinstance(target, str) else None,
        secondary_target=secondary_target.strip() if isinstance(secondary_target, str) else None,
        utterance=utterance.strip() if isinstance(utterance, str) else None,
        confidence=float(confidence),
    )
