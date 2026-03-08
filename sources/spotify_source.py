import os
import re


_OPEN_PLAYLIST_RE = re.compile(
    r"https://open\.spotify\.com/playlist/([A-Za-z0-9]+)"
)
_URI_PLAYLIST_RE = re.compile(
    r"spotify:playlist:([A-Za-z0-9]+)$"
)

_SCOPES = "playlist-read-private playlist-read-collaborative"
TOKEN_CACHE_PATH = ".spotify_token_cache"
DEFAULT_REDIRECT_URI = "http://localhost:8888/callback"
_PAGE_LIMIT = 50


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


def _get_client():
    """Return an authenticated Spotify client using PKCE.

    Reads SPOTIFY_CLIENT_ID (required) and SPOTIFY_REDIRECT_URI (optional)
    from the environment. On first call, opens the browser for login and
    caches the token to TOKEN_CACHE_PATH. Subsequent calls reuse the cache.

    Raises:
        ValueError: if SPOTIFY_CLIENT_ID is not set.
        ImportError: if spotipy is not installed.
    """
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    if not client_id:
        raise ValueError(
            "SPOTIFY_CLIENT_ID environment variable is not set. "
            "Register a Spotify app at https://developer.spotify.com/dashboard "
            "and add SPOTIFY_CLIENT_ID to your environment."
        )

    try:
        import spotipy
        from spotipy.oauth2 import SpotifyPKCE
    except ImportError as exc:
        raise ImportError(
            "spotipy is required for Spotify import. "
            "Install it with: pip install spotipy"
        ) from exc

    redirect_uri = os.environ.get("SPOTIFY_REDIRECT_URI", DEFAULT_REDIRECT_URI)
    auth_manager = SpotifyPKCE(
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=_SCOPES,
        cache_path=TOKEN_CACHE_PATH,
    )
    return spotipy.Spotify(auth_manager=auth_manager)


def _normalize_item(item):
    """Convert one Spotify playlist item dict to the normalized track dict.

    Returns None for local files and removed tracks (track is None).
    """
    if item.get("is_local", False):
        return None
    track = item.get("track")
    if track is None:
        return None

    artists = "; ".join(a["name"] for a in track.get("artists", []))
    return {
        "Track Name": track.get("name", ""),
        "Artist Name(s)": artists,
        "Album Name": (track.get("album") or {}).get("name", ""),
        "Duration (ms)": str(track.get("duration_ms", 0)),
        "ISRC": (track.get("external_ids") or {}).get("isrc", ""),
        "Track URI": track.get("uri", ""),
    }


def load_tracks_from_spotify(playlist_url):
    """Fetch all tracks from a Spotify playlist and return normalized track dicts.

    Each returned dict has the keys expected by downstream helpers:
        Track Name, Artist Name(s), Album Name, Duration (ms), ISRC, Track URI

    Local files and removed tracks (null track objects) are silently skipped.

    Raises:
        ValueError: if playlist_url is not a valid playlist URL or URI.
        ValueError: if SPOTIFY_CLIENT_ID is not set in the environment.
        ImportError: if spotipy is not installed.
    """
    playlist_id = parse_playlist_id(playlist_url)
    sp = _get_client()

    tracks = []
    offset = 0

    while True:
        response = sp.playlist_tracks(playlist_id, limit=_PAGE_LIMIT, offset=offset)
        for item in response.get("items", []):
            normalized = _normalize_item(item)
            if normalized is not None:
                tracks.append(normalized)

        if response.get("next") is None:
            break
        offset += _PAGE_LIMIT

    return tracks
