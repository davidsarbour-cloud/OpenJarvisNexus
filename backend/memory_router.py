"""Memory & facts endpoints — read/update facts, add notes, clear sessions.

Extracted from main.py. Self-contained, no shared app state.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from memory import clear_session, list_sessions, load_facts, save_facts

router = APIRouter(tags=["memory"])


class FactsUpdate(BaseModel):
    user_name:   Optional[str]       = None
    full_name:   Optional[str]       = None
    location:    Optional[str]       = None
    projects:    Optional[list[str]] = None
    preferences: Optional[list[str]] = None
    tech_stack:  Optional[list[str]] = None
    goals:       Optional[list[str]] = None
    notes:       Optional[list[str]] = None


@router.get("/v1/memory")
def get_memory():
    return {"facts": load_facts(), "sessions": list_sessions()}


@router.post("/v1/memory/facts")
def update_facts(update: FactsUpdate):
    facts = load_facts()
    if update.user_name   is not None: facts["user_name"]   = update.user_name
    if update.full_name   is not None: facts["full_name"]   = update.full_name
    if update.location    is not None: facts["location"]    = update.location
    if update.projects    is not None: facts["projects"]    = update.projects
    if update.preferences is not None: facts["preferences"] = update.preferences
    if update.tech_stack  is not None: facts["tech_stack"]  = update.tech_stack
    if update.goals       is not None: facts["goals"]       = update.goals
    if update.notes       is not None: facts["notes"]       = update.notes
    save_facts(facts)
    return {"ok": True, "facts": facts}


@router.post("/v1/memory/note")
def add_note(body: dict):
    note = body.get("note", "")
    if not note:
        raise HTTPException(400, "Champ 'note' requis")
    facts = load_facts()
    facts.setdefault("notes", []).append(note)
    save_facts(facts)
    return {"ok": True, "notes": facts["notes"]}


@router.delete("/v1/memory/session/{session_id}")
def clear_session_route(session_id: str):
    clear_session(session_id)
    return {"ok": True, "cleared": session_id}


@router.delete("/v1/memory/facts")
def clear_facts():
    save_facts({
        "user_name": None, "projects": [], "preferences": [],
        "notes": [], "updated_at": None,
    })
    return {"ok": True}
