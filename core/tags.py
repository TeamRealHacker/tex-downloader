"""ID3 tags + cover art for MP3."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:  # requests is bundled with yt-dlp
    requests = None  # type: ignore

try:
    from mutagen.id3 import ID3, ID3NoHeaderError, APIC, TIT2, TPE1, TALB, TYER  # type: ignore
    from mutagen.mp3 import MP3  # type: ignore
    _HAS_MUTAGEN = True
except Exception:  # pragma: no cover
    _HAS_MUTAGEN = False


def tag_mp3(
    path: Path,
    *,
    title: str,
    artist: str = "",
    album: str = "",
    year: str = "",
    cover_url: str = "",
    cover_bytes: Optional[bytes] = None,
) -> None:
    if not _HAS_MUTAGEN:
        return
    try:
        try:
            audio = MP3(str(path), ID3=ID3)
        except ID3NoHeaderError:
            audio = MP3(str(path))
            audio.add_tags()

        # Remove existing frames we'll overwrite
        for k in ("TIT2", "TPE1", "TALB", "TYER"):
            if k in audio.tags:
                del audio.tags[k]
        if "APIC:" in audio.tags:
            del audio.tags["APIC:"]

        audio.tags.add(TIT2(encoding=3, text=title or ""))
        if artist:
            audio.tags.add(TPE1(encoding=3, text=artist))
        if album:
            audio.tags.add(TALB(encoding=3, text=album))
        if year:
            audio.tags.add(TYER(encoding=3, text=year))

        # Cover
        img = cover_bytes
        if not img and cover_url and requests is not None:
            try:
                r = requests.get(cover_url, timeout=10)
                if r.status_code == 200 and r.content:
                    img = r.content
            except Exception:
                img = None
        if img:
            # Detect actual MIME type from the image bytes header.
            _MIME_MAP = {
                b"\x89PNG": "image/png",
                b"GIF8": "image/gif",
                b"RIFF": "image/webp",  # RIFF....WEBP
            }
            mime = "image/jpeg"  # default fallback
            for magic, m in _MIME_MAP.items():
                if img[:8].startswith(magic) or magic in img[:12]:
                    mime = m
                    break
            audio.tags.add(APIC(
                encoding=3, mime=mime, type=3, desc="cover",
                data=img,
            ))

        audio.save()
    except Exception:
        pass
