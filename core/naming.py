import re

from .artists import split_artists


def safe_name(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:180] if value else "unknown"


def format_artists_for_filename(artist_text):
    artists = split_artists(artist_text)
    return ", ".join(artists) if artists else "Unknown"


def format_artists_for_metadata(artist_text):
    artists = split_artists(artist_text)
    if not artists:
        return "Unknown"
    return ", ".join(artists[:2])

