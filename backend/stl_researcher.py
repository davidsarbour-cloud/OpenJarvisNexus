"""
STL Researcher Agent — daily 21:00 trend report
Fetches top-selling / most-downloaded 3D models from Thingiverse, Cults3D and Etsy
to inspire D3Dprintix new product ideas. Saves to backend/research_logs/.

Designed to plug into APScheduler in main.py.
"""

import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter()

RESEARCH_DIR = Path(__file__).parent / "research_logs"
RESEARCH_DIR.mkdir(exist_ok=True)

# Optional API keys (free tier is fine)
THINGIVERSE_TOKEN = os.getenv("THINGIVERSE_TOKEN", "")
ETSY_API_KEY      = os.getenv("ETSYPUBLIC_KEY", "")

USER_AGENT = "JARVIS-NexusX9-Researcher/0.1 (+D3Dprintix research bot)"

# ── Thingiverse ──────────────────────────────────────────

async def fetch_thingiverse_popular(limit: int = 20) -> list[dict]:
    """Thingiverse popular this week. Uses public API (no key needed for public data)."""
    url = "https://api.thingiverse.com/popular"
    headers = {"User-Agent": USER_AGENT}
    params = {"per_page": limit, "page": 1}
    if THINGIVERSE_TOKEN:
        headers["Authorization"] = f"Bearer {THINGIVERSE_TOKEN}"
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(url, headers=headers, params=params, timeout=20)
            if r.status_code != 200:
                return [{"source": "thingiverse", "error": f"HTTP {r.status_code}"}]
            data = r.json()
            items = data if isinstance(data, list) else data.get("hits", [])
            return [
                {
                    "source":      "thingiverse",
                    "title":       it.get("name", ""),
                    "url":         it.get("public_url") or it.get("absolute_url", ""),
                    "thumbnail":   it.get("thumbnail", ""),
                    "downloads":   it.get("download_count"),
                    "likes":       it.get("like_count"),
                    "tags":        it.get("tags", []),
                    "license":     it.get("license", ""),
                }
                for it in items[:limit]
            ]
    except Exception as e:
        return [{"source": "thingiverse", "error": str(e)}]


# ── Cults3D ──────────────────────────────────────────────

async def fetch_cults3d_bestsellers(limit: int = 20) -> list[dict]:
    """Cults3D has no public API — scrape best-sellers page (HTML parsing)."""
    url = "https://cults3d.com/en/3d-models/best-sellers"
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}
    try:
        async with httpx.AsyncClient(follow_redirects=True) as c:
            r = await c.get(url, headers=headers, timeout=20)
            if r.status_code != 200:
                return [{"source": "cults3d", "error": f"HTTP {r.status_code}"}]
            html = r.text
            # Lightweight regex extraction of card titles + URLs
            cards = re.findall(
                r'<a[^>]+class="[^"]*creation[^"]*"[^>]+href="([^"]+)"[^>]*>.*?<h3[^>]*>([^<]+)</h3>',
                html, re.S
            )[:limit]
            return [
                {
                    "source": "cults3d",
                    "title":  title.strip(),
                    "url":    href if href.startswith("http") else "https://cults3d.com" + href,
                }
                for href, title in cards
            ]
    except Exception as e:
        return [{"source": "cults3d", "error": str(e)}]


# ── Etsy ─────────────────────────────────────────────────

async def fetch_etsy_top_stl(limit: int = 20) -> list[dict]:
    """Etsy top STL listings — keyword search sorted by relevance."""
    if not ETSY_API_KEY:
        return [{"source": "etsy", "error": "ETSYPUBLIC_KEY not set"}]
    url = "https://openapi.etsy.com/v3/application/listings/active"
    headers = {"x-api-key": ETSY_API_KEY, "User-Agent": USER_AGENT}
    params = {"keywords": "stl 3d printing", "limit": limit, "sort_on": "score"}
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(url, headers=headers, params=params, timeout=20)
            if r.status_code != 200:
                return [{"source": "etsy", "error": f"HTTP {r.status_code}: {r.text[:120]}"}]
            data = r.json()
            return [
                {
                    "source": "etsy",
                    "title":  l.get("title", ""),
                    "url":    l.get("url", ""),
                    "price":  l.get("price", {}).get("amount") if isinstance(l.get("price"), dict) else None,
                    "views":  l.get("views"),
                    "favorers": l.get("num_favorers"),
                }
                for l in data.get("results", [])[:limit]
            ]
    except Exception as e:
        return [{"source": "etsy", "error": str(e)}]


# ── Daily report ─────────────────────────────────────────

async def generate_daily_report() -> dict:
    """Fetch all sources in parallel + save snapshot."""
    print("[RESEARCHER] Generating daily STL trends report...")
    thingiverse, cults3d, etsy = await asyncio.gather(
        fetch_thingiverse_popular(20),
        fetch_cults3d_bestsellers(20),
        fetch_etsy_top_stl(20),
    )
    report = {
        "generated_at": datetime.now().isoformat(),
        "thingiverse":  thingiverse,
        "cults3d":      cults3d,
        "etsy":         etsy,
        "summary": {
            "thingiverse_count": sum(1 for x in thingiverse if "error" not in x),
            "cults3d_count":     sum(1 for x in cults3d if "error" not in x),
            "etsy_count":        sum(1 for x in etsy if "error" not in x),
        },
    }
    date = datetime.now().strftime("%Y-%m-%d")
    out = RESEARCH_DIR / f"{date}.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[RESEARCHER] Saved: {out.name} — {report['summary']}")
    return report


# ── Routes ───────────────────────────────────────────────

@router.post("/v1/research/run")
async def run_now():
    """Manual trigger — same as the scheduled 21:00 job."""
    return await generate_daily_report()


@router.get("/v1/research/latest")
def latest_report():
    files = sorted(RESEARCH_DIR.glob("*.json"), reverse=True)
    if not files:
        raise HTTPException(404, "No report yet — POST /v1/research/run to generate one")
    return json.loads(files[0].read_text(encoding="utf-8"))


@router.get("/v1/research/history")
def list_history():
    return [f.stem for f in sorted(RESEARCH_DIR.glob("*.json"), reverse=True)]
