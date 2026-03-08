"""Tests for core.artists."""
import pytest

from core.artists import get_duration_ms, make_track_key, split_artists


class TestSplitArtists:
    def test_empty(self):
        assert split_artists("") == []
        assert split_artists(None) == []
        assert split_artists("   ") == []

    def test_semicolon_separated(self):
        assert split_artists("A; B; C") == ["A", "B", "C"]
        assert split_artists("Artist1;Artist2") == ["Artist1", "Artist2"]

    def test_comma_separated(self):
        assert split_artists("A, B, C") == ["A", "B", "C"]
        assert split_artists("Artist1, Artist2") == ["Artist1", "Artist2"]

    def test_single_artist(self):
        assert split_artists("Jack Johnson") == ["Jack Johnson"]

    def test_strips_whitespace(self):
        # Comma-separated: strips outer and splits by comma
        assert split_artists("  A , B , C  ") == ["A", "B", "C"]
        # Semicolon takes precedence when present
        assert split_artists("A ; B ; C") == ["A", "B", "C"]


class TestGetDurationMs:
    def test_track_duration_ms(self):
        row = {"Track Duration (ms)": " 123456 "}
        assert get_duration_ms(row) == "123456"

    def test_duration_ms(self):
        row = {"Duration (ms)": "999"}
        assert get_duration_ms(row) == "999"

    def test_bom_prefixed_key(self):
        row = {"\ufeffTrack Duration (ms)": "500"}
        assert get_duration_ms(row) == "500"

    def test_first_match_wins(self):
        row = {
            "Track Duration (ms)": "100",
            "Duration (ms)": "200",
        }
        assert get_duration_ms(row) == "100"

    def test_missing_returns_empty(self):
        assert get_duration_ms({}) == ""
        assert get_duration_ms({"other": "x"}) == ""

    def test_empty_value_skipped(self):
        row = {"Track Duration (ms)": "  "}
        assert get_duration_ms(row) == ""


class TestMakeTrackKey:
    def test_full_row(self):
        row = {
            "Artist Name(s)": "Jack Johnson",
            "Track Name": "Banana Pancakes",
            "Album Name": "In Between Dreams",
            "Track Duration (ms)": "180000",
        }
        assert make_track_key(row) == "Jack Johnson||Banana Pancakes||In Between Dreams||180000"

    def test_partial_row(self):
        row = {"Artist Name(s)": "A", "Track Name": "T"}
        assert "||" in make_track_key(row)
        assert make_track_key(row).startswith("A||T||")

    def test_empty_values(self):
        row = {}
        # artist||track||album||duration with all empty
        assert make_track_key(row) == "||||||"
