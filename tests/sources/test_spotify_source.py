"""Tests for sources.spotify_source.

Phase 1c-i: parse_playlist_id -- URL/URI parsing only. No auth, no network.
Phase 1c-ii: load_tracks_from_spotify -- mocked API responses. No auth, no network,
             no spotipy required (all tests that call the API mock _get_client).
"""

from unittest.mock import MagicMock, call, patch

import pytest

from sources.spotify_source import load_tracks_from_spotify, parse_playlist_id

PLAYLIST_ID = "4zq02HbIOeYLjbchtbgEGx"
PLAYLIST_URL = f"https://open.spotify.com/playlist/{PLAYLIST_ID}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_item(name, artists, album, duration_ms, isrc="", uri=""):
    """Build a mock Spotify playlist track item (is_local=False, track present)."""
    return {
        "is_local": False,
        "track": {
            "name": name,
            "artists": [{"name": a} for a in artists],
            "album": {"name": album},
            "duration_ms": duration_ms,
            "external_ids": {"isrc": isrc} if isrc else {},
            "uri": uri,
        },
    }


def _make_null_item():
    """Item whose track has been removed from Spotify."""
    return {"is_local": False, "track": None}


def _make_local_item():
    """Item representing a local file added to the playlist."""
    return {"is_local": True, "track": None}


@pytest.fixture
def mock_client(monkeypatch):
    """Patch _get_client to return a MagicMock Spotify client."""
    client = MagicMock()
    monkeypatch.setattr("sources.spotify_source._get_client", lambda: client)
    return client


# ---------------------------------------------------------------------------
# Phase 1c-i: parse_playlist_id
# ---------------------------------------------------------------------------


def test_https_url_bare():
    url = f"https://open.spotify.com/playlist/{PLAYLIST_ID}"
    assert parse_playlist_id(url) == PLAYLIST_ID


def test_https_url_with_si_param():
    url = f"https://open.spotify.com/playlist/{PLAYLIST_ID}?si=7fd2dd510bc04e00"
    assert parse_playlist_id(url) == PLAYLIST_ID


def test_https_url_with_multiple_query_params():
    url = f"https://open.spotify.com/playlist/{PLAYLIST_ID}?si=abc&nd=1"
    assert parse_playlist_id(url) == PLAYLIST_ID


def test_https_url_strips_surrounding_whitespace():
    url = f"  https://open.spotify.com/playlist/{PLAYLIST_ID}  "
    assert parse_playlist_id(url) == PLAYLIST_ID


def test_spotify_uri():
    uri = f"spotify:playlist:{PLAYLIST_ID}"
    assert parse_playlist_id(uri) == PLAYLIST_ID


def test_spotify_uri_strips_surrounding_whitespace():
    uri = f"  spotify:playlist:{PLAYLIST_ID}  "
    assert parse_playlist_id(uri) == PLAYLIST_ID


def test_rejects_track_url():
    with pytest.raises(ValueError, match="playlist"):
        parse_playlist_id("https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh")


def test_rejects_album_url():
    with pytest.raises(ValueError, match="playlist"):
        parse_playlist_id("https://open.spotify.com/album/1DFixLWuPkv3KT3TnV35m3")


def test_rejects_artist_url():
    with pytest.raises(ValueError, match="playlist"):
        parse_playlist_id("https://open.spotify.com/artist/0TnOYISbd1XYRBk9myaseg")


def test_rejects_track_uri():
    with pytest.raises(ValueError, match="playlist"):
        parse_playlist_id("spotify:track:4iV5W9uYEdYUVa79Axb7Rh")


def test_rejects_album_uri():
    with pytest.raises(ValueError, match="playlist"):
        parse_playlist_id("spotify:album:1DFixLWuPkv3KT3TnV35m3")


def test_rejects_empty_string():
    with pytest.raises(ValueError):
        parse_playlist_id("")


def test_rejects_whitespace_only():
    with pytest.raises(ValueError):
        parse_playlist_id("   ")


def test_rejects_none():
    with pytest.raises((ValueError, AttributeError)):
        parse_playlist_id(None)


def test_rejects_arbitrary_url():
    with pytest.raises(ValueError):
        parse_playlist_id("https://example.com/playlist/abc")


def test_rejects_plain_id_string():
    with pytest.raises(ValueError):
        parse_playlist_id(PLAYLIST_ID)


def test_rejects_exportify_url():
    with pytest.raises(ValueError):
        parse_playlist_id(
            f"https://exportify.net/?playlist={PLAYLIST_ID}"
        )


# ---------------------------------------------------------------------------
# Phase 1c-ii: load_tracks_from_spotify -- field mapping
# ---------------------------------------------------------------------------


def test_returns_normalized_dicts(mock_client):
    mock_client.playlist_tracks.return_value = {
        "items": [
            _make_item(
                "Open Mind",
                ["Jack Johnson"],
                "Meet The Moonlight",
                213586,
                isrc="USUB12200187",
                uri="spotify:track:623UQ72wx42BkxaNAXQVGT",
            )
        ],
        "next": None,
    }
    tracks = load_tracks_from_spotify(PLAYLIST_URL)

    assert len(tracks) == 1
    t = tracks[0]
    assert t["Track Name"] == "Open Mind"
    assert t["Artist Name(s)"] == "Jack Johnson"
    assert t["Album Name"] == "Meet The Moonlight"
    assert t["Duration (ms)"] == "213586"
    assert t["ISRC"] == "USUB12200187"
    assert t["Track URI"] == "spotify:track:623UQ72wx42BkxaNAXQVGT"


def test_duration_ms_is_string(mock_client):
    # Spotify API returns duration_ms as int; contract requires string.
    mock_client.playlist_tracks.return_value = {
        "items": [_make_item("Song", ["Artist"], "Album", 180000)],
        "next": None,
    }
    tracks = load_tracks_from_spotify(PLAYLIST_URL)
    assert tracks[0]["Duration (ms)"] == "180000"
    assert isinstance(tracks[0]["Duration (ms)"], str)


def test_multi_artist_joined_with_semicolon(mock_client):
    mock_client.playlist_tracks.return_value = {
        "items": [
            _make_item("Collab", ["Artist A", "Artist B", "Artist C"], "Album", 200000)
        ],
        "next": None,
    }
    tracks = load_tracks_from_spotify(PLAYLIST_URL)
    assert tracks[0]["Artist Name(s)"] == "Artist A; Artist B; Artist C"


def test_missing_isrc_is_empty_string(mock_client):
    mock_client.playlist_tracks.return_value = {
        "items": [_make_item("Song", ["Artist"], "Album", 200000, isrc="")],
        "next": None,
    }
    tracks = load_tracks_from_spotify(PLAYLIST_URL)
    assert tracks[0]["ISRC"] == ""


def test_all_contract_keys_present(mock_client):
    mock_client.playlist_tracks.return_value = {
        "items": [_make_item("Song", ["Artist"], "Album", 180000)],
        "next": None,
    }
    tracks = load_tracks_from_spotify(PLAYLIST_URL)
    for key in ("Track Name", "Artist Name(s)", "Album Name", "Duration (ms)", "ISRC", "Track URI"):
        assert key in tracks[0], f"missing key: {key}"


# ---------------------------------------------------------------------------
# Phase 1c-ii: load_tracks_from_spotify -- pagination
# ---------------------------------------------------------------------------


def test_single_page_no_next(mock_client):
    items = [_make_item(f"Song {i}", ["Artist"], "Album", 180000) for i in range(3)]
    mock_client.playlist_tracks.return_value = {"items": items, "next": None}

    tracks = load_tracks_from_spotify(PLAYLIST_URL)

    assert len(tracks) == 3
    mock_client.playlist_tracks.assert_called_once_with(
        PLAYLIST_ID, limit=50, offset=0
    )


def test_two_pages_fetches_all_tracks(mock_client):
    page1 = [_make_item(f"Song {i}", ["Artist"], "Album", 180000) for i in range(3)]
    page2 = [_make_item(f"Song {i}", ["Artist"], "Album", 180000) for i in range(3, 5)]
    mock_client.playlist_tracks.side_effect = [
        {"items": page1, "next": "https://api.spotify.com/v1/playlists/.../tracks?offset=50"},
        {"items": page2, "next": None},
    ]

    tracks = load_tracks_from_spotify(PLAYLIST_URL)

    assert len(tracks) == 5
    assert mock_client.playlist_tracks.call_count == 2
    assert mock_client.playlist_tracks.call_args_list == [
        call(PLAYLIST_ID, limit=50, offset=0),
        call(PLAYLIST_ID, limit=50, offset=50),
    ]


def test_empty_playlist_returns_empty_list(mock_client):
    mock_client.playlist_tracks.return_value = {"items": [], "next": None}
    assert load_tracks_from_spotify(PLAYLIST_URL) == []


# ---------------------------------------------------------------------------
# Phase 1c-ii: load_tracks_from_spotify -- null / local filtering
# ---------------------------------------------------------------------------


def test_null_track_items_are_skipped(mock_client):
    mock_client.playlist_tracks.return_value = {
        "items": [
            _make_null_item(),
            _make_item("Real Song", ["Artist"], "Album", 180000),
            _make_null_item(),
        ],
        "next": None,
    }
    tracks = load_tracks_from_spotify(PLAYLIST_URL)
    assert len(tracks) == 1
    assert tracks[0]["Track Name"] == "Real Song"


def test_local_file_items_are_skipped(mock_client):
    mock_client.playlist_tracks.return_value = {
        "items": [
            _make_local_item(),
            _make_item("Real Song", ["Artist"], "Album", 180000),
        ],
        "next": None,
    }
    tracks = load_tracks_from_spotify(PLAYLIST_URL)
    assert len(tracks) == 1
    assert tracks[0]["Track Name"] == "Real Song"


def test_mixed_items_returns_only_valid_tracks(mock_client):
    mock_client.playlist_tracks.return_value = {
        "items": [
            _make_null_item(),
            _make_local_item(),
            _make_item("Track A", ["Artist"], "Album", 180000),
            _make_null_item(),
            _make_item("Track B", ["Artist"], "Album", 200000),
        ],
        "next": None,
    }
    tracks = load_tracks_from_spotify(PLAYLIST_URL)
    assert len(tracks) == 2
    assert tracks[0]["Track Name"] == "Track A"
    assert tracks[1]["Track Name"] == "Track B"


# ---------------------------------------------------------------------------
# Phase 1c-ii: load_tracks_from_spotify -- error paths (no mock on _get_client)
# ---------------------------------------------------------------------------


def test_missing_client_id_raises_value_error(monkeypatch):
    # _get_client() checks env var before importing spotipy, so this works
    # even without spotipy installed.
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
    with pytest.raises(ValueError, match="SPOTIFY_CLIENT_ID"):
        load_tracks_from_spotify(PLAYLIST_URL)


def test_invalid_url_raises_value_error():
    # parse_playlist_id() raises before _get_client() is ever called.
    with pytest.raises(ValueError):
        load_tracks_from_spotify("https://example.com/not-a-playlist")
