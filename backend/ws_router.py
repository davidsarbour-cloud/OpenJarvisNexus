"""
Nexus9 — WebSocket Events Router (Phase 7)

Hub pub/sub in-memory pour pousser des événements vers tous les clients
connectés au RightPanel du Command Center.

Endpoints:
    WS  /ws/events            — connexion long-lived, recevoir les events
    GET /v1/events/recent     — récupère les N derniers événements (replay)
    POST /v1/events/publish   — publier un événement (admin/test)

Pas de Redis requis : tout est en mémoire pour une seule instance backend.
À scaler horizontalement, remplacer le hub par Redis pub/sub.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import Any, Deque

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

router = APIRouter(tags=["events"])

# ─────────────────────────────────────────────────────────
# Hub in-memory
# ─────────────────────────────────────────────────────────
class EventHub:
    """Petit pub/sub thread-safe asyncio pour broadcaster aux WebSockets."""

    def __init__(self, history_size: int = 200) -> None:
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._history: Deque[dict[str, Any]] = deque(maxlen=history_size)
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=128)
        async with self._lock:
            self._subscribers.add(q)
        return q

    async def unsubscribe(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        async with self._lock:
            self._subscribers.discard(q)

    async def publish(self, event: dict[str, Any]) -> int:
        """Broadcast à tous les subs. Retourne le nombre de subs notifiés."""
        # Enrichit le payload
        event.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%S"))
        event.setdefault("level", "info")
        event.setdefault("source", "NEXUS")
        async with self._lock:
            self._history.append(event)
            subs = list(self._subscribers)
        delivered = 0
        for q in subs:
            try:
                q.put_nowait(event)
                delivered += 1
            except asyncio.QueueFull:
                # Sub lent — on jette pour ne pas bloquer
                pass
        return delivered

    def history(self, n: int | None = None) -> list[dict[str, Any]]:
        items = list(self._history)
        return items[-n:] if n else items

    @property
    def sub_count(self) -> int:
        return len(self._subscribers)


hub = EventHub()


# Seed events au démarrage pour que les nouveaux clients voient toujours quelque chose
_BOOTSTRAP_EVENTS: list[dict[str, Any]] = [
    {"level": "info",  "source": "NEXUS9", "msg": "WebSocket hub online"},
    {"level": "info",  "source": "JARVIS", "msg": "orchestrator ready"},
]


async def _seed_history() -> None:
    """Pré-remplit l'historique pour que le replay au connect ait du contenu."""
    for e in _BOOTSTRAP_EVENTS:
        await hub.publish(dict(e))


# Tente de seed dès l'import (FastAPI mainloop déjà actif normalement)
try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(_seed_history())
except RuntimeError:
    # Pas d'event loop encore — sera fait au premier publish
    pass


# ─────────────────────────────────────────────────────────
# REST helpers
# ─────────────────────────────────────────────────────────
class EventIn(BaseModel):
    level: str = "info"     # "info" | "warn" | "alert"
    source: str = "NEXUS"
    msg: str


@router.get("/v1/events/recent")
async def events_recent(limit: int = 50):
    """Renvoie les N derniers événements (utile au refresh / debug)."""
    return {"events": hub.history(limit), "subscribers": hub.sub_count}


@router.post("/v1/events/publish")
async def events_publish(event: EventIn):
    """Publie un événement dans le hub. Tous les WS connectés le recevront."""
    delivered = await hub.publish(event.model_dump())
    return {"ok": True, "delivered": delivered, "subscribers": hub.sub_count}


# ─────────────────────────────────────────────────────────
# WebSocket endpoint
# ─────────────────────────────────────────────────────────
@router.websocket("/ws/events")
async def ws_events(ws: WebSocket) -> None:
    """
    Connexion WebSocket long-lived. Au connect:
      1. Envoie 'hello' + replay des derniers événements (history)
      2. Tient la socket ouverte, push chaque nouvel event reçu via le hub
      3. Heartbeat ping toutes les 30s
    """
    await ws.accept()
    q = await hub.subscribe()

    try:
        # 1) Hello + replay
        await ws.send_json({
            "type": "hello",
            "subscribers": hub.sub_count,
            "history": hub.history(20),
        })

        # 2) Boucle event + heartbeat
        async def pump_events() -> None:
            while True:
                event = await q.get()
                await ws.send_json({"type": "event", "data": event})

        async def heartbeat() -> None:
            while True:
                await asyncio.sleep(30)
                await ws.send_json({"type": "ping", "ts": time.time()})

        events_task = asyncio.create_task(pump_events())
        beat_task = asyncio.create_task(heartbeat())
        # On attend qu'une des deux échoue (ou le client disconnect)
        done, pending = await asyncio.wait(
            {events_task, beat_task},
            return_when=asyncio.FIRST_EXCEPTION,
        )
        for t in pending:
            t.cancel()

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_json({"type": "error", "msg": f"{type(e).__name__}: {e}"})
        except Exception:
            pass
    finally:
        await hub.unsubscribe(q)


# ─────────────────────────────────────────────────────────
# Public helper for other modules to publish events
# ─────────────────────────────────────────────────────────
async def emit(level: str, source: str, msg: str, **extra: Any) -> None:
    """Helper pour le reste du backend : `await emit('warn', 'FORGE', 'queue full')`."""
    payload = {"level": level, "source": source, "msg": msg, **extra}
    await hub.publish(payload)


def emit_sync(level: str, source: str, msg: str, **extra: Any) -> None:
    """Variante non-async (best effort, fire-and-forget)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(emit(level, source, msg, **extra))
    except RuntimeError:
        pass
