"""Persistent config: portable-aware (next to EXE) or ~/.tex/config.json"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

def _base_dir() -> Path:
    """Return the config root:

    * Portable: ``<exe_dir>/TexData/`` when running from a PyInstaller bundle.
    * Installed: ``~/.tex/`` (the historical default).
    """
    if getattr(sys, 'frozen', False):
        exe = Path(sys.executable).resolve().parent
        return exe / "TexData"
    return Path.home() / ".tex"


CONFIG_DIR = _base_dir()
CONFIG_PATH = CONFIG_DIR / "config.json"
THUMBS_DIR = CONFIG_DIR / "thumbs"

DEFAULTS: dict[str, Any] = {
    "save_dir": str(Path.home() / "Downloads" / "Tex"),
    "subdirs": {"video": "Video", "audio": "Audio"},
    "concurrency": 0,  # 0 = unlimited — user explicitly asked for this
    "speed_limit_bps": 0,
    "theme": "dark",
    "filename_template": "{title} [{quality}].{ext}",
    "cookies_file": "",
    "cookies_from_browser": "auto",
    "retries": 3,
    "watch_clipboard": True,
    "minimize_to_tray": True,
    "theme_accent": "#D7191A",
    "sounds_enabled": True,
    "notifications_enabled": True,
}

# In-memory cache. Invalidated by save().
_CACHE: dict[str, Any] | None = None


def _ensure_dirs() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    THUMBS_DIR.mkdir(parents=True, exist_ok=True)


def load() -> dict[str, Any]:
    """Return the merged config (defaults + on-disk overrides).

    Cached in memory; ``save()`` invalidates the cache.
    """
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    _ensure_dirs()
    if not CONFIG_PATH.exists():
        save(DEFAULTS)
        _CACHE = dict(DEFAULTS)
        return _CACHE
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        data = {}
    merged = dict(DEFAULTS)
    merged.update(data)
    _CACHE = merged
    return _CACHE


def invalidate() -> None:
    """Drop the in-memory cache. Next ``load()`` re-reads the file."""
    global _CACHE
    _CACHE = None
    metadata_cache_clear()


def metadata_cache_clear() -> None:
    """Also clear the metadata fetch cache (auth changes invalidate results)."""
    from .metadata import clear_cache
    clear_cache()


def save(cfg: dict[str, Any]) -> None:
    _ensure_dirs()
    tmp = CONFIG_PATH.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    try:
        os.replace(tmp, CONFIG_PATH)
    except PermissionError:
        # Windows: file may be locked by antivirus or another instance.
        # Best-effort: try to remove the old file first, then rename.
        try:
            CONFIG_PATH.unlink(missing_ok=True)
            tmp.rename(CONFIG_PATH)
        except OSError:
            pass  # give up — cache is still valid
    invalidate()


def get(key: str, default: Any = None) -> Any:
    return load().get(key, default)


def set_value(key: str, value: Any) -> None:
    cfg = load()
    cfg[key] = value
    save(cfg)


def ensure_save_subdir(kind: str) -> Path:
    """Return (and create) the configured subdirectory for 'video' or 'audio'."""
    cfg = load()
    base = Path(cfg.get("save_dir", str(Path.home() / "Downloads" / "Tex")))
    subdirs = cfg.get("subdirs")
    if isinstance(subdirs, dict):
        sub = subdirs.get(kind, "Video" if kind == "video" else "Audio")
    else:
        sub = "Video" if kind == "video" else "Audio"
    out = base / sub
    out.mkdir(parents=True, exist_ok=True)
    return out
