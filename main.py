from __future__ import annotations

from pathlib import Path

from game.parser import build_default_processor
from game.world import HELP_TEXT


QUIT_COMMANDS = {"quit", "exit"}


def main() -> int:
    processor = build_default_processor()
    print("Night Desk")
    print(processor.opening_text())
    print(HELP_TEXT)

    while True:
        try:
            player_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSession closed.")
            return 0

        if not player_input:
            print("Type a command or `help`.")
            continue
        if player_input.lower() in QUIT_COMMANDS:
            print("Session closed.")
            return 0

        result = processor.process_turn(player_input)
        print(result.rendered_response)
        if processor.state.game_over:
            print("You escaped the office.")
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
