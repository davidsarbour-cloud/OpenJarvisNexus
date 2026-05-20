# agent_logger.py — Dashboard logs temps réel
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import asyncio, json
from datetime import datetime
import uvicorn

app = FastAPI()
connected_clients = []

# ── Log une action agent ──
async def log_agent(agent_name: str, action: str, details: str, level="INFO"):
    entry = {
        "time":    datetime.now().strftime("%H:%M:%S"),
        "agent":   agent_name,
        "action":  action,
        "details": details,
        "level":   level
    }
    # Envoyer à tous les clients connectés
    for client in connected_clients[:]:
        try:
            await client.send_text(json.dumps(entry))
        except:
            connected_clients.remove(client)

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            await asyncio.sleep(1)
    except:
        connected_clients.remove(websocket)

@app.get("/logs-dashboard", response_class=HTMLResponse)
async def dashboard():
    return """
<!DOCTYPE html>
<html>
<head>
<title>Agent Logs — NexusX9</title>
<style>
  body { background:#050810; color:#00ffaa; font-family:monospace; padding:20px; }
  h1 { color:#00c8ff; letter-spacing:4px; }
  #logs { height:80vh; overflow-y:auto; border:1px solid #0a2040; padding:10px; }
  .log { margin:3px 0; padding:4px 8px; border-radius:4px; font-size:13px; }
  .INFO    { color:#00ffaa; }
  .WARNING { color:#ffd200; }
  .ERROR   { color:#ff2d55; background:rgba(255,45,85,0.1); }
  .SUCCESS { color:#00c8ff; }
  .time    { color:#3d607f; margin-right:10px; }
  .agent   { color:#ffd200; font-weight:bold; margin-right:8px; }
</style>
</head>
<body>
<h1>⬡ NEXUSX9 — AGENT LOGS</h1>
<div id="logs"></div>
<script>
  const ws = new WebSocket('ws://localhost:8001/ws/logs');
  ws.onmessage = (e) => {
    const d = JSON.parse(e.data);
    const div = document.createElement('div');
    div.className = 'log ' + d.level;
    div.innerHTML = `<span class="time">${d.time}</span>
                     <span class="agent">[${d.agent}]</span>
                     <strong>${d.action}</strong> — ${d.details}`;
    document.getElementById('logs').appendChild(div);
    div.scrollIntoView();
  };
</script>
</body>
</html>
"""

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)