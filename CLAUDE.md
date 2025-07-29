# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based game engine for creating LLM-powered character interactions in virtual worlds. The project is currently in the initial planning phase with only a specification document.

## Key Architecture

Based on the README.md specification, this project follows a modular architecture:

- **core/**: Main game loop, world state, characters, and events
- **llm/**: LLM provider abstractions with adapters for OpenAI, Anthropic, and Ollama
- **memory/**: Character memory systems and perception handling
- **actions/**: Character action system with movement, interaction, and inventory
- **tools/**: LLM function calling tools for character capabilities
- **persistence/**: SQLite-based data storage
- **config/**: YAML/JSON configuration system for worlds and characters

## Technical Requirements

- **Python 3.12** is the target version
- **Async/await** pattern throughout for LLM call performance
- **SQLite** for persistent state storage
- **YAML/JSON** for configuration files
- **Text-only interface** initially (no GUI)

## Implementation Phases

The project is designed to be built in 6 phases:
1. Core Infrastructure (base classes, events, persistence)
2. LLM Integration (providers, tools, prompts)
3. Game Mechanics (movement, inventory, interactions)
4. Memory & Intelligence (character memory, perception, autonomy)
5. Player Interface (command parsing, natural language)
6. Advanced Features (multiple providers, complex rules, relationships)

## Development Notes

- Use environment variables for API keys
- Implement proper error handling and retry logic for LLM calls
- Add rate limiting for API calls
- Use comprehensive logging throughout
- Design for extensibility (future combat, magic systems, etc.)
- Mock LLM providers should be used for testing

## Testing Strategy

- Unit tests for core components
- Integration tests for LLM interactions
- Mock LLM provider for testing without API calls
- Example scenarios for validation

## Current State

The repository currently contains only specification documents. Implementation has not yet begun, so there are no build commands, test commands, or executable code yet.