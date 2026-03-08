"""Tests for sources.csv_source – CSV track loading."""

import csv
import os

from sources.csv_source import load_tracks_from_csv

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "manual", "input_csv")
DUMMY_CSV = os.path.join(FIXTURE_DIR, "dummy_small.csv")


# --- happy path ---


def test_loads_all_valid_tracks():
    valid, invalid = load_tracks_from_csv(DUMMY_CSV)
    assert len(valid) == 4
    assert len(invalid) == 0


def test_track_dict_has_expected_keys():
    valid, _ = load_tracks_from_csv(DUMMY_CSV)
    row = valid[0]
    for key in ("Track Name", "Artist Name(s)", "Album Name", "Duration (ms)"):
        assert key in row, f"missing key: {key}"


def test_track_values_match_fixture():
    valid, _ = load_tracks_from_csv(DUMMY_CSV)
    first = valid[0]
    assert first["Track Name"] == "Open Mind"
    assert first["Artist Name(s)"] == "Jack Johnson"
    assert first["Album Name"] == "Meet The Moonlight"
    assert first["Duration (ms)"] == "213586"


# --- filtering ---


def test_filters_invalid_rows(tmp_path):
    csv_path = tmp_path / "mixed.csv"
    fieldnames = ["Track Name", "Artist Name(s)", "Album Name", "Duration (ms)"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow({
            "Track Name": "Good Song",
            "Artist Name(s)": "Artist",
            "Album Name": "Album",
            "Duration (ms)": "200000",
        })
        writer.writerow({
            "Track Name": "",
            "Artist Name(s)": "",
            "Album Name": "Orphan Album",
            "Duration (ms)": "100000",
        })

    valid, invalid = load_tracks_from_csv(str(csv_path))
    assert len(valid) == 1
    assert len(invalid) == 1
    assert valid[0]["Track Name"] == "Good Song"
    assert invalid[0]["Album Name"] == "Orphan Album"


def test_row_with_only_track_name_is_valid(tmp_path):
    csv_path = tmp_path / "track_only.csv"
    fieldnames = ["Track Name", "Artist Name(s)"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow({"Track Name": "Solo", "Artist Name(s)": ""})

    valid, invalid = load_tracks_from_csv(str(csv_path))
    assert len(valid) == 1
    assert len(invalid) == 0


def test_row_with_only_artist_is_valid(tmp_path):
    csv_path = tmp_path / "artist_only.csv"
    fieldnames = ["Track Name", "Artist Name(s)"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow({"Track Name": "", "Artist Name(s)": "Someone"})

    valid, invalid = load_tracks_from_csv(str(csv_path))
    assert len(valid) == 1
    assert len(invalid) == 0


def test_empty_csv_returns_empty_lists(tmp_path):
    csv_path = tmp_path / "empty.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Track Name", "Artist Name(s)"])
        writer.writeheader()

    valid, invalid = load_tracks_from_csv(str(csv_path))
    assert valid == []
    assert invalid == []
