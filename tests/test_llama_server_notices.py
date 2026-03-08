from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from game.actions import ActionEngine
from game.logging import TurnLogger
from game.narration import NarrationReply
from game.npc import NPCReply
from game.parser import TurnProcessor
from game.router import RouterTurn, RuleBasedRouter
from game.schemas import RouterDecision
from game.world import build_initial_state


ROUTER_ENDPOINT = "http://127.0.0.1:8081/v1/chat/completions"
TEXT_ENDPOINT = "http://127.0.0.1:8082/v1/chat/completions"
ROUTER_ERROR = (
    f"schema: Unable to reach llama-server at {ROUTER_ENDPOINT}: <urlopen error [Errno 111] Connection refused>; "
    f"grammar: Unable to reach llama-server at {ROUTER_ENDPOINT}: <urlopen error [Errno 111] Connection refused>"
)
TEXT_ERROR = f"Unable to reach llama-server at {TEXT_ENDPOINT}: <urlopen error [Errno 111] Connection refused>"


class UnavailableRouter:
    endpoint = ROUTER_ENDPOINT

    def route(self, player_input: str, state: object) -> RouterTurn:
        return RouterTurn(
            decision=RouterDecision("unknown", None, None, None, 0.0),
            raw_output="",
            prompt_excerpt="router unavailable",
            error=ROUTER_ERROR,
            used_constraint="failed",
        )


class UnavailableNarrator:
    endpoint = TEXT_ENDPOINT

    def opening_scene(self, state: object, facts: list[str]) -> NarrationReply:
        return NarrationReply(
            text="Rain needles the glass while Mara Voss watches from the far side of the desk.",
            raw_output="fallback opening",
            prompt_excerpt="opening",
            used_fallback=True,
            error=TEXT_ERROR,
        )

    def narrate(self, state: object, context: object) -> NarrationReply:
        return NarrationReply(
            text="The office stays still around you.",
            raw_output="fallback narration",
            prompt_excerpt="narration",
            used_fallback=True,
            error=TEXT_ERROR,
        )


class StaticNPC:
    endpoint = TEXT_ENDPOINT

    def generate_reply(self, state: object, context: object) -> NPCReply:
        return NPCReply(
            text="Mara says nothing.",
            raw_output="npc fallback",
            prompt_excerpt="npc",
        )


class LlamaServerNoticeTests(unittest.TestCase):
    def build_processor(self, path: Path, *, router: object, narrator: object) -> TurnProcessor:
        return TurnProcessor(
            state=build_initial_state(),
            router=router,
            engine=ActionEngine(),
            narrator=narrator,
            npc=StaticNPC(),
            logger=TurnLogger(path),
        )

    def test_router_transport_failure_reports_configured_urls(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "router-unavailable.jsonl"
            processor = self.build_processor(log_path, router=UnavailableRouter(), narrator=UnavailableNarrator())

            result = processor.process_turn("inspect visitor ledger")

            self.assertIn("llama-server is not running", result.rendered_response)
            self.assertIn(ROUTER_ENDPOINT, result.rendered_response)
            self.assertIn(TEXT_ENDPOINT, result.rendered_response)
            self.assertNotIn("That does not resolve into a safe action", result.rendered_response)
            payload = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(payload["state_transition"]["events"], ["router_transport_failure"])
            self.assertEqual(payload["validated_action"]["intent"], "unknown")

    def test_opening_text_appends_unavailable_notice(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "opening-unavailable.jsonl"
            processor = self.build_processor(log_path, router=RuleBasedRouter(), narrator=UnavailableNarrator())

            opening_text = processor.opening_text()

            self.assertIn("Rain needles the glass", opening_text)
            self.assertIn("llama-server is not running", opening_text)
            self.assertIn(TEXT_ENDPOINT, opening_text)

    def test_turn_narration_appends_unavailable_notice(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "turn-unavailable.jsonl"
            processor = self.build_processor(log_path, router=RuleBasedRouter(), narrator=UnavailableNarrator())

            result = processor.process_turn("look")

            self.assertIn("The office stays still around you.", result.rendered_response)
            self.assertIn("llama-server is not running", result.rendered_response)
            self.assertIn(TEXT_ENDPOINT, result.rendered_response)
            payload = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(payload["error"], TEXT_ERROR)


if __name__ == "__main__":
    unittest.main()
