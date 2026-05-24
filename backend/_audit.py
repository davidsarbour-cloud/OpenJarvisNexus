"""
Nexus9 Trend Scraper — Full Audit
  1. Import check (no unused/missing symbols)
  2. Smoke tests (unit — no network)
  3. Bug fix verification (C1, W9, W10, W11)
  4. Health check (module-level function calls)
  5. Benchmark (time key operations)
"""
import asyncio
import sys
import time as _time

PASS = 0
FAIL = 0

def ok(msg):
    global PASS
    PASS += 1
    print(f"  [OK] {msg}")

def fail(msg):
    global FAIL
    FAIL += 1
    print(f"  [!!] FAIL: {msg}", file=sys.stderr)

# ─────────────────────────────────────────────────────────────────────────────
# 1. IMPORT CHECK
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== 1. IMPORTS ===")

try:
    from scrapers.browser import get_browser_context, human_delay, close_browser, _LAUNCH_ARGS
    # C1: verify merged --disable-features
    disable_feat = [a for a in _LAUNCH_ARGS if a.startswith("--disable-features=")]
    assert len(disable_feat) == 1, f"Expected 1 --disable-features flag, got {len(disable_feat)}: {disable_feat}"
    val = disable_feat[0]
    assert "NetworkServiceSandbox" in val
    assert "VizDisplayCompositor" in val
    assert "IsolateOrigins" in val
    ok(f"browser.py C1 fixed: single --disable-features flag with {val.count(',') + 1} values")
except Exception as e:
    fail(f"browser import / C1: {e}")

try:
    # W2: INTENT_PHRASES NOT in reddit_scraper namespace
    import scrapers.reddit_scraper as rr
    assert not hasattr(rr, 'INTENT_PHRASES'), "W2: INTENT_PHRASES should be gone"
    # W11: uses _norm_vel not local _normalize_velocity
    assert hasattr(rr, '_norm_vel'), "W11: _norm_vel should exist"
    assert not hasattr(rr, '_normalize_velocity'), "W11: local _normalize_velocity should be removed"
    ok("reddit_scraper.py W2+W11 fixed")
except Exception as e:
    fail(f"reddit_scraper W2/W11: {e}")

try:
    # W3: normalize_tiktok_velocity NOT imported in fusion
    import trend_engine.fusion as fus
    import inspect
    src = inspect.getsource(fus)
    assert "normalize_tiktok_velocity" not in src, "W3: still imported in fusion"
    # W7/W8: reddit_intent_hits / reddit_texts_count NOT in fusion
    assert "reddit_intent_hits" not in src, "W7: dead var still in fusion"
    assert "reddit_texts_count" not in src, "W8: dead var still in fusion"
    ok("fusion.py W3+W7+W8 fixed")
except Exception as e:
    fail(f"fusion W3/W7/W8: {e}")

try:
    # W4: signals_summary NOT imported in store
    import trend_memory.store as st
    import inspect
    src = inspect.getsource(st)
    assert "signals_summary" not in src, "W4: still imported in store"
    ok("store.py W4 fixed")
except Exception as e:
    fail(f"store W4: {e}")

try:
    # W5: dead imports gone from trend_hunter
    import trend_hunter as th
    import inspect
    src = inspect.getsource(th)
    assert "normalize_reddit_velocity" not in src, "W5a: still in trend_hunter"
    assert "INTENT_PHRASES" not in src, "W5b: still in trend_hunter"
    ok("trend_hunter.py W5 fixed")
except Exception as e:
    fail(f"trend_hunter W5: {e}")

try:
    # W6: asyncio NOT imported in tiktok_scraper
    import scrapers.tiktok_scraper as tt
    import inspect
    src = inspect.getsource(tt)
    assert "import asyncio" not in src, "W6: asyncio still imported"
    ok("tiktok_scraper.py W6 fixed")
except Exception as e:
    fail(f"tiktok W6: {e}")

try:
    # W10: no assert in scoring
    import inspect, trend_engine.scoring as sc
    src = inspect.getsource(sc)
    assert "assert abs(sum(WEIGHTS" not in src, "W10: assert still in scoring"
    # get_action now takes only stage
    import inspect as ins
    sig = ins.signature(sc.get_action)
    params = list(sig.parameters.keys())
    assert params == ["stage"], f"W10/I2: get_action params should be ['stage'], got {params}"
    ok(f"scoring.py W10+I2 fixed: get_action({params}), no assert")
except Exception as e:
    fail(f"scoring W10/I2: {e}")

try:
    # I1: _extract_text_count_from_playwright removed from etsy
    import scrapers.etsy_scraper as et
    import inspect
    src = inspect.getsource(et)
    assert "_extract_text_count_from_playwright" not in src, "I1: dead func still in etsy"
    ok("etsy_scraper.py I1 fixed: dead function removed")
except Exception as e:
    fail(f"etsy I1: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# 2. SMOKE TESTS (no network)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== 2. SMOKE TESTS ===")

try:
    from trend_engine.sentiment import scan_intent, score_intent, INTENT_PHRASES, VIRAL_HOOKS
    h, _ = scan_intent(["where can i buy this?", "just a post"])
    assert h >= 1
    s = score_intent(5, 25)
    assert 0 < s < 1
    ok(f"sentiment: {len(INTENT_PHRASES)} phrases, {len(VIRAL_HOOKS)} hooks, scan OK")
except Exception as e:
    fail(f"sentiment: {e}")

try:
    from trend_engine.velocity import (
        normalize_reddit_velocity, normalize_google_breakout,
        normalize_etsy_listing_count, fuse_velocity, detect_momentum
    )
    assert normalize_reddit_velocity(1000) == 1.0
    assert normalize_google_breakout(2.0) == 1.0
    assert normalize_etsy_listing_count(0) == 0.5
    assert fuse_velocity(1.0, 1.0, 1.0) == 1.0
    assert detect_momentum(0.9, [0.5, 0.5]) == "RISING"
    ok("velocity: all normalizers + fuse + momentum OK")
except Exception as e:
    fail(f"velocity: {e}")

try:
    from trend_engine.scoring import compute_trend_score, get_alert_level, get_stage, get_action, WEIGHTS
    ts = compute_trend_score("test", 0.8, 0.7, 3, "LOW")
    assert ts.score >= 60
    assert ts.alert_level in ("HIGH", "MEDIUM")
    assert get_action("BUILD") == "Build product — high demand, low competition"
    assert get_action("IGNORE") == "Skip — insufficient signal"
    ok(f"scoring: score={ts.score}, alert={ts.alert_level}, stage={ts.stage}")
except Exception as e:
    fail(f"scoring: {e}")

try:
    from trend_engine.fusion import fuse_signals, signals_summary
    ts = fuse_signals(
        "test kw",
        reddit={"post_count": 10, "velocity_raw": 500, "intent_score": 0.5, "unique_subs": 3, "error": None},
        etsy={"listing_count": 100, "competition_level": "MEDIUM", "competition_score": 0.6, "jackpot": False, "error": None},
    )
    assert ts.score >= 0
    assert "reddit" in ts.platforms
    assert "etsy" in ts.platforms
    # W9 check: etsy with count=0 and no jackpot should NOT be in platforms
    ts2 = fuse_signals("ghost", etsy={"listing_count": 0, "jackpot": False, "error": None})
    assert "etsy" not in ts2.platforms, f"W9: etsy with count=0 still in platforms: {ts2.platforms}"
    ok(f"fusion: score={ts.score}, platforms={ts.platforms}, W9 OK")
except Exception as e:
    fail(f"fusion: {e}")

try:
    import tempfile
    from pathlib import Path
    from trend_memory.store import record_trend, mark_winner, get_niche, summary_stats
    from trend_engine.scoring import compute_trend_score
    tmp = Path(tempfile.mktemp(suffix=".json"))
    ts = compute_trend_score("test niche", 0.7, 0.6, 2, "LOW")
    record_trend(ts, path=tmp)
    n = get_niche("test niche", tmp)
    assert n is not None
    assert n["peak_score"] == ts.score
    stats = summary_stats(tmp)
    assert stats["total_tracked"] == 1
    tmp.unlink(missing_ok=True)
    ok(f"store: record+get+stats OK, score={ts.score}")
except Exception as e:
    fail(f"store: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# 3. HEALTH CHECK (function-level, no network)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== 3. HEALTH CHECK ===")

try:
    # Scoring integrity
    from trend_engine.scoring import WEIGHTS, ALERT_THRESHOLDS
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9
    assert ALERT_THRESHOLDS["HIGH"] == 70
    assert ALERT_THRESHOLDS["NOISE"] == 0
    ok("WEIGHTS sum=1.0, ALERT_THRESHOLDS correct")
except Exception as e:
    fail(f"scoring health: {e}")

try:
    # Browser executable detection
    from scrapers.browser import _get_browser_executable
    exe = _get_browser_executable()
    ok(f"Browser exe: {exe or 'bundled Chromium (fallback)'}")
except Exception as e:
    fail(f"browser health: {e}")

try:
    # Snapshot dir writable
    from pathlib import Path
    snap_dir = Path("trend_snapshots")
    snap_dir.mkdir(exist_ok=True)
    test_f = snap_dir / "_health_test.tmp"
    test_f.write_text("ok")
    test_f.unlink()
    ok(f"trend_snapshots/ dir writable")
except Exception as e:
    fail(f"snapshot dir: {e}")

try:
    # Memory store default path accessible
    from trend_memory.store import _DEFAULT_PATH
    _DEFAULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ok(f"trend_memory store path: {_DEFAULT_PATH.parent}")
except Exception as e:
    fail(f"memory store path: {e}")

try:
    # trend_hunter config read
    from trend_hunter import _hunter_cfg, _cfg
    cfg = _hunter_cfg()
    ok(f"trend_hunter config: tickers={cfg.get('tickers', [])}, kws={len(cfg.get('dropshipping_keywords', []))}")
except Exception as e:
    fail(f"trend_hunter config: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# 4. BENCHMARK
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== 4. BENCHMARK ===")

ITERATIONS = 1000

# sentiment scan
t0 = _time.perf_counter()
for _ in range(ITERATIONS):
    scan_intent(["where can i buy this?", "i need this in my life", "normal post"] * 5)
ms = (_time.perf_counter() - t0) * 1000
ok(f"scan_intent x{ITERATIONS}: {ms:.1f}ms total = {ms/ITERATIONS:.3f}ms/call")

# score computation
from trend_engine.scoring import compute_trend_score
t0 = _time.perf_counter()
for _ in range(ITERATIONS):
    compute_trend_score("test product", 0.7, 0.5, 3, "MEDIUM")
ms = (_time.perf_counter() - t0) * 1000
ok(f"compute_trend_score x{ITERATIONS}: {ms:.1f}ms total = {ms/ITERATIONS:.3f}ms/call")

# fusion
from trend_engine.fusion import fuse_signals
reddit_sig = {"post_count": 10, "velocity_raw": 400, "intent_score": 0.4, "unique_subs": 2, "error": None}
etsy_sig   = {"listing_count": 200, "competition_level": "MEDIUM", "jackpot": False, "error": None}
t0 = _time.perf_counter()
for _ in range(ITERATIONS):
    fuse_signals("bench kw", reddit=reddit_sig, etsy=etsy_sig)
ms = (_time.perf_counter() - t0) * 1000
ok(f"fuse_signals x{ITERATIONS}: {ms:.1f}ms total = {ms/ITERATIONS:.3f}ms/call")

# velocity normalizations
from trend_engine.velocity import normalize_reddit_velocity, fuse_velocity
t0 = _time.perf_counter()
for _ in range(ITERATIONS):
    normalize_reddit_velocity(350)
    fuse_velocity(0.5, 0.3, 0.7)
ms = (_time.perf_counter() - t0) * 1000
ok(f"velocity ops x{ITERATIONS}: {ms:.1f}ms total = {ms/ITERATIONS:.3f}ms/call")


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"  PASS: {PASS}   FAIL: {FAIL}")
print(f"{'='*60}")
if FAIL > 0:
    sys.exit(1)
