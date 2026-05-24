"""
scrapers/keyword_engine.py
NLP noun extraction + Ollama-powered product keyword expansion.
Extracts product keywords from raw text; expands with LLM when available.
"""
from __future__ import annotations

import json
import re
import urllib.request as _ur
from typing import Sequence

# ── Simple noun extraction (no spaCy/NLTK dependency) ────────────────────────

# Common English stop words to exclude from extracted nouns
_STOP_WORDS: frozenset[str] = frozenset({
    "a", "an", "the", "this", "that", "these", "those", "it", "its",
    "i", "you", "he", "she", "we", "they", "me", "him", "her", "us", "them",
    "is", "are", "was", "were", "be", "been", "being", "am",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "used",
    "get", "got", "make", "made", "take", "took", "know", "knew",
    "here", "there", "when", "where", "which", "who", "what", "how", "why",
    "just", "also", "very", "really", "quite", "so", "too", "even", "still",
    "only", "also", "as", "at", "by", "for", "from", "in", "into", "of",
    "on", "or", "to", "up", "with", "not", "no", "but", "and", "if",
    "my", "your", "his", "her", "our", "their", "any", "all", "some",
    "new", "good", "great", "best", "more", "most", "own", "same",
    "like", "need", "want", "buy", "sell", "use", "look", "go", "come",
    "thing", "way", "time", "year", "day", "people", "man", "woman",
    "one", "two", "three", "four", "five", "first", "last", "next",
    "post", "comment", "subreddit", "reddit", "tiktok", "etsy", "amazon",
    # Common verbs/adjectives that aren't product names
    "love", "hate", "think", "feel", "found", "find", "found", "tried",
    "really", "perfect", "amazing", "awesome", "great", "nice", "cool",
    "seen", "seen", "show", "says", "said", "told", "telling", "tell",
    "work", "works", "working", "worked", "using", "used", "using",
    "product", "products", "item", "items", "stuff", "things", "something",
    "little", "small", "large", "huge", "tiny", "simple", "easy", "hard",
    "price", "cheap", "expensive", "worth", "money", "cost", "costs",
    "actually", "basically", "literally", "honestly", "definitely",
})

# Product-relevant adjective starters (keep these with their nouns)
_PRODUCT_PREFIXES: frozenset[str] = frozenset({
    "cable", "desk", "wall", "magnetic", "wireless", "wooden", "bamboo",
    "aluminum", "silicone", "leather", "portable", "foldable", "adjustable",
    "custom", "handmade", "personalized", "minimalist", "ergonomic",
    "smart", "led", "usb", "solar", "rechargeable", "waterproof",
})


def extract_nouns(text: str, min_length: int = 4) -> list[str]:
    """
    Extract candidate product keywords from text using heuristic rules:
    - Capitalized words not at sentence start
    - Multi-word noun phrases (adj + noun pairs)
    - Removes stop words and short tokens

    Returns deduplicated, lowercased list sorted by frequency.
    """
    if not text:
        return []

    text_clean = re.sub(r'https?://\S+|@\w+|#\w+', ' ', text)
    words = re.findall(r'\b[a-zA-Z][a-zA-Z\-]{2,}\b', text_clean)

    # Count lowercased tokens, excluding stop words
    freq: dict[str, int] = {}
    for w in words:
        lw = w.lower()
        if lw not in _STOP_WORDS and len(lw) >= min_length:
            freq[lw] = freq.get(lw, 0) + 1

    # Also extract 2-word noun phrases where first word is a product prefix
    phrases: dict[str, int] = {}
    tokens = [w.lower() for w in words]
    for i in range(len(tokens) - 1):
        t1, t2 = tokens[i], tokens[i + 1]
        if (
            t1 in _PRODUCT_PREFIXES
            and t2 not in _STOP_WORDS
            and len(t2) >= 3
        ):
            phrase = f"{t1} {t2}"
            phrases[phrase] = phrases.get(phrase, 0) + 1

    # Merge single words + phrases, sort by frequency
    combined = {**freq, **phrases}
    sorted_kws = sorted(combined, key=lambda k: -combined[k])
    return sorted_kws[:30]


# ── Ollama keyword expansion ──────────────────────────────────────────────────

def expand_keywords_ollama(
    seed_keywords: list[str],
    model: str = "qwen3:14b",
    ollama_url: str = "http://localhost:11434",
    max_keywords: int = 15,
    timeout: int = 15,
) -> list[str]:
    """
    Use Ollama to expand a list of seed keywords into related product ideas.
    Synchronous (run in thread if needed from async context).

    Returns list of new keyword strings, empty list on error.
    """
    if not seed_keywords:
        return []

    seed_str = ", ".join(seed_keywords[:10])
    prompt = (
        f"You are a product research assistant.\n"
        f"Given these trending keywords: [{seed_str}]\n\n"
        f"Generate {max_keywords} specific product keyword ideas that a dropshipper "
        f"or Etsy seller could use to find winning products.\n"
        f"Rules:\n"
        f"- Return ONLY a JSON array of strings, no explanation\n"
        f"- Each keyword: 2-4 words, specific product name\n"
        f"- Mix: accessories, organizers, gadgets, gifts, home items\n"
        f"- Example: [\"cable management box\", \"magnetic cable clips\", ...]\n\n"
        f"JSON array:"
    )

    payload = json.dumps({
        "model":   model,
        "prompt":  prompt,
        "stream":  False,
        "options": {"temperature": 0.6, "num_predict": 400},
    }).encode()

    try:
        req = _ur.Request(
            f"{ollama_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with _ur.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        raw = data.get("response", "").strip()

        # Extract JSON array from response (may have preamble/postamble)
        m = re.search(r'\[.*?\]', raw, re.DOTALL)
        if not m:
            return []
        kws = json.loads(m.group(0))
        if isinstance(kws, list):
            return [str(k).strip() for k in kws if k][:max_keywords]
    except Exception as e:
        print(f"[keyword_engine] Ollama unavailable: {e}")
    return []


# ── Combined pipeline ─────────────────────────────────────────────────────────

def extract_and_expand(
    texts: Sequence[str],
    ollama_url: str = "http://localhost:11434",
    model: str = "qwen3:14b",
    use_ollama: bool = True,
) -> dict:
    """
    Full keyword pipeline:
    1. Extract nouns from raw texts
    2. Optionally expand via Ollama

    Returns
    -------
    {
        "extracted":  list[str],   # raw NLP extraction
        "expanded":   list[str],   # Ollama expansion (empty if disabled/error)
        "combined":   list[str],   # deduped union, extracted first
    }
    """
    combined_text = " ".join(texts)
    extracted = extract_nouns(combined_text)

    expanded: list[str] = []
    if use_ollama and extracted:
        # Take top 5 most frequent as seeds
        expanded = expand_keywords_ollama(
            extracted[:5], model=model, ollama_url=ollama_url
        )

    # Dedup union
    seen: set[str] = set()
    result: list[str] = []
    for kw in extracted + expanded:
        if kw not in seen:
            seen.add(kw)
            result.append(kw)

    return {
        "extracted": extracted,
        "expanded":  expanded,
        "combined":  result[:40],
    }
