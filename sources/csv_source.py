import csv


def load_tracks_from_csv(csv_path):
    """Load tracks from an Exportify-style CSV file.

    Returns (valid_tracks, invalid_rows).  A row is invalid when both
    Track Name and Artist Name(s) are empty or missing.
    """
    with open(csv_path, newline="", encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))

    valid = []
    invalid = []
    for row in all_rows:
        track_name = (row.get("Track Name", "") or "").strip()
        artist_name = (row.get("Artist Name(s)", "") or "").strip()
        if not track_name and not artist_name:
            invalid.append(row)
        else:
            valid.append(row)

    return valid, invalid
