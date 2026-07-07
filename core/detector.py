"""URL detection: youtube (single/playlist), tiktok, instagram, generic."""
from __future__ import annotations

import re
from typing import Literal

Platform = Literal[
    "youtube", "youtube_playlist", "tiktok", "instagram", "twitter", "generic"
]

_YT_DOMAINS = ("youtube.com", "youtu.be", "m.youtube.com", "music.youtube.com")
_TT_DOMAINS = ("tiktok.com", "vm.tiktok.com")
_IG_DOMAINS = ("instagram.com", "instagr.am")
_TW_DOMAINS = ("twitter.com", "x.com")

_URL_RE = re.compile(r"https?://[^\s<>\"']+")


def extract_urls(text: str) -> list[str]:
    return _URL_RE.findall(text or "")


def detect(url: str) -> Platform:
    u = url.lower().strip()
    if not u.startswith(("http://", "https://")):
        return "generic"

    host = _host(u)

    if any(d in host for d in _YT_DOMAINS):
        has_v = "v=" in u or "youtu.be/" in u or "/shorts/" in u
        has_list = "list=" in u
        if has_list and not has_v:
            return "youtube_playlist"
        if has_list and has_v:
            return "youtube_playlist"  # single video inside a playlist still treated as playlist
        return "youtube"

    if any(d in host for d in _TT_DOMAINS):
        return "tiktok"
    if any(d in host for d in _IG_DOMAINS):
        return "instagram"
    if any(d in host for d in _TW_DOMAINS):
        return "twitter"
    return "generic"


def _host(url: str) -> str:
    m = re.match(r"https?://([^/]+)", url)
    return m.group(1) if m else ""


def youtube_video_id(url: str) -> str | None:
    u = url
    m = re.search(r"[?&]v=([A-Za-z0-9_-]{6,})", u)
    if m:
        return m.group(1)
    m = re.search(r"youtu\.be/([A-Za-z0-9_-]{6,})", u)
    if m:
        return m.group(1)
    m = re.search(r"/shorts/([A-Za-z0-9_-]{6,})", u)
    if m:
        return m.group(1)
    return None


def youtube_playlist_id(url: str) -> str | None:
    m = re.search(r"[?&]list=([A-Za-z0-9_-]{6,})", url)
    return m.group(1) if m else None
