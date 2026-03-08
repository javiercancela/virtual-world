from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from game.actions import ActionEngine
from game.logging import TurnLogger
from game.parser import TurnProcessor
from game.router import RuleBasedRouter, validate_router_decision
from game.schemas import RouterValidationError, parse_router_payload
from game.narration import NarratorModel
from game.npc import NPCModel
from game.world import CABINET_CODE, build_initial_state


class EngineTests(unittest.TestCase):
    def test_initial_state(self) -> None:
        state = build_initial_state()
        self.assertEqual(state.current_location, "Security Office")
        self.assertFalse(state.escaped)
        self.assertTrue(state.object_states["steel cabinet"]["locked"])
        self.assertEqual(state.inventory, [])

    def test_router_schema_validation(self) -> None:
        decision = parse_router_payload(
            '{"intent":"inspect","target":"visitor ledger","secondary_target":null,"utterance":null,"confidence":0.91}'
        )
        self.assertEqual(decision.intent, "inspect")
        self.assertEqual(decision.target, "visitor ledger")

        with self.assertRaises(RouterValidationError):
            parse_router_payload(
                '{"intent":"inspect","target":"visitor ledger","secondary_target":null,"utterance":null,"confidence":0.91,"extra":true}'
            )

    def test_invalid_action_does_not_corrupt_state(self) -> None:
        state = build_initial_state()
        engine = ActionEngine()
        action = validate_router_decision(RuleBasedRouter().route("take lamp", state).decision)
        before = state.to_dict()
        outcome = engine.apply(state, action)
        after = state.to_dict()
        self.assertFalse(outcome.success)
        self.assertEqual(before, after)

    def test_reveal_gating_for_npc(self) -> None:
        state = build_initial_state()
        engine = ActionEngine()

        talk_action = validate_router_decision(RuleBasedRouter().route("talk to Mara about the cabinet", state).decision)
        outcome = engine.apply(state, talk_action)

        self.assertEqual(outcome.response_mode, "npc")
        self.assertFalse(state.puzzle_flags["cabinet_code_known"])
        self.assertNotIn(CABINET_CODE, outcome.deterministic_text)

    def test_ledger_reference_without_alias_does_not_unlock_code(self) -> None:
        state = build_initial_state()
        engine = ActionEngine()
        router = RuleBasedRouter()

        inspect_action = validate_router_decision(router.route("inspect visitor ledger", state).decision)
        engine.apply(state, inspect_action)
        talk_action = validate_router_decision(router.route("talk to Mara about the ledger", state).decision)
        outcome = engine.apply(state, talk_action)

        self.assertEqual(outcome.response_mode, "npc")
        self.assertFalse(state.puzzle_flags["cabinet_code_known"])
        self.assertNotIn(CABINET_CODE, outcome.deterministic_text)

    def test_using_key_on_wrong_target_does_not_escape(self) -> None:
        state = build_initial_state()
        engine = ActionEngine()
        router = RuleBasedRouter()

        for command in [
            "inspect visitor ledger",
            "talk to Mara about Silas Vale",
            "use steel cabinet",
            "take brass key",
        ]:
            action = validate_router_decision(router.route(command, state).decision)
            engine.apply(state, action)

        wrong_use = validate_router_decision(router.route("use brass key on Mara", state).decision)
        outcome = engine.apply(state, wrong_use)

        self.assertFalse(outcome.success)
        self.assertFalse(state.escaped)
        self.assertTrue(state.object_states["exit door"]["locked"])

    def test_win_condition(self) -> None:
        state = build_initial_state()
        engine = ActionEngine()
        router = RuleBasedRouter()

        for command in [
            "inspect visitor ledger",
            "talk to Mara about Silas Vale",
            "use steel cabinet",
            "take brass key",
            "use brass key on exit door",
        ]:
            action = validate_router_decision(router.route(command, state).decision)
            outcome = engine.apply(state, action)
            self.assertTrue(outcome.success, command)

        self.assertTrue(state.escaped)
        self.assertTrue(state.game_over)

    def test_jsonl_logging(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "turns.jsonl"
            logger = TurnLogger(path)
            logger.log_turn({"turn_index": 1, "player_input": "look", "state_after": {"turn_count": 1}})
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            payload = json.loads(lines[0])
            self.assertEqual(payload["turn_index"], 1)
            self.assertEqual(payload["player_input"], "look")
            self.assertIn("timestamp", payload)
