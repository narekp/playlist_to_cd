"""Tests for sources.spotify_source.parse_playlist_id.

Phase 1c-i: URL/URI parsing only. No auth, no network.
"""

import pytest

from sources.spotify_source import parse_playlist_id

PLAYLIST_ID = "4zq02HbIOeYLjbchtbgEGx"


# --- accepted: HTTPS URL ---


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


# --- accepted: URI ---


def test_spotify_uri():
    uri = f"spotify:playlist:{PLAYLIST_ID}"
    assert parse_playlist_id(uri) == PLAYLIST_ID


def test_spotify_uri_strips_surrounding_whitespace():
    uri = f"  spotify:playlist:{PLAYLIST_ID}  "
    assert parse_playlist_id(uri) == PLAYLIST_ID


# --- rejected: non-playlist Spotify URLs ---


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


# --- rejected: garbage and empty ---


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
