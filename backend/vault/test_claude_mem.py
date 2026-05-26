import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from vault.memory_manager import save_to_claude_mem


async def test():
    print("[TEST] Testing Claude-Mem integration...")

    result = await save_to_claude_mem(
        memory_type="test",
        content="JARVIS test memory from Nexus9 integration",
        metadata={"system": "nexus9", "version": "0.8"}
    )

    if result:
        print(f"✓ Saved to Claude-Mem: {result}")
    else:
        print("✗ Failed to save (server may not be running)")

if __name__ == "__main__":
    asyncio.run(test())
