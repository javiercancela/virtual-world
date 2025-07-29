import asyncio
from core.engine import GameEngine

async def main():
    engine = GameEngine("config/examples/simple_world.yaml")
    await engine.run()

if __name__ == "__main__":
    asyncio.run(main())