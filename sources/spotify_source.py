import re


_OPEN_PLAYLIST_RE = re.compile(
    r"https://open\.spotify\.com/playlist/([A-Za-z0-9]+)"
)
_URI_PLAYLIST_RE = re.compile(
    r"spotify:playlist:([A-Za-z0-9]+)$"
)


def parse_playlist_id(url_or_uri):
    """Extract a Spotify playlist ID from a URL or URI.

    Accepted formats:
        https://open.spotify.com/playlist/{id}
        https://open.spotify.com/playlist/{id}?si=...
        spotify:playlist:{id}

    Raises ValueError for anything else (tracks, albums, garbage, empty).
    """
    if not url_or_uri or not url_or_uri.strip():
        raise ValueError("Empty input: expected a Spotify playlist URL or URI.")

    value = url_or_uri.strip()

    m = _OPEN_PLAYLIST_RE.match(value)
    if m:
        return m.group(1)

    m = _URI_PLAYLIST_RE.match(value)
    if m:
        return m.group(1)

    if "spotify.com" in value or value.startswith("spotify:"):
        raise ValueError(
            f"Not a playlist URL or URI: {value!r}. "
            "Only playlist links are accepted."
        )

    raise ValueError(
        f"Unrecognised format: {value!r}. "
        "Expected https://open.spotify.com/playlist/... "
        "or spotify:playlist:..."
    )
