"""
trend_engine/sentiment.py
Shared intent phrases + scan functions used by all scrapers.
Single source of truth — imported everywhere, defined nowhere else.
"""
from __future__ import annotations

import re
from typing import Sequence


# ── Buyer intent (English + French) ──────────────────────────────────────────

INTENT_PHRASES: list[str] = [
    # English — purchase
    "i need this", "where to buy", "where can i buy", "need this in my life",
    "shut up and take my money", "want this so bad", "i want this",
    "take my money", "anyone know where", "how much does this cost",
    "is this available", "pre-order", "pre order", "add to cart",
    "link in bio", "drop the link", "give me the link", "send me the link",
    "buy link", "purchase link", "anyone selling",
    # English — problem/desire
    "i struggle with", "i hate when", "i always lose", "i keep forgetting",
    "i wish there was", "why doesn't someone make",
    # French — achat
    "je veux ça", "où acheter", "j'ai besoin de ça", "prenez mon argent",
    "combien ça coûte", "c'est dispo", "disponible où",
    "quelqu'un vend ça", "je cherche ça",
    # French — problème/désir
    "j'en ai marre de", "pourquoi personne ne fait", "il manque",
]

# ── TikTok viral hooks ────────────────────────────────────────────────────────

VIRAL_HOOKS: list[str] = [
    "you need this", "wait till the end", "wait for it",
    "this changed my life", "game changer", "this is a game changer",
    "underrated product", "hidden gem", "life hack", "life changing",
    "why didn't i know this sooner", "i can't believe this exists",
    "where has this been all my life", "obsessed with this",
    "must have", "must-have", "can't live without",
    "tiktok made me buy it", "tiktok made me buy",
    "amazon find", "amazon must have", "etsy find",
    "small business check", "small biz", "#smallbusiness",
    "POV you need this", "POV: you need this",
]

# ── STL / 3D printing intent ──────────────────────────────────────────────────

STL_INTENT_PHRASES: list[str] = [
    "stl?", "stl file?", "can you share the file", "share the stl",
    "where's the stl", "where is the stl", "download link",
    "thingiverse?", "makerworld?", "cults?", "printables?",
    "is this printable", "can i print this", "what filament",
    "print settings", "layer height", "infill", "supports needed",
    "i printed this", "just printed", "printed mine",
    "sliced in", "prusa slicer", "bambu studio", "orca slicer",
    "how long to print", "print time",
]


# ── Core scan function ────────────────────────────────────────────────────────

def scan_intent(
    texts: Sequence[str],
    phrases: Sequence[str] | None = None,
    case_sensitive: bool = False,
) -> tuple[int, list[str]]:
    """
    Scan a list of strings for intent phrases.

    Parameters
    ----------
    texts         : list of raw strings (post titles, comments, captions…)
    phrases       : phrase list to use (default: INTENT_PHRASES)
    case_sensitive: default False

    Returns
    -------
    (hit_count, matched_phrases)
        hit_count      — total number of phrase matches across all texts
        matched_phrases— deduplicated list of phrases that matched at least once
    """
    if phrases is None:
        phrases = INTENT_PHRASES

    hits = 0
    found: set[str] = set()

    for raw in texts:
        if not raw:
            continue
        text = raw if case_sensitive else raw.lower()
        for phrase in phrases:
            needle = phrase if case_sensitive else phrase.lower()
            # \b only applies at word-char boundaries.
            # Phrases ending in non-word chars (e.g. "stl?") must skip trailing \b.
            lead_b = r'\b' if needle and (needle[0].isalnum() or needle[0] == '_') else ''
            tail_b = r'\b' if needle and (needle[-1].isalnum() or needle[-1] == '_') else ''
            if re.search(lead_b + re.escape(needle) + tail_b, text):
                hits += 1
                found.add(phrase)

    return hits, sorted(found)


def score_intent(hits: int, total_texts: int) -> float:
    """
    Normalize hit count to 0.0–1.0.
    Uses a soft cap: 10+ hits across 25 texts = near-perfect score.

    Returns 0.0 if total_texts == 0.
    """
    if total_texts <= 0:
        return 0.0
    # density: hits per text
    density = hits / total_texts
    # soft cap at density = 0.4 (10 hits in 25 texts → 1.0)
    return min(density / 0.4, 1.0)


def scan_viral(texts: Sequence[str]) -> tuple[int, list[str]]:
    """Convenience wrapper for VIRAL_HOOKS phrases."""
    return scan_intent(texts, phrases=VIRAL_HOOKS)


def scan_stl(texts: Sequence[str]) -> tuple[int, list[str]]:
    """Convenience wrapper for STL_INTENT_PHRASES."""
    return scan_intent(texts, phrases=STL_INTENT_PHRASES)
