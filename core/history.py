"""Local download history (last 50)."""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import config

MAX = 50


@dataclass
class HistoryEntry:
    title: str
    uploader: str
    url: str
    quality: str
    kind: str            # "video" | "audio"
    path: str
    size: int = 0
    duration: int = 0
    finished_at: float = 0.0
    thumbnail: str = ""


def _path() -> Path:
    return config.CONFIG_DIR / "history.json"


def load_all() -> list[HistoryEntry]:
    p = _path()
    if not p.exists():
        return []
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []
    return [HistoryEntry(**x) for x in data if isinstance(x, dict)]


def add(entry: HistoryEntry) -> list[HistoryEntry]:
    items = load_all()
    items.insert(0, entry)
    items = items[:MAX]
    _save(items)
    return items


def _save(items: list[HistoryEntry]) -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump([asdict(i) for i in items], f, indent=2)
    try:
        os.replace(tmp, p)
    except PermissionError:
        try:
            p.unlink(missing_ok=True)
            tmp.rename(p)
        except OSError:
            pass


def try_get_size(path: str) -> int:
    try:
        return Path(path).stat().st_size
    except OSError:
        return 0
