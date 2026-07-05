"""Format selection: MP4 6 rungs + MP3 3 bitrates."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QualityOption:
    key: str          # "2160p" | "1080p" | "320"
    label: str        # "2160p (4K)"
    kind: str         # "video" | "audio"
    format_str: str   # yt-dlp format selector
    extra: dict | None = None


VIDEO_RUNG_HEIGHT = 2160


def _video_prefer_mp4(height: int) -> str:
    # Prefer MP4 container, but fall back to any container if MP4 is
    # unavailable (important for Twitter/X, Instagram, etc. that often
    # only provide webm). yt-dlp's merge_output_format handles remuxing.
    return (
        f"bv*[height<={height}][ext=mp4]+ba[ext=m4a]"
        f"/b[height<={height}][ext=mp4]"
        f"/bv*[height<={height}]+ba"
        f"/b[height<={height}]"
    )


MP4_QUALITIES: list[QualityOption] = [
    QualityOption("2160p", "2160p · 4K", "video", _video_prefer_mp4(2160)),
    QualityOption("1440p", "1440p · 2K", "video", _video_prefer_mp4(1440)),
    QualityOption("1080p", "1080p · FULL HD", "video", _video_prefer_mp4(1080)),
    QualityOption("720p",  "720p · HD", "video", _video_prefer_mp4(720)),
    QualityOption("480p",  "480p", "video", _video_prefer_mp4(480)),
    QualityOption("360p",  "360p", "video", _video_prefer_mp4(360)),
]

MP3_QUALITIES: list[QualityOption] = [
    QualityOption("320", "MP3 · 320 kbps", "audio", "bestaudio/best",
                  {"preferredquality": "320"}),
    QualityOption("192", "MP3 · 192 kbps", "audio", "bestaudio/best",
                  {"preferredquality": "192"}),
    QualityOption("128", "MP3 · 128 kbps", "audio", "bestaudio/best",
                  {"preferredquality": "128"}),
]


def all_qualities() -> list[QualityOption]:
    return MP4_QUALITIES + MP3_QUALITIES


def find_by_key(key: str) -> QualityOption | None:
    for q in all_qualities():
        if q.key == key:
            return q
    return None
