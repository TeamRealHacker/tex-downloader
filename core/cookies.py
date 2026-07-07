"""Browser cookie auto-detection.

Lets Tex authenticate to age-restricted / private content using cookies pulled
straight from the user's installed browser. No more "go find your cookies.txt".

The supported set is the same as yt-dlp's ``--cookies-from-browser``:

    chrome, chromium, firefox, edge, brave, opera, opera_gx, vivaldi, safari, whale, lynx

For each browser we provide a cheap file-existence check on the platform's
typical install paths. ``detect_browser()`` returns the first match in priority
order, or ``None`` if nothing is installed.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable, Optional

# (yt-dlp key, human label, list of candidate paths to check)
BrowserDef = tuple[str, str, list[str]]


def _windows_paths() -> dict[str, list[str]]:
    """Return candidate paths for each browser on Windows."""
    la = os.environ.get("LOCALAPPDATA", "")
    ra = os.environ.get("APPDATA", "")
    return {
        "chrome":   [f"{la}\\Google\\Chrome\\User Data\\Default\\Cookies"],
        "chromium": [f"{la}\\Chromium\\User Data\\Default\\Cookies"],
        "edge":     [f"{la}\\Microsoft\\Edge\\User Data\\Default\\Cookies"],
        "brave":    [f"{la}\\BraveSoftware\\Brave-Browser\\User Data\\Default\\Cookies"],
        "opera":    [f"{ra}\\Opera Software\\Opera Stable\\Cookies"],
        "opera_gx": [f"{ra}\\Opera Software\\Opera GX Stable\\Cookies"],
        "vivaldi":  [f"{la}\\Vivaldi\\User Data\\Default\\Cookies"],
        "whale":    [f"{la}\\Naver\\Whale\\User Data\\Default\\Cookies"],
    }


def _mac_paths() -> dict[str, list[str]]:
    home = os.environ.get("HOME", "")
    return {
        "chrome":   [f"{home}/Library/Application Support/Google/Chrome/Default/Cookies"],
        "chromium": [f"{home}/Library/Application Support/Chromium/Default/Cookies"],
        "edge":     [f"{home}/Library/Application Support/Microsoft Edge/Default/Cookies"],
        "brave":    [f"{home}/Library/Application Support/BraveSoftware/Brave-Browser/Default/Cookies"],
        "opera":    [f"{home}/Library/Application Support/com.operasoftware.Opera/Cookies"],
        "vivaldi":  [f"{home}/Library/Application Support/Vivaldi/Default/Cookies"],
        "firefox":  [f"{home}/Library/Application Support/Firefox/Profiles"],
    }


def _linux_paths() -> dict[str, list[str]]:
    home = os.environ.get("HOME", "")
    return {
        "chrome":   [f"{home}/.config/google-chrome/Default/Cookies"],
        "chromium": [f"{home}/.config/chromium/Default/Cookies"],
        "edge":     [f"{home}/.config/microsoft-edge/Default/Cookies"],
        "brave":    [f"{home}/.config/BraveSoftware/Brave-Browser/Default/Cookies"],
        "opera":    [f"{home}/.config/opera/Cookies"],
        "vivaldi":  [f"{home}/.config/vivaldi/Default/Cookies"],
    }


# Order matters: chrome → edge → firefox → brave → opera → vivaldi.
# (Firefox is checked last on Win/Mac because its file path is a directory
# tree of profile folders, not a single file.)
BROWSERS: list[BrowserDef] = [
    # key,        label,            detection paths
    ("chrome",    "Chrome",         _windows_paths().get("chrome", [])),  # populated per-OS
    ("chromium",  "Chromium",       []),
    ("edge",      "Microsoft Edge", []),
    ("brave",     "Brave",          []),
    ("opera",     "Opera",          []),
    ("opera_gx",  "Opera GX",       []),
    ("vivaldi",   "Vivaldi",        []),
    ("whale",     "Naver Whale",    []),
]


def _platform_paths() -> dict[str, list[str]]:
    if sys.platform.startswith("win"):
        return _windows_paths()
    if sys.platform == "darwin":
        return _mac_paths()
    return _linux_paths()


def _rebuild_browsers() -> list[BrowserDef]:
    """Rebuild BROWSERS with the right per-OS paths so detection is accurate."""
    p = _platform_paths()
    # Firefox uses a directory of profile subfolders, special-case
    ff_paths: list[str] = []
    if sys.platform.startswith("win"):
        ra = os.environ.get("APPDATA", "")
        ff_paths = [f"{ra}\\Mozilla\\Firefox\\Profiles"]
    elif sys.platform == "darwin":
        home = os.environ.get("HOME", "")
        ff_paths = [f"{home}/Library/Application Support/Firefox/Profiles"]
    else:
        home = os.environ.get("HOME", "")
        ff_paths = [f"{home}/.mozilla/firefox"]
    out: list[BrowserDef] = [
        ("chrome",    "Chrome",         p.get("chrome", [])),
        ("chromium",  "Chromium",       p.get("chromium", [])),
        ("edge",      "Microsoft Edge", p.get("edge", [])),
        ("brave",     "Brave",          p.get("brave", [])),
        ("opera",     "Opera",          p.get("opera", [])),
        ("opera_gx",  "Opera GX",       p.get("opera_gx", [])),
        ("vivaldi",   "Vivaldi",        p.get("vivaldi", [])),
        ("whale",     "Naver Whale",    p.get("whale", [])),
        ("firefox",   "Firefox",        ff_paths),
    ]
    return out


def available_browsers() -> list[BrowserDef]:
    """Return the list of browsers that look installed on this machine."""
    found: list[BrowserDef] = []
    for key, label, paths in _rebuild_browsers():
        if any(Path(p).exists() for p in paths):
            found.append((key, label, paths))
    return found


def detect_browser() -> Optional[str]:
    """Return the yt-dlp browser key of the first installed browser, or None."""
    for key, _label, paths in _rebuild_browsers():
        if any(Path(p).exists() for p in paths):
            return key
    return None


def is_valid(path: str | Path) -> bool:
    """Legacy helper: minimal structural check on a Netscape cookies.txt file.

    Kept in case the user wants to feed a hand-crafted cookies file via
    the config, but no longer surfaced in the UI.
    """
    p = Path(path)
    if not p.exists() or p.stat().st_size < 16:
        return False
    try:
        with p.open("r", encoding="utf-8", errors="ignore") as f:
            head = f.read(200)
    except OSError:
        return False
    return ("netscape" in head.lower()) or ("\t" in head)


# Strings that yt-dlp emits when browser-cookie extraction fails. Used by the
# fetch and download workers to trigger a silent retry without cookies.
# NOTE: keep these SPECIFIC to cookie issues — generic messages like
# "no such file" or "permission denied" match non-cookie errors (missing
# output dir, read-only fs) and would trigger a pointless retry.
_BROWSER_COOKIE_HINTS = (
    "failed to decrypt with dpapi",
    "failed to decrypt",
    "could not find a suitable keyring",
    "keyring",
    "could not find a profile",
    "failed to load cookies",
    "cookie database is locked",
    "cookiesfrombrowser",
    "decryption failed",
    "win32crypt",
    "no saved credentials",
)


def is_browser_cookie_error(err: str) -> bool:
    """Return True if the message looks like a browser-cookie extraction failure."""
    if not err:
        return False
    e = err.lower()
    return any(h in e for h in _BROWSER_COOKIE_HINTS)
