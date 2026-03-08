from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from game.actions import ActionEngine
from game.logging import TurnLogger
from game.narration import NarratorModel
from game.npc import NPCModel
from game.parser import TurnProcessor
from game.router import RuleBasedRouter
from game.world import build_initial_state


class TranscriptTests(unittest.TestCase):
    def build_processor(self, path: Path) -> TurnProcessor:
        return TurnProcessor(
            state=build_initial_state(),
            router=RuleBasedRouter(),
            engine=ActionEngine(),
            narrator=NarratorModel(),
            npc=NPCModel(),
            logger=TurnLogger(path),
        )

    def test_full_success_transcript(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "success.jsonl"
            processor = self.build_processor(log_path)
            commands = [
                "look",
                "inspect visitor ledger",
                "talk to Mara about Silas Vale",
                "use steel cabinet",
                "take brass key",
                "use brass key on exit door",
            ]
            outputs = [processor.process_turn(command).rendered_response for command in commands]
            self.assertTrue(processor.state.escaped)
            self.assertIn("417", outputs[2])
            self.assertIn("step free", outputs[-1].lower())
            lines = log_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), len(commands))
            last_payload = json.loads(lines[-1])
            self.assertTrue(last_payload["state_after"]["escaped"])

    def test_invalid_then_recovery_transcript(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "recovery.jsonl"
            processor = self.build_processor(log_path)
            commands = [
                "take lamp",
                "talk to Mara",
                "use steel cabinet",
                "inspect visitor ledger",
                "talk to Mara about Vale",
                "use steel cabinet",
                "take brass key",
                "use exit door",
            ]
            outputs = [processor.process_turn(command).rendered_response for command in commands]
            self.assertIn("rephrase", outputs[0].lower())
            self.assertIn("ledger", outputs[1].lower())
            self.assertTrue(processor.state.escaped)
            payloads = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(payloads[0]["validated_action"]["intent"], "unknown")
            self.assertFalse(payloads[0]["state_after"]["escaped"])
            self.assertEqual(payloads[0]["error"], "unknown_action")
