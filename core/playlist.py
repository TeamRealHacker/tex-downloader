"""Playlist utilities: current-video detection."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .detector import youtube_playlist_id, youtube_video_id


@dataclass
class ParsedPlaylist:
    playlist_id: str | None
    current_video_id: str | None
    url: str
    is_playlist: bool
    is_single_in_playlist: bool  # URL has both list= and v=


def parse(url: str) -> ParsedPlaylist:
    pid = youtube_playlist_id(url)
    vid = youtube_video_id(url)
    is_pl = pid is not None
    is_single_in_pl = bool(pid and vid)
    return ParsedPlaylist(
        playlist_id=pid,
        current_video_id=vid,
        url=url,
        is_playlist=is_pl,
        is_single_in_playlist=is_single_in_pl,
    )


def precheck_ids(entries: list, current_video_id: str | None) -> set[str]:
    """Return set of entry ids to pre-tick (default: only the currently-watched video)."""
    if not current_video_id:
        return set()
    return {current_video_id}
