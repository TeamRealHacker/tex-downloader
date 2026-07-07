"""yt-dlp info-dict wrapper. Single source of truth for metadata."""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yt_dlp
from yt_dlp.utils import DownloadError

from . import config
from .detector import (
    Platform,
    detect,
    youtube_playlist_id,
    youtube_video_id,
)

_FFMPEG_LOCATION: str | None = None

# In-memory cache: url+no_cookies -> (timestamp, result)
_FETCH_CACHE: dict[tuple[str, bool], tuple[float, FetchResult]] = {}
_FETCH_CACHE_TTL = 300.0  # 5 min
_FETCH_CACHE_MAX = 32


def ffmpeg_location() -> str | None:
    """Resolve ffmpeg path once and cache."""
    global _FFMPEG_LOCATION
    if _FFMPEG_LOCATION is not None:
        return _FFMPEG_LOCATION
    try:
        import imageio_ffmpeg  # type: ignore

        _FFMPEG_LOCATION = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        _FFMPEG_LOCATION = None
    return _FFMPEG_LOCATION


@dataclass
class VideoInfo:
    id: str
    title: str
    uploader: str
    duration: int  # seconds
    thumbnail: str
    url: str
    webpage_url: str
    platform: Platform
    filesize_approx: int | None = None
    # quality_key -> bytes (computed once from the format list, replaces the
    # 9-worker size probe that used to run after every fetch).
    format_sizes: dict[str, int] = field(default_factory=dict)

    @property
    def duration_str(self) -> str:
        s = max(0, int(self.duration or 0))
        h, rem = divmod(s, 3600)
        m, s = divmod(rem, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


@dataclass
class PlaylistInfo:
    id: str
    title: str
    uploader: str
    entries: list[VideoInfo] = field(default_factory=list)


@dataclass
class FetchResult:
    kind: str  # "single" | "playlist"
    video: VideoInfo | None = None
    playlist: PlaylistInfo | None = None


def _common_opts(no_cookies: bool = False) -> dict[str, Any]:
    cfg = config.load()
    opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "no_color": True,
        "noprogress": True,
        "skip_download": True,
        "extract_flat": False,
        "noplaylist": False,
        "ignoreerrors": False,
    }
    ffm = ffmpeg_location()
    if ffm:
        opts["ffmpeg_location"] = ffm
    # Auth: explicit file overrides, else pull cookies from the user's browser.
    # ``no_cookies`` short-circuits both — used for the silent retry path.
    if not no_cookies:
        if cfg.get("cookies_file"):
            opts["cookiefile"] = cfg["cookies_file"]
        else:
            from .cookies import detect_browser
            browser = (cfg.get("cookies_from_browser", "auto") or "auto").strip().lower()
            if browser and browser not in ("none", "off", "no", "false", "0"):
                if browser in ("auto", "default"):
                    browser = detect_browser() or ""
                if browser:
                    opts["cookiesfrombrowser"] = (browser, None, None, None)
    return opts


def _compute_format_sizes(info: dict[str, Any]) -> dict[str, int]:
    """Given a yt-dlp info dict, return quality_key -> bytes for every option
    in MP4_QUALITIES + MP3_QUALITIES. Replaces the 9-worker _SizeWorker probe.
    """
    # Import here to avoid a cycle (formats.py is tiny but pure data)
    from .formats import MP3_QUALITIES, MP4_QUALITIES
    fmts = info.get("formats") or []
    if not fmts:
        return {}
    out: dict[str, int] = {}
    audios = [x for x in fmts if x.get("acodec") not in (None, "none")]
    if audios:
        best_audio = max(audios, key=lambda x: x.get("abr") or 0)
        best_audio_size = (
            best_audio.get("filesize") or best_audio.get("filesize_approx") or 0
        )
    else:
        best_audio_size = 0
    for opt in MP4_QUALITIES:
        h = int(opt.key.replace("p", ""))
        cand = [
            x for x in fmts
            if 0 < (x.get("height") or 0) <= h
            and x.get("vcodec") not in (None, "none")
        ]
        if not cand:
            continue
        # Pick closest resolution to target for more accurate estimates.
        cand.sort(key=lambda x: (abs((x.get("height") or 0) - h), -(x.get("tbr") or 0)))
        v = cand[0]
        v_size = v.get("filesize") or v.get("filesize_approx") or 0
        # We mux video+audio on download, so the total ≈ sum (with some overhead)
        if v_size:
            out[opt.key] = min(int(v_size) + int(best_audio_size), 2_147_483_647) if best_audio_size else int(v_size)
    for opt in MP3_QUALITIES:
        if not audios:
            continue
        target = int(opt.key)  # e.g. 320
        # Find audio with abr closest to target
        cand = sorted(audios, key=lambda x: abs((x.get("abr") or 0) - target))
        a = cand[0] if cand else None
        if not a:
            continue
        sz = a.get("filesize") or a.get("filesize_approx")
        if sz:
            out[opt.key] = int(sz)
    return out


def _to_video_info(d: dict[str, Any], url: str) -> VideoInfo:
    return VideoInfo(
        id=d.get("id", ""),
        title=(d.get("title") or d.get("description") or "Untitled")[:240],
        uploader=d.get("uploader") or d.get("channel") or d.get("creator") or "",
        duration=int(d.get("duration") or 0),
        thumbnail=_best_thumb(d),
        url=d.get("url") or url,
        webpage_url=d.get("webpage_url") or url,
        platform=detect(url),
        filesize_approx=d.get("filesize_approx"),
        format_sizes=_compute_format_sizes(d),
    )


def _best_thumb(d: dict[str, Any]) -> str:
    thumbs = d.get("thumbnails") or []
    if not thumbs:
        return d.get("thumbnail", "") or ""
    thumbs_sorted = sorted(
        [t for t in thumbs if t.get("url")],
        key=lambda t: (t.get("width") or 0) * (t.get("height") or 0),
    )
    return thumbs_sorted[-1]["url"] if thumbs_sorted else ""


def _cache_get(url: str, no_cookies: bool) -> FetchResult | None:
    key = (url, no_cookies)
    cached = _FETCH_CACHE.get(key)
    if not cached:
        return None
    ts, result = cached
    if (time.monotonic() - ts) > _FETCH_CACHE_TTL:
        _FETCH_CACHE.pop(key, None)
        return None
    return result


def _cache_put(url: str, no_cookies: bool, result: FetchResult) -> None:
    if len(_FETCH_CACHE) >= _FETCH_CACHE_MAX:
        # Drop the oldest entry
        oldest = min(_FETCH_CACHE, key=lambda k: _FETCH_CACHE[k][0])
        _FETCH_CACHE.pop(oldest, None)
    _FETCH_CACHE[(url, no_cookies)] = (time.monotonic(), result)


def clear_cache() -> None:
    """Clear the entire fetch cache. Called when auth settings change."""
    _FETCH_CACHE.clear()


def fetch(url: str, no_cookies: bool = False) -> FetchResult:
    """Detect & extract metadata. Single URL or playlist URL.

    ``no_cookies`` skips browser / file cookie loading — used by the auto-retry
    path when ``cookiesfrombrowser`` fails to decrypt.

    Results are memoized in-process for 5 minutes per (url, no_cookies) pair.

    Playlists use ``extract_flat=True`` so all entries come back in a single
    fetch with just basic info (id, title, duration, thumbnail). Full metadata
    for individual videos is fetched on demand when the user downloads.
    """
    cached = _cache_get(url, no_cookies)
    if cached is not None:
        return cached

    platform = detect(url)
    opts = _common_opts(no_cookies=no_cookies)
    opts["noplaylist"] = False

    if platform in ("tiktok", "instagram"):
        opts["noplaylist"] = True

    # Playlist detection: use flat extraction so a 200-item playlist comes back
    # in one round-trip instead of N+1.
    is_playlist = (
        platform == "youtube_playlist"
        or ("list=" in url and "v=" not in url)
    )
    if is_playlist:
        opts["extract_flat"] = True
        # Bound memory + UI cost for very large playlists.
        opts["playlist_items"] = "1-200"

    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except DownloadError as e:
            raise RuntimeError(_friendly_err(str(e))) from e

    if not info:
        raise RuntimeError("Could not extract any information from this URL.")

    entries = info.get("entries")
    if entries:
        plist = PlaylistInfo(
            id=info.get("id", ""),
            title=info.get("title", "Playlist"),
            uploader=info.get("uploader") or info.get("channel") or "",
            entries=[],
        )
        for e in entries:
            if not e:
                continue
            # Flat entry: just basic info. Construct a full watch URL so the
            # platform detector works.
            entry_url = _entry_url(e, url)
            plist.entries.append(_to_video_info(e, entry_url))
        result = FetchResult(kind="playlist", playlist=plist)
    else:
        result = FetchResult(
            kind="single",
            video=_to_video_info(info, info.get("webpage_url") or url),
        )
    _cache_put(url, no_cookies, result)
    return result


def _entry_url(entry: dict[str, Any], fallback: str) -> str:
    """Best-effort full URL for a flat playlist entry."""
    u = entry.get("webpage_url") or entry.get("url") or ""
    if u.startswith("http://") or u.startswith("https://"):
        return u
    # Only construct a YouTube watch URL if the entry is actually from YouTube.
    eid = entry.get("id")
    eurl_lower = (u or "").lower()
    is_yt = "youtube.com" in eurl_lower or "youtu.be" in eurl_lower
    if eid and len(eid) >= 6 and is_yt:
        return f"https://www.youtube.com/watch?v={eid}"
    return fallback


def thumbnail_cache_path(video_id: str) -> Path:
    cfg_dir = config.CONFIG_DIR
    return cfg_dir / "thumbs" / f"{video_id}.jpg"


_SAFE = re.compile(r"[^A-Za-z0-9._\- ]+")


def safe_filename(name: str, max_len: int = 120) -> str:
    s = _SAFE.sub("_", name).strip("._- ")
    return s[:max_len] or "untitled"


# --- Friendly error mapping ---
def _friendly_err(msg: str) -> str:
    m = msg.lower()
    if "private video" in m:
        return "This video is private."
    if "sign in" in m or "confirm your age" in m or "age-restricted" in m:
        return "Age-restricted. Try a different browser in Settings, or close the locked one."
    if "login required" in m or "log in to confirm" in m:
        return "Login required. Try a different browser in Settings."
    if "not available" in m or "geo" in m:
        return "Region-blocked or unavailable."
    if "http error 403" in m:
        return "Access denied (403). Try a different browser in Settings."
    if "unable to extract" in m:
        return "Could not parse this page. Site may not be supported."
    if "video unavailable" in m:
        return "Video unavailable."
    return msg.splitlines()[0][:200]
