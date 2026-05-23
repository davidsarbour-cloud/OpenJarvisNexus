"""Génère les métadonnées SEO pour les produits via ULTRON (Sonnet) + GWEN (Qwen)."""
from __future__ import annotations
import json, os, re
import httpx

BACKEND_PORT      = int(os.getenv("BACKEND_PORT", 8000))
CLAUDE_GROS_MODEL = os.getenv("CLAUDE_MODEL_GROS", "claude-sonnet-4-6")
OLLAMA_HOST       = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL      = os.getenv("OLLAMA_MODEL", "qwen3:14b")

_CONCEPT_SYSTEM = """You are ULTRON, product strategist for D3Dprintix 3D print shop.
Analyze the product idea and return ONLY valid JSON:
{
  "title": "SEO product title (max 60 chars)",
  "niche": "target niche/audience",
  "style": "visual style description",
  "forge_prompt": "STL generation prompt for Forge Room (organic/mechanical description)",
  "usp": "unique selling proposition",
  "target_audience": "who buys this"
}"""

_META_SYSTEM = """You are ULTRON, SEO specialist for 3D printed products on Etsy/Shopify.
Return ONLY valid JSON:
{
  "title": "Etsy SEO title (max 140 chars, include keywords)",
  "description": "Product description (200-300 words, markdown OK)",
  "tags": ["tag1", "tag2", "... up to 13 tags"],
  "price_usd": 4.99,
  "category": "category name",
  "keywords": ["keyword1", "keyword2"]
}"""


async def _ask_claude(system: str, message: str) -> dict:
    """Appelle ULTRON (Claude Sonnet) via l'endpoint local."""
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"http://localhost:{BACKEND_PORT}/v1/chat/completions",
            json={
                "system": system,
                "message": message,
                "stream": False,
                "model": CLAUDE_GROS_MODEL,
            },
            timeout=30,
        )
        if r.status_code != 200:
            return {}
        d = r.json()
        msg = d.get("choices", [{}])[0].get("message", "")
        text = msg if isinstance(msg, str) else msg.get("content", "")
        m = re.search(r"\{[\s\S]+\}", text)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
        return {}


async def generate_concept(idea: str) -> dict:
    """ULTRON génère le concept produit."""
    result = await _ask_claude(_CONCEPT_SYSTEM, f"Product idea: {idea}")
    if not result:
        return {
            "title": idea[:60],
            "niche": "3D printing",
            "style": "low-poly",
            "forge_prompt": f"{idea} low-poly FDM printable flat base support-free",
            "usp": "Unique 3D printed design",
            "target_audience": "3D printing enthusiasts",
        }
    return result


async def generate_listing_metadata(idea: str, concept: dict, score: int) -> dict:
    """ULTRON génère les métadonnées SEO pour le listing."""
    msg = (
        f"Product: {idea}\n"
        f"Concept: {json.dumps(concept)}\n"
        f"Printability score: {score}/100\n"
        f"Shop: D3Dprintix (Etsy/Shopify 3D print shop)\n"
        f"Generate optimized listing metadata."
    )
    result = await _ask_claude(_META_SYSTEM, msg)
    if not result:
        return {
            "title": f"{idea[:80]} | 3D Printable STL File | Digital Download",
            "description": (
                f"High quality 3D printable STL file for {idea}.\n\n"
                f"Print-ready, tested on Bambu Lab.\nScore: {score}/100."
            ),
            "tags": ["3d print", "stl file", "digital download", "3d printing"],
            "price_usd": 4.99,
            "category": "Digital Downloads",
        }
    return result
