"""Reusable icon catalogs. Bundle IDs are real iOS first-party app IDs so the
Siri Shortcut installer can open the right app. Labels are 2-4 char strings
chosen to be distinct across the catalog (no two icons share the same label)."""
from __future__ import annotations

from .brief import IconSpec, PackBrief

# 30-app iOS pilot catalog. Bundle IDs verified from Apple's public docs.
# All distinct labels (no collisions) so 30 minimal icons stay distinguishable.
MINIMAL_BLACK_30: list[IconSpec] = [
    IconSpec(name="Mail",        bundle_id="com.apple.mobilemail",      label="Mail"),
    IconSpec(name="Messages",    bundle_id="com.apple.MobileSMS",       label="Msg"),
    IconSpec(name="Phone",       bundle_id="com.apple.mobilephone",     label="Tel"),
    IconSpec(name="Safari",      bundle_id="com.apple.mobilesafari",    label="Web"),
    IconSpec(name="Camera",      bundle_id="com.apple.camera",          label="Cam"),
    IconSpec(name="Settings",    bundle_id="com.apple.Preferences",     label="Set"),
    IconSpec(name="Photos",      bundle_id="com.apple.mobileslideshow", label="Pic"),
    IconSpec(name="Calendar",    bundle_id="com.apple.mobilecal",       label="Cal"),
    IconSpec(name="Notes",       bundle_id="com.apple.mobilenotes",     label="Nts"),
    IconSpec(name="Maps",        bundle_id="com.apple.Maps",            label="Map"),
    IconSpec(name="Music",       bundle_id="com.apple.Music",           label="Mus"),
    IconSpec(name="App Store",   bundle_id="com.apple.AppStore",        label="App"),
    IconSpec(name="Clock",       bundle_id="com.apple.mobiletimer",     label="Clk"),
    IconSpec(name="Calculator",  bundle_id="com.apple.calculator",      label="±"),
    IconSpec(name="Weather",     bundle_id="com.apple.weather",         label="Wth"),
    IconSpec(name="Files",       bundle_id="com.apple.DocumentsApp",    label="Fil"),
    IconSpec(name="FaceTime",    bundle_id="com.apple.facetime",        label="FT"),
    IconSpec(name="Wallet",      bundle_id="com.apple.Passbook",        label="Wal"),
    IconSpec(name="Reminders",   bundle_id="com.apple.reminders",       label="Rem"),
    IconSpec(name="Health",      bundle_id="com.apple.Health",          label="Hth"),
    IconSpec(name="Voice Memos", bundle_id="com.apple.VoiceMemos",      label="Vox"),
    IconSpec(name="Compass",     bundle_id="com.apple.compass",         label="Cmp"),
    IconSpec(name="TV",          bundle_id="com.apple.tv",              label="TV"),
    IconSpec(name="Podcasts",    bundle_id="com.apple.podcasts",        label="Pod"),
    IconSpec(name="Books",       bundle_id="com.apple.iBooks",          label="Bks"),
    IconSpec(name="News",        bundle_id="com.apple.news",            label="Nws"),
    IconSpec(name="Stocks",      bundle_id="com.apple.stocks",          label="Stk"),
    IconSpec(name="Home",        bundle_id="com.apple.Home",            label="Hom"),
    IconSpec(name="Find My",     bundle_id="com.apple.findmy",          label="Fnd"),
    IconSpec(name="Shortcuts",   bundle_id="com.apple.shortcuts",       label="Cut"),
]


def minimal_black_pilot() -> PackBrief:
    """The Phase 1 pilot brief — procedural, 30 distinct minimal icons."""
    return PackBrief(
        name="Minimal Black",
        version="1.0.0",
        theme="Bold white letters on matte-black iOS squircle. Geometric, "
              "high-contrast, modern minimalism.",
        category="Minimal",
        generator="procedural",
        targets=["ios", "android", "streamdeck"],
        bg_color="#000000",
        fg_color="#FFFFFF",
        corner_radius_frac=0.22,
        icons=MINIMAL_BLACK_30,
    )
