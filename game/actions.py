from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .router import ValidatedAction
from .state import GameState
from .world import CABINET_CODE, EXIT_KEY, HELP_TEXT, NPC_NAME, VISITOR_ALIAS, room_state_summary


@dataclass(slots=True)
class NarrationContext:
    action_name: str
    deterministic_text: str
    facts: list[str]
    forbidden_terms: list[str] = field(default_factory=list)


@dataclass(slots=True)
class NPCContext:
    phase: str
    deterministic_text: str
    allowed_facts: list[str]
    forbidden_terms: list[str] = field(default_factory=list)
    recent_player_line: str | None = None


@dataclass(slots=True)
class ActionOutcome:
    success: bool
    response_mode: str
    deterministic_text: str
    state_transition: dict[str, Any]
    error: str | None = None
    narrator_context: NarrationContext | None = None
    npc_context: NPCContext | None = None


UNKNOWN_TEXT = "That does not resolve into a safe action. Rephrase it with a clear object or request."


REVEAL_CLUE = f"Cabinet code: {CABINET_CODE}"
LEDGER_CLUE = f"The last suspicious visitor signed in as {VISITOR_ALIAS}."


class ActionEngine:
    def apply(self, state: GameState, action: ValidatedAction) -> ActionOutcome:
        if state.game_over:
            return ActionOutcome(
                success=False,
                response_mode="plain",
                deterministic_text="The office is already behind you. Start a new session to play again.",
                state_transition={"events": ["game_over_noop"]},
            )

        handlers = {
            "help": self._handle_help,
            "inventory": self._handle_inventory,
            "ask_state": self._handle_ask_state,
            "inspect": self._handle_inspect,
            "take": self._handle_take,
            "move": self._handle_move,
            "use": self._handle_use,
            "talk": self._handle_talk,
            "unknown": self._handle_unknown,
        }
        return handlers[action.intent](state, action)

    def _handle_help(self, state: GameState, action: ValidatedAction) -> ActionOutcome:
        return ActionOutcome(True, "plain", HELP_TEXT, {"events": ["help_shown"]})

    def _handle_inventory(self, state: GameState, action: ValidatedAction) -> ActionOutcome:
        if state.inventory:
            text = "Inventory: " + ", ".join(state.inventory) + "."
        else:
            text = "Inventory: empty."
        return ActionOutcome(True, "plain", text, {"events": ["inventory_checked"]})

    def _handle_ask_state(self, state: GameState, action: ValidatedAction) -> ActionOutcome:
        facts = room_state_summary(state)
        fallback_text = " ".join(facts)
        return ActionOutcome(
            True,
            "narrator",
            fallback_text,
            {"events": ["room_state_described"]},
            narrator_context=NarrationContext(
                action_name="ask_state",
                deterministic_text=fallback_text,
                facts=facts,
                forbidden_terms=self._secret_terms(state),
            ),
        )

    def _handle_unknown(self, state: GameState, action: ValidatedAction) -> ActionOutcome:
        return ActionOutcome(False, "plain", UNKNOWN_TEXT, {"events": ["unknown_action"]}, error="unknown_action")

    def _handle_inspect(self, state: GameState, action: ValidatedAction) -> ActionOutcome:
        target = action.target
        assert target is not None
        state.object_states[target]["inspected"] = True

        if target == "exit door":
            facts = [
                "The reinforced exit door is shut tight.",
                "Its lock is mechanical, not electronic.",
                "You need a physical key, not a keypad code, to leave.",
            ]
            return self._narrated("inspect_exit_door", facts, state, ["The door stays locked."])

        if target == "steel cabinet":
            cabinet = state.object_states["steel cabinet"]
            if cabinet["open"]:
                facts = [
                    "The steel cabinet stands open.",
                    "A single brass key rests inside." if not state.object_states[EXIT_KEY]["taken"] else "The key compartment is empty now.",
                ]
            elif cabinet["locked"]:
                facts = [
                    "The steel cabinet is locked.",
                    "A three-digit keypad is built into the handle.",
                    "Mara glances at it every time the room falls quiet.",
                ]
            else:
                facts = [
                    "The keypad has been accepted and the cabinet door is loose.",
                    "A brass key is visible inside.",
                ]
            return self._narrated("inspect_cabinet", facts, state, ["The cabinet waits in front of you."])

        if target == "desk":
            facts = [
                "The desk is crowded with incident forms, a dead flashlight, and a visitor ledger.",
                "The ledger is already open to the latest page.",
                "Someone expected you to notice the entries.",
            ]
            return self._narrated("inspect_desk", facts, state, ["The desk points your attention toward the ledger."])

        if target == "visitor ledger":
            learned = not state.puzzle_flags["ledger_alias_learned"]
            state.puzzle_flags["ledger_alias_learned"] = True
            state.add_clue(LEDGER_CLUE)
            facts = [
                "The final entry is underlined twice in red pencil.",
                f"The suspicious visitor signed in as {VISITOR_ALIAS}.",
                "Mara would probably care whether you caught that name.",
            ]
            events = ["ledger_inspected"]
            if learned:
                events.append("ledger_alias_learned")
            return ActionOutcome(
                True,
                "narrator",
                "The ledger gives you the name Mara wanted someone to notice: Silas Vale.",
                {"events": events, "clues_added": [LEDGER_CLUE] if learned else []},
                narrator_context=NarrationContext(
                    action_name="inspect_ledger",
                    deterministic_text="The ledger gives you the name Mara wanted someone to notice: Silas Vale.",
                    facts=facts,
                    forbidden_terms=self._secret_terms(state),
                ),
            )

        if target == "framed photo":
            facts = [
                "The photo shows Mara with a commendation ribbon pinned to her jacket.",
                "The engraved plaque reads: Attention kept us alive.",
                "It feels less like sentiment and more like a test.",
            ]
            return self._narrated("inspect_photo", facts, state, ["The photo suggests Mara respects careful observation."])

        if target == "coat rack":
            facts = [
                "Mara's raincoat drips onto the tiles.",
                "A leather key clip hangs empty from the sleeve seam.",
                "Whatever key belongs there is not on the rack.",
            ]
            return self._narrated("inspect_coat_rack", facts, state, ["The empty clip suggests the important key is stored elsewhere."])

        if target == EXIT_KEY:
            facts = ["The brass key is heavy, old, and tagged EXIT."]
            return self._narrated("inspect_key", facts, state, ["The key is plainly the way out."])

        if target == "mara":
            facts = [
                "Mara Voss watches every move with controlled impatience.",
                "She looks tired, suspicious, and unwilling to volunteer the cabinet code.",
            ]
            return self._narrated("inspect_mara", facts, state, ["Mara is waiting for proof that you have paid attention."])

        return self._handle_unknown(state, action)

    def _handle_take(self, state: GameState, action: ValidatedAction) -> ActionOutcome:
        target = action.target
        assert target is not None
        if target != EXIT_KEY:
            return ActionOutcome(
                False,
                "plain",
                f"You cannot take the {target}.",
                {"events": ["take_rejected"], "target": target},
                error="take_rejected",
            )

        key_state = state.object_states[EXIT_KEY]
        if not key_state["available"]:
            return ActionOutcome(
                False,
                "plain",
                "There is no key within reach yet.",
                {"events": ["take_missing_key"]},
                error="take_missing_key",
            )
        if key_state["taken"]:
            return ActionOutcome(
                False,
                "plain",
                "You already have the brass key.",
                {"events": ["take_duplicate_key"]},
                error="take_duplicate_key",
            )

        key_state["taken"] = True
        state.add_item(EXIT_KEY)
        return ActionOutcome(
            True,
            "narrator",
            "You take the brass key from the cabinet.",
            {"events": ["key_taken"], "inventory_added": [EXIT_KEY]},
            narrator_context=NarrationContext(
                action_name="take_key",
                deterministic_text="You take the brass key from the cabinet.",
                facts=[
                    "The brass key comes free with a metallic scrape.",
                    "Its EXIT tag confirms it belongs to the door.",
                ],
            ),
        )

    def _handle_move(self, state: GameState, action: ValidatedAction) -> ActionOutcome:
        target = action.target
        assert target is not None
        if target not in {"framed photo", "coat rack"}:
            return ActionOutcome(
                False,
                "plain",
                f"You shift the {target}, but it changes nothing useful.",
                {"events": ["move_no_effect"], "target": target},
            )

        state.object_states[target]["moved"] = True
        if target == "framed photo":
            facts = [
                "You straighten the framed photo and expose a dust-free rectangle behind it.",
                "Someone has been handling it recently, but there is no hidden switch.",
                "The gesture reinforces the room's theme: notice details, do not expect tricks.",
            ]
            return self._narrated("move_photo", facts, state, ["The photo hides no mechanism, only a hint about Mara's standards."])

        facts = [
            "You drag the coat rack aside.",
            "Only wet tile and a trail of grit wait underneath.",
            "No spare key was tucked there.",
        ]
        return self._narrated("move_coat_rack", facts, state, ["The floor under the coat rack is empty."])

    def _handle_use(self, state: GameState, action: ValidatedAction) -> ActionOutcome:
        target = action.target
        secondary = action.secondary_target
        assert target is not None

        if target == "steel cabinet":
            if state.object_states["steel cabinet"]["open"]:
                return ActionOutcome(
                    False,
                    "plain",
                    "The cabinet is already open.",
                    {"events": ["cabinet_already_open"]},
                )
            if not state.puzzle_flags["cabinet_code_known"]:
                return ActionOutcome(
                    False,
                    "plain",
                    "The keypad waits for a three-digit code you do not have yet.",
                    {"events": ["cabinet_use_blocked"]},
                    error="cabinet_code_unknown",
                )
            state.object_states["steel cabinet"]["locked"] = False
            state.object_states["steel cabinet"]["open"] = True
            state.object_states[EXIT_KEY]["available"] = True
            state.puzzle_flags["cabinet_opened"] = True
            facts = [
                f"You enter {CABINET_CODE} and the keypad clicks green.",
                "The steel cabinet swings open.",
                "Inside rests a brass key tagged EXIT.",
            ]
            return ActionOutcome(
                True,
                "narrator",
                "The cabinet unlocks and opens, revealing a brass key inside.",
                {
                    "events": ["cabinet_unlocked", "cabinet_opened"],
                    "object_updates": {"steel cabinet": {"locked": False, "open": True}, EXIT_KEY: {"available": True}},
                },
                narrator_context=NarrationContext(
                    action_name="use_cabinet",
                    deterministic_text="The cabinet unlocks and opens, revealing a brass key inside.",
                    facts=facts,
                    forbidden_terms=[],
                ),
            )

        door_requested = target == "exit door" or secondary == "exit door"
        if door_requested:
            if EXIT_KEY not in state.inventory and not (target == EXIT_KEY and state.object_states[EXIT_KEY]["taken"]):
                return ActionOutcome(
                    False,
                    "plain",
                    "The door needs a brass key, and you do not have it yet.",
                    {"events": ["door_use_blocked"]},
                    error="missing_key",
                )
            state.object_states["exit door"]["locked"] = False
            state.puzzle_flags["door_unlocked"] = True
            state.escaped = True
            state.game_over = True
            facts = [
                "The brass key turns with a heavy clunk.",
                "The exit door opens onto the rain-dark corridor.",
                f"Mara gives a single tight nod as you leave the {state.current_location.lower()}.",
            ]
            return ActionOutcome(
                True,
                "narrator",
                "The key turns, the exit door opens, and you step free.",
                {
                    "events": ["door_unlocked", "escaped"],
                    "object_updates": {"exit door": {"locked": False}},
                    "escaped": True,
                },
                narrator_context=NarrationContext(
                    action_name="use_exit_door",
                    deterministic_text="The key turns, the exit door opens, and you step free.",
                    facts=facts,
                ),
            )

        return ActionOutcome(
            False,
            "plain",
            f"Using the {target} that way does nothing useful.",
            {"events": ["use_no_effect"], "target": target, "secondary_target": secondary},
            error="use_no_effect",
        )

    def _handle_talk(self, state: GameState, action: ValidatedAction) -> ActionOutcome:
        utterance = (action.utterance or "").strip()
        lowered = utterance.lower()
        state.conversation_flags["mara_met"] = True

        if state.conversation_flags["mara_trust"]:
            return ActionOutcome(
                True,
                "npc",
                f"Mara reminds you that the cabinet code is {CABINET_CODE} and the key is inside.",
                {"events": ["mara_followup_reply"]},
                npc_context=NPCContext(
                    phase="trusted",
                    deterministic_text=f"Mara folds her arms. 'I already gave you what you need. The cabinet code is {CABINET_CODE}. The key is inside.'",
                    allowed_facts=[
                        f"The cabinet code is {CABINET_CODE}.",
                        "The brass exit key is inside the steel cabinet.",
                        "Mara can speak tersely and stay in character.",
                    ],
                    recent_player_line=utterance,
                ),
            )

        if state.puzzle_flags["ledger_alias_learned"] and self._mentions_alias(lowered):
            state.conversation_flags["mara_trust"] = True
            state.conversation_flags["mara_revealed_code"] = True
            state.puzzle_flags["cabinet_code_known"] = True
            state.add_clue(REVEAL_CLUE)
            return ActionOutcome(
                True,
                "npc",
                f"Mara trusts you now and reveals the cabinet code: {CABINET_CODE}.",
                {"events": ["mara_trust_gained", "cabinet_code_revealed"], "clues_added": [REVEAL_CLUE]},
                npc_context=NPCContext(
                    phase="reveal_code",
                    deterministic_text=f"Mara studies you for a beat, then nods. 'Good. You were paying attention. The cabinet code is {CABINET_CODE}. The key you want is inside.'",
                    allowed_facts=[
                        f"The suspicious visitor alias was {VISITOR_ALIAS}.",
                        f"The cabinet code is {CABINET_CODE}.",
                        "The brass exit key is inside the steel cabinet.",
                        "Mara reveals the code because the player proved they noticed the ledger entry.",
                    ],
                    recent_player_line=utterance,
                ),
            )

        phase = "guarded"
        deterministic_text = (
            "Mara watches you without blinking. 'If you want me to trust you, tell me the name that mattered in the visitor ledger.'"
        )
        allowed_facts = [
            "Mara is suspicious and testing whether the player inspected the visitor ledger carefully.",
            "She must not reveal the cabinet code yet.",
            "She may hint that a specific name in the ledger matters, but she must not say the name.",
        ]
        forbidden_terms = [CABINET_CODE, "brass key", "inside the cabinet"]
        if not utterance:
            deterministic_text = "Mara lifts her chin. 'Ask a real question. Start with the ledger if you want answers.'"
            phase = "nudge"
        elif any(token in lowered for token in ["who are you", "what happened", "why are we locked", "hello"]):
            deterministic_text = "Mara exhales slowly. 'Later. First prove you noticed what was written in the ledger.'"
            phase = "nudge"

        return ActionOutcome(
            True,
            "npc",
            deterministic_text,
            {"events": ["mara_guarded_reply"]},
            npc_context=NPCContext(
                phase=phase,
                deterministic_text=deterministic_text,
                allowed_facts=allowed_facts,
                forbidden_terms=forbidden_terms,
                recent_player_line=utterance,
            ),
        )

    def _mentions_alias(self, lowered_text: str) -> bool:
        return any(token in lowered_text for token in ["silas", "vale"])

    def _narrated(self, action_name: str, facts: list[str], state: GameState, fallback_sentences: list[str]) -> ActionOutcome:
        fallback_text = " ".join(fallback_sentences)
        return ActionOutcome(
            True,
            "narrator",
            fallback_text,
            {"events": [action_name]},
            narrator_context=NarrationContext(
                action_name=action_name,
                deterministic_text=fallback_text,
                facts=facts,
                forbidden_terms=self._secret_terms(state),
            ),
        )

    def _secret_terms(self, state: GameState) -> list[str]:
        forbidden: set[str] = set()
        if not state.puzzle_flags["cabinet_code_known"]:
            forbidden.update([CABINET_CODE, "417"])
        if not state.object_states[EXIT_KEY]["available"]:
            forbidden.add("brass key")
        return sorted(forbidden)
