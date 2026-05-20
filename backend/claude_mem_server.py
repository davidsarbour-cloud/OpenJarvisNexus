"""
Claude-Mem MCP Server Bridge
Expose claude-mem as MCP service for JARVIS + all agents
"""
import asyncio
import subprocess
import json
from pathlib import Path

CLAUDE_MEM_PATH = Path(__file__).parent / "claude-mem"
PORT = 8084

async def start_claude_mem_service():
    """Start claude-mem as Node.js service"""
    print(f"[CLAUDE-MEM] Starting on port {PORT}...")
    
    # Run claude-mem via Node
    proc = subprocess.Popen(
        ["node", str(CLAUDE_MEM_PATH / "dist" / "npx-cli" / "index.js")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    print(f"[CLAUDE-MEM] Service running (PID: {proc.pid})")
    return proc

if __name__ == "__main__":
    proc = asyncio.run(start_claude_mem_service())
    proc.wait()
