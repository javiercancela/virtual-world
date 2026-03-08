"""Local-LLM detective CLI prototype."""

from .parser import TurnProcessor, build_default_processor
from .state import GameState
from .world import build_initial_state

__all__ = ["GameState", "TurnProcessor", "build_default_processor", "build_initial_state"]
