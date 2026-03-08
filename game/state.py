from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


TRANSCRIPT_LIMIT = 8


@dataclass(slots=True)
class TranscriptLine:
    speaker: str
    text: str

    def to_dict(self) -> dict[str, str]:
        return {"speaker": self.speaker, "text": self.text}


@dataclass(slots=True)
class GameState:
    current_location: str
    discovered_clues: list[str] = field(default_factory=list)
    inventory: list[str] = field(default_factory=list)
    object_states: dict[str, dict[str, Any]] = field(default_factory=dict)
    conversation_flags: dict[str, bool] = field(default_factory=dict)
    puzzle_flags: dict[str, bool] = field(default_factory=dict)
    turn_count: int = 0
    escaped: bool = False
    game_over: bool = False
    recent_transcript: list[TranscriptLine] = field(default_factory=list)

    def add_clue(self, clue: str) -> bool:
        if clue in self.discovered_clues:
            return False
        self.discovered_clues.append(clue)
        self.discovered_clues.sort()
        return True

    def add_item(self, item: str) -> bool:
        if item in self.inventory:
            return False
        self.inventory.append(item)
        self.inventory.sort()
        return True

    def add_transcript_line(self, speaker: str, text: str) -> None:
        self.recent_transcript.append(TranscriptLine(speaker=speaker, text=text))
        if len(self.recent_transcript) > TRANSCRIPT_LIMIT:
            self.recent_transcript = self.recent_transcript[-TRANSCRIPT_LIMIT:]

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_location": self.current_location,
            "discovered_clues": list(self.discovered_clues),
            "inventory": list(self.inventory),
            "object_states": {
                name: dict(sorted(flags.items()))
                for name, flags in sorted(self.object_states.items())
            },
            "conversation_flags": dict(sorted(self.conversation_flags.items())),
            "puzzle_flags": dict(sorted(self.puzzle_flags.items())),
            "turn_count": self.turn_count,
            "escaped": self.escaped,
            "game_over": self.game_over,
            "recent_transcript": [line.to_dict() for line in self.recent_transcript],
        }
