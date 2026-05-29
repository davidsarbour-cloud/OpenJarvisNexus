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

# Optional API keys. Etsy uses the SAME key as the rest of the app
# (commerce/etsy_client reads ETSY_API_KEY); fall back to the legacy
# ETSYPUBLIC_KEY name so either works.
THINGIVERSE_TOKEN = os.getenv("THINGIVERSE_TOKEN", "")
ETSY_API_KEY      = os.getenv("ETSY_API_KEY", "") or os.getenv("ETSYPUBLIC_KEY", "")
# Reddit blocks the anonymous .json endpoints from datacenter IPs (HTTP 403).
# A free "script" app (reddit.com/prefs/apps) gives client id/secret → OAuth,
# which works from any IP. Without creds we still try the keyless endpoint
# (usually fine from a home/residential IP).
REDDIT_CLIENT_ID     = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")

USER_AGENT = "JARVIS-NexusX9-Researcher/0.1 (+D3Dprintix research bot)"

# Reddit is the keyless workhorse — these communities surface what's actually
# trending / printing well right now.
STL_SUBREDDITS = ["3Dprinting", "functionalprint", "3Dmodeling", "BambuLab", "ender3", "prusa3d"]


# ── Reddit (primary source — OAuth if creds, else keyless) ────────────────────

async def _reddit_token(c: httpx.AsyncClient) -> str | None:
    """App-only OAuth token (client_credentials). None if no creds / failure."""
    if not (REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET):
        return None
    try:
        r = await c.post(
            "https://www.reddit.com/api/v1/access_token",
            data={"grant_type": "client_credentials"},
            auth=(REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET),
            headers={"User-Agent": USER_AGENT},
            timeout=15,
        )
        return r.json().get("access_token") if r.status_code == 200 else None
    except Exception:
        return None


async def fetch_reddit_3d_trends(limit: int = 20) -> list[dict]:
    """Top 3D-printing posts this week across key subreddits.

    Uses Reddit OAuth when REDDIT_CLIENT_ID/SECRET are set (robust, any IP),
    otherwise the keyless .json endpoint (works from residential IPs; 403 from
    datacenter IPs)."""
    out: list[dict] = []
    last_status = None
    try:
        async with httpx.AsyncClient(follow_redirects=True) as c:
            token = await _reddit_token(c)
            base = "https://oauth.reddit.com" if token else "https://www.reddit.com"
            headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            for sub in STL_SUBREDDITS:
                try:
                    r = await c.get(
                        f"{base}/r/{sub}/top.json",
                        headers=headers,
                        params={"t": "week", "limit": 15, "raw_json": 1},
                        timeout=15,
                    )
                    last_status = r.status_code
                    if r.status_code != 200:
                        continue
                    for child in r.json().get("data", {}).get("children", []):
                        d = child.get("data", {})
                        thumb = d.get("thumbnail", "")
                        out.append({
                            "source":    "reddit",
                            "subreddit": sub,
                            "title":     d.get("title", ""),
                            "url":       "https://www.reddit.com" + d.get("permalink", ""),
                            "score":     d.get("score", 0),
                            "comments":  d.get("num_comments", 0),
                            "thumbnail": thumb if isinstance(thumb, str) and thumb.startswith("http") else "",
                        })
                except Exception:
                    continue
        if not out:
            hint = (f"HTTP {last_status}" if last_status else "network error")
            if last_status == 403 and not token:
                hint += " — datacenter IP blocked; set REDDIT_CLIENT_ID/SECRET (free app) for OAuth"
            return [{"source": "reddit", "error": f"no posts ({hint})"}]
        out.sort(key=lambda x: x.get("score", 0), reverse=True)
        return out[:limit]
    except Exception as e:
        return [{"source": "reddit", "error": str(e)}]

# ── Thingiverse ──────────────────────────────────────────

async def fetch_thingiverse_popular(limit: int = 20) -> list[dict]:
    """Thingiverse popular. REQUIRES a free app token (THINGIVERSE_TOKEN) —
    the API rejects anonymous calls with 401. Get one at
    thingiverse.com/apps/create (an app token, free)."""
    if not THINGIVERSE_TOKEN:
        return [{"source": "thingiverse",
                 "error": "THINGIVERSE_TOKEN not set — create a free app at thingiverse.com/apps/create"}]
    url = "https://api.thingiverse.com/popular"
    headers = {"User-Agent": USER_AGENT, "Authorization": f"Bearer {THINGIVERSE_TOKEN}"}
    params = {"per_page": limit, "page": 1}
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
        return [{"source": "etsy", "error": "ETSY_API_KEY not set (same key as Etsy OAuth in .env)"}]
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
    reddit, thingiverse, cults3d, etsy = await asyncio.gather(
        fetch_reddit_3d_trends(20),
        fetch_thingiverse_popular(20),
        fetch_cults3d_bestsellers(20),
        fetch_etsy_top_stl(20),
    )
    report = {
        "generated_at": datetime.now().isoformat(),
        "reddit":       reddit,
        "thingiverse":  thingiverse,
        "cults3d":      cults3d,
        "etsy":         etsy,
        "summary": {
            "reddit_count":      sum(1 for x in reddit if "error" not in x),
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
