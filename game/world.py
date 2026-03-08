from __future__ import annotations

from dataclasses import dataclass

from .state import GameState


ROOM_NAME = "Security Office"
NPC_NAME = "Mara Voss"
CABINET_CODE = "417"
VISITOR_ALIAS = "Silas Vale"
EXIT_KEY = "brass key"


@dataclass(frozen=True, slots=True)
class ObjectDefinition:
    name: str
    aliases: tuple[str, ...]
    portable: bool = False
    movable: bool = False
    inspect_summary: str = ""


OBJECTS: dict[str, ObjectDefinition] = {
    "exit door": ObjectDefinition(
        name="exit door",
        aliases=("door", "exit", "office door"),
        inspect_summary="A reinforced door with a brass lock cylinder and no keypad.",
    ),
    "steel cabinet": ObjectDefinition(
        name="steel cabinet",
        aliases=("cabinet", "locker", "storage cabinet"),
        inspect_summary="A waist-high steel cabinet with a three-digit keypad.",
    ),
    "desk": ObjectDefinition(
        name="desk",
        aliases=("security desk", "table"),
        inspect_summary="A cramped desk stacked with incident forms and a visitor ledger.",
    ),
    "visitor ledger": ObjectDefinition(
        name="visitor ledger",
        aliases=("ledger", "visitor book", "logbook", "log book", "book"),
        inspect_summary="A paper ledger opened to the last page of sign-ins.",
    ),
    "framed photo": ObjectDefinition(
        name="framed photo",
        aliases=("photo", "picture", "frame"),
        movable=True,
        inspect_summary="A framed staff photo hangs slightly crooked beside the door.",
    ),
    "coat rack": ObjectDefinition(
        name="coat rack",
        aliases=("rack", "coat stand", "stand", "raincoat"),
        movable=True,
        inspect_summary="A coat rack holds Mara's raincoat and an empty key clip.",
    ),
    EXIT_KEY: ObjectDefinition(
        name=EXIT_KEY,
        aliases=("key", "cabinet key", "brass key"),
        portable=True,
        inspect_summary="A heavy brass key tagged EXIT.",
    ),
    "mara": ObjectDefinition(
        name="mara",
        aliases=("mara voss", "guard", "supervisor", "npc", "woman"),
        inspect_summary="Mara Voss sits on the edge of the desk, watching carefully.",
    ),
}

OBJECT_ORDER = [
    "exit door",
    "steel cabinet",
    "desk",
    "visitor ledger",
    "framed photo",
    "coat rack",
]

SUPPORTED_INTENTS = [
    "talk",
    "inspect",
    "use",
    "take",
    "move",
    "inventory",
    "ask_state",
    "help",
    "unknown",
]

HELP_TEXT = "Commands: inspect <object>, talk to Mara, use <item> on <target>, take <item>, move <object>, inventory, look, help, quit."

OPENING_FACTS = [
    "You are locked inside a security office while rain rattles the shutters.",
    "Mara Voss, the night supervisor, is inside with you and clearly knows more than she wants to say.",
    "The exit door is locked.",
    "A steel cabinet with a keypad stands under the wall clock.",
    "A desk holds a visitor ledger.",
]


ALIAS_TO_CANONICAL: dict[str, str] = {}
for canonical_name, definition in OBJECTS.items():
    ALIAS_TO_CANONICAL[canonical_name] = canonical_name
    for alias in definition.aliases:
        ALIAS_TO_CANONICAL[alias] = canonical_name


def canonicalize_name(raw_name: str | None) -> str | None:
    if raw_name is None:
        return None
    cleaned = " ".join(raw_name.lower().strip().split())
    if not cleaned:
        return None
    return ALIAS_TO_CANONICAL.get(cleaned)


def visible_objects(state: GameState) -> list[str]:
    names = list(OBJECT_ORDER)
    if state.object_states[EXIT_KEY]["available"] and not state.object_states[EXIT_KEY]["taken"]:
        names.append(EXIT_KEY)
    return names


def room_state_summary(state: GameState) -> list[str]:
    cabinet_state = state.object_states["steel cabinet"]
    door_state = state.object_states["exit door"]
    summary = [
        "Rain drums against the high windows of the security office.",
        f"Mara Voss is present and {'trusts you enough to speak plainly' if state.conversation_flags['mara_trust'] else 'still measures your story'}.",
        f"The steel cabinet is {'open' if cabinet_state['open'] else 'closed'} and {'unlocked' if not cabinet_state['locked'] else 'locked'}.",
        f"The exit door is {'unlocked' if not door_state['locked'] else 'locked'}.",
        "Visible objects: " + ", ".join(visible_objects(state)) + ".",
    ]
    return summary


def build_initial_state() -> GameState:
    return GameState(
        current_location=ROOM_NAME,
        object_states={
            "exit door": {"locked": True, "inspected": False},
            "steel cabinet": {"locked": True, "open": False, "inspected": False},
            "desk": {"inspected": False},
            "visitor ledger": {"inspected": False},
            "framed photo": {"inspected": False, "moved": False},
            "coat rack": {"inspected": False, "moved": False},
            EXIT_KEY: {"available": False, "taken": False, "inspected": False},
            "mara": {"inspected": False},
        },
        conversation_flags={
            "mara_met": False,
            "mara_trust": False,
            "mara_revealed_code": False,
        },
        puzzle_flags={
            "ledger_alias_learned": False,
            "cabinet_code_known": False,
            "cabinet_opened": False,
            "door_unlocked": False,
        },
    )
