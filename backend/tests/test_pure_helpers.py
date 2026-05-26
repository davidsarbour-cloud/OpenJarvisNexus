"""Unit tests for pure backend helpers.

The other files under backend/tests/ are manual probe scripts (Claude API
finder, vault skill search, raw HTTP probe) — they live behind a
`__main__` guard so pytest's collection doesn't fire their live calls.
This file is the actual pytest harness for in-process logic.
"""
import sys
from pathlib import Path

# Make backend/ importable when pytest runs from anywhere
sys.path.insert(0, str(Path(__file__).parent.parent))

from ollama_client import strip_think_tags  # noqa: E402
from trend_engine.scoring import get_alert_level, monetization_score  # noqa: E402


class TestStripThinkTags:
    def test_removes_single_block(self):
        assert strip_think_tags("<think>noise</think>real answer") == "real answer"

    def test_removes_multiline_block(self):
        raw = "<think>line1\nline2\nline3</think>\nfinal"
        assert strip_think_tags(raw) == "final"

    def test_removes_multiple_blocks(self):
        raw = "<think>a</think>middle<think>b</think>end"
        assert strip_think_tags(raw) == "middleend"

    def test_passes_through_when_no_tag(self):
        assert strip_think_tags("plain text") == "plain text"

    def test_strips_surrounding_whitespace(self):
        assert strip_think_tags("  <think>x</think>  hello  ") == "hello"


class TestAlertLevel:
    """ALERT_THRESHOLDS: HIGH≥70, MEDIUM≥40, WATCH≥20, NOISE<20."""

    def test_high_for_top_scores(self):
        level, emoji = get_alert_level(95)
        assert level == "HIGH"
        assert emoji  # non-empty

    def test_high_at_lower_bound(self):
        level, _ = get_alert_level(70)
        assert level == "HIGH"

    def test_medium_band(self):
        level, _ = get_alert_level(50)
        assert level == "MEDIUM"

    def test_watch_band(self):
        level, _ = get_alert_level(20)
        assert level == "WATCH"

    def test_noise_below_threshold(self):
        level, _ = get_alert_level(5)
        assert level == "NOISE"

    def test_accepts_float_scores(self):
        # Conversion happens via int() inside the function — 69.9 → 69 → MEDIUM
        assert get_alert_level(69.9)[0] == "MEDIUM"
        assert get_alert_level(70.1)[0] == "HIGH"


class TestMonetizationScore:
    """monetization_score does substring match and keeps the *max* over all
    hits, so 0.5 acts as a neutral floor — low-margin keywords cannot pull
    below it. The tests pin that documented behavior."""

    def test_known_high_margin_keyword(self):
        assert monetization_score("ergonomic") == 0.9
        assert monetization_score("wedding")   == 0.85

    def test_low_margin_keyword_floored_at_neutral(self):
        # "generic" maps to 0.3 in the table, but the function takes max with
        # the 0.5 neutral default — so the low-margin signal is effectively
        # capped. This is the current (somewhat surprising) behavior.
        assert monetization_score("generic") == 0.5

    def test_unknown_keyword_defaults_to_neutral(self):
        assert monetization_score("xyzzy_unknown_word") == 0.5

    def test_case_insensitive_lookup(self):
        assert monetization_score("Ergonomic") == monetization_score("ergonomic")

    def test_substring_match_picks_strongest(self):
        # "personalized wedding gift" should match wedding (0.85) and gift
        # (0.8) and personalized (0.85) — function returns max = 0.85
        assert monetization_score("personalized wedding gift") == 0.85
