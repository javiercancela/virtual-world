# Virtual World - Implementation Specification

## Project Overview

A Python-based game engine that allows users to interact with LLM-powered characters in configurable worlds. Characters have distinct personalities, memories, and can interact autonomously with each other and the environment.

## Key Requirements

- **Python 3.12** based implementation
- **Text-only interface** (initially)
- **Configurable LLM providers** (OpenAI, Anthropic, Gemini, Ollama for local models)
- **Persistent state** using SQLite
- **Autonomous character interactions**
- **Tool-based actions** for characters
- **Perception-based knowledge** (characters only know what they can see/hear or are told)
- **YAML/JSON configuration** for worlds and characters

## Project Structure

```
llm-game-engine/
├── core/
│   ├── __init__.py
│   ├── engine.py           # Main game loop & orchestration
│   ├── world.py            # World state management
│   ├── location.py         # Location/room management
│   ├── character.py        # Character base class
│   ├── player.py           # Player interface
│   └── events.py           # Event system
├── llm/
│   ├── __init__.py
│   ├── base.py             # Abstract LLM interface
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── openai.py       # OpenAI adapter
│   │   ├── anthropic.py    # Anthropic adapter
│   │   └── ollama.py       # Local models via Ollama
│   └── factory.py          # Provider factory
├── memory/
│   ├── __init__.py
│   ├── character_memory.py # Individual character memories
│   ├── event_log.py        # Global event tracking
│   └── perception.py       # What characters can perceive
├── actions/
│   ├── __init__.py
│   ├── base.py             # Action interface
│   ├── movement.py         # Character movement
│   ├── interaction.py      # Object/character interactions
│   ├── inventory.py        # Item management
│   └── validators.py       # Rule enforcement
├── tools/
│   ├── __init__.py
│   ├── base.py             # Tool interface for LLMs
│   ├── perception_tools.py # Look, examine, listen
│   ├── action_tools.py     # Move, take, use, talk
│   └── query_tools.py      # Check inventory, recall memory
├── persistence/
│   ├── __init__.py
│   ├── sqlite_store.py     # SQLite backend
│   └── migrations.py       # Schema versioning
├── config/
│   ├── __init__.py
│   ├── loader.py           # Configuration loading
│   ├── schemas/
│   │   ├── world_schema.json
│   │   └── character_schema.json
│   └── examples/
│       └── simple_world.yaml
├── utils/
│   ├── __init__.py
│   ├── prompts.py          # Prompt engineering
│   └── scheduler.py        # Character action scheduling
├── tests/
│   └── ...
├── requirements.txt
├── setup.py
└── README.md
```

## Implementation Order

1. **Phase 1: Core Infrastructure**
   - Set up project structure
   - Implement base classes (World, Location, Character, Item)
   - Create event system
   - Basic persistence with SQLite

2. **Phase 2: LLM Integration**
   - Implement LLM provider interface
   - Create OpenAI adapter
   - Add tool system for character actions
   - Basic prompt engineering

3. **Phase 3: Game Mechanics**
   - Movement system
   - Inventory management
   - Character interactions
   - Perception system

4. **Phase 4: Memory & Intelligence**
   - Character memory implementation
   - Event perception logic
   - Autonomous character behavior
   - Goal-driven actions

5. **Phase 5: Player Interface**
   - Command parsing
   - Natural language understanding
   - Game state display
   - Save/load functionality

6. **Phase 6: Advanced Features**
   - Additional LLM providers (Anthropic, Ollama)
   - Complex world rules
   - Character relationships
   - Narrative generation

## Testing Strategy

- Unit tests for core components
- Integration tests for LLM interactions
- Mock LLM provider for testing
- Example scenarios for validation

## Example Usage

```python
# main.py
import asyncio
from core.engine import GameEngine

async def main():
    engine = GameEngine("config/examples/simple_world.yaml")
    await engine.run()

if __name__ == "__main__":
    asyncio.run(main())
```

## Notes for Implementation

1. Use `asyncio` throughout for better performance with LLM calls
2. Implement proper error handling for LLM failures
3. Add retry logic for API calls
4. Use environment variables for API keys
5. Consider rate limiting for API calls
6. Implement proper logging throughout
7. Make the system extensible for future additions (combat, magic, etc.)

## Next Steps

1. Create the project structure
2. Implement core classes with basic functionality
3. Add LLM integration starting with OpenAI
4. Build a simple test world
5. Iterate based on testing