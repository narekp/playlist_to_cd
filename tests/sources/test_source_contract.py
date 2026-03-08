"""Contract tests: any source's output dicts must work with downstream helpers.

These tests verify that CSV-sourced rows and any dict with the expected shape
are compatible with make_track_key() and get_duration_ms() from core.artists.
"""

import os

from core.artists import make_track_key, get_duration_ms
from sources.csv_source import load_tracks_from_csv

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "manual", "input_csv")
DUMMY_CSV = os.path.join(FIXTURE_DIR, "dummy_small.csv")


# --- CSV-sourced rows ---


def test_csv_row_works_with_make_track_key():
    valid, _ = load_tracks_from_csv(DUMMY_CSV)
    key = make_track_key(valid[0])
    assert "Jack Johnson" in key
    assert "Open Mind" in key
    assert "Meet The Moonlight" in key
    assert "213586" in key


def test_csv_row_works_with_get_duration_ms():
    valid, _ = load_tracks_from_csv(DUMMY_CSV)
    assert get_duration_ms(valid[0]) == "213586"


# --- Dict shape contract (any source producing this shape works with core) ---


def test_dict_with_expected_keys_works_with_make_track_key():
    row = {
        "Track Name": "Open Mind",
        "Artist Name(s)": "Jack Johnson",
        "Album Name": "Meet The Moonlight",
        "Duration (ms)": "213586",
    }
    key = make_track_key(row)
    assert "Jack Johnson" in key
    assert "Open Mind" in key
    assert "Meet The Moonlight" in key
    assert "213586" in key


def test_dict_with_expected_keys_works_with_get_duration_ms():
    row = {
        "Track Name": "Open Mind",
        "Artist Name(s)": "Jack Johnson",
        "Album Name": "Meet The Moonlight",
        "Duration (ms)": "213586",
    }
    assert get_duration_ms(row) == "213586"


def test_multi_artist_row_works_with_make_track_key():
    row = {
        "Track Name": "Some Song",
        "Artist Name(s)": "Artist A; Artist B; Artist C",
        "Album Name": "Album X",
        "Duration (ms)": "180000",
    }
    key = make_track_key(row)
    assert "Artist A; Artist B; Artist C" in key
    assert "Some Song" in key
    assert "180000" in key
