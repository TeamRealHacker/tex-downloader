"""Channel bulk fetcher — list videos from a YouTube/TikTok/Instagram channel.

Uses ``extract_flat=True`` so a 50-video channel comes back in a single
yt-dlp call (no per-video metadata round-trip).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yt_dlp
from yt_dlp.utils import DownloadError

from . import config
from .detector import Platform, detect
from .metadata import _friendly_err, ffmpeg_location


@dataclass
class ChannelInfo:
    id: str
    title: str
    uploader: str
    url: str
    platform: Platform
    entries: list = field(default_factory=list)
    truncated: bool = False  # True when more videos existed but were capped
    avatar: str = ""  # channel avatar URL (used in the panel header)


def _safe_folder(name: str, max_len: int = 80) -> str:
    import re
    s = re.sub(r"[^\w\s.\-]+", "_", name).strip("._- ")
    return s[:max_len] or "channel"


def _channel_dir(channel: ChannelInfo) -> str:
    """Return the save directory for this channel's downloads.

    Sits at ``{save_dir}/Channels/{sanitized_name}``. We can't use
    ``ensure_save_subdir`` here because that helper only knows the
    ``video`` / ``audio`` subdirs and falls back to ``Audio`` for any
    unknown key — which is exactly what was putting channel folders
    inside the user's audio directory.
    """
    base = Path(config.get("save_dir", str(Path.home() / "Downloads" / "Tex")))
    out = base / "Channels" / _safe_folder(channel.title or channel.uploader or "channel")
    out.mkdir(parents=True, exist_ok=True)
    return str(out)


def _to_video_entry(e: dict[str, Any], fallback_url: str) -> dict:
    """Normalize a flat entry to the fields the UI cares about."""
    eid = e.get("id", "")
    eurl = e.get("webpage_url") or e.get("url") or ""
    if not eurl.startswith("http"):
        # YouTube flat entries often have a bare id — build the watch URL.
        if eid:
            eurl = f"https://www.youtube.com/watch?v={eid}"
        else:
            eurl = fallback_url
    # Thumbnail: prefer yt-dlp's list, but for YouTube a flat extraction
    # sometimes only carries the channel's avatar. Use the public, stable
    # ``i.ytimg.com/vi/<id>/hqdefault.jpg`` as a guaranteed fallback.
    thumb = ""
    thumbs = e.get("thumbnails") or []
    is_yt = "youtube.com" in eurl or "youtu.be" in eurl
    for t in thumbs:
        u = (t.get("url") or "").strip()
        if not u:
            continue
        # Skip anything pointing at the channel's avatar / banner.
        if "googleusercontent.com" in u:
            continue
        thumb = u
        break
    if not thumb and is_yt and eid:
        thumb = f"https://i.ytimg.com/vi/{eid}/hqdefault.jpg"
    if not thumb and thumbs:
        thumb = thumbs[-1].get("url", "") or thumbs[0].get("url", "")
    return {
        "id": eid,
        "title": (e.get("title") or "Untitled")[:200],
        "uploader": e.get("uploader") or e.get("channel") or "",
        "duration": int(e.get("duration") or 0),
        "thumbnail": thumb,
        "url": eurl,
        "webpage_url": eurl,
    }


def _filter_short(entry: dict, want: str) -> bool:
    """True if the entry should be kept given the user's filter."""
    if want == "all":
        return True
    eurl = (entry.get("url") or entry.get("webpage_url") or "").lower()
    # Detect short-form content across platforms.
    is_short = (
        "/shorts/" in eurl                           # YouTube Shorts
        or "/reel" in eurl                            # Instagram Reels
    )
    if want == "shorts":
        return is_short
    if want == "videos":
        return not is_short
    return True


def fetch_channel(url: str, content_type: str = "videos",
                  max_count: int = 10) -> ChannelInfo:
    """List videos from a channel.

    ``content_type``: ``"videos"`` | ``"shorts"`` | ``"all"``
    ``max_count``:    1..N (capped at 200 to keep memory + UI sane).
    """
    max_count = max(1, min(200, int(max_count)))
    platform = detect(url)
    target_url = url.rstrip("/")

    # YouTube: append the tab path so yt-dlp lists the right kind.
    if platform == "youtube" and content_type in ("videos", "shorts"):
        # Strip any existing tab suffix and re-append.
        for tail in ("/videos", "/shorts", "/streams", "/featured", "/community"):
            if target_url.endswith(tail):
                target_url = target_url[: -len(tail)]
                break
        target_url = f"{target_url}/{content_type}"

    cfg = config.load()
    opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "no_color": True,
        "noprogress": True,
        "skip_download": True,
        "extract_flat": True,
        "noplaylist": False,
        "playlist_items": f"1-{max_count}",
    }
    if platform in ("tiktok", "instagram"):
        opts["noplaylist"] = True
    ffm = ffmpeg_location()
    if ffm:
        opts["ffmpeg_location"] = ffm
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

    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            info = ydl.extract_info(target_url, download=False)
        except DownloadError as e:
            raise RuntimeError(_friendly_err(str(e))) from e

    if not info:
        raise RuntimeError("Could not read this channel.")

    raw_entries = info.get("entries") or []
    entries: list[dict] = []
    for e in raw_entries:
        if not e:
            continue
        norm = _to_video_entry(e, target_url)
        if not _filter_short(norm, content_type):
            continue
        entries.append(norm)
        if len(entries) >= max_count:
            break

    return ChannelInfo(
        id=info.get("id", "") or info.get("channel_id", ""),
        title=info.get("title", "Channel"),
        uploader=info.get("uploader") or info.get("channel") or info.get("title", ""),
        url=target_url,
        platform=platform,
        entries=entries,
        truncated=len(raw_entries) > len(entries),
        avatar=info.get("thumbnail", "") or "",
    )

