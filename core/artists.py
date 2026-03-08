def make_track_key(row):
    artist = (row.get("Artist Name(s)", "") or "").strip()
    track = (row.get("Track Name", "") or "").strip()
    album = (row.get("Album Name", "") or "").strip()
    duration = get_duration_ms(row)
    return f"{artist}||{track}||{album}||{duration}"


def split_artists(artist_text):
    artist_text = (artist_text or "").strip()
    if not artist_text:
        return []
    if ";" in artist_text:
        parts = [a.strip() for a in artist_text.split(";") if a.strip()]
    else:
        parts = [a.strip() for a in artist_text.split(",") if a.strip()]
    return parts


def get_duration_ms(row):
    """Return the duration string from common CSV field names."""
    for key in ["Track Duration (ms)", "Duration (ms)",
                "\ufeffTrack Duration (ms)", "\ufeffDuration (ms)"]:
        val = row.get(key)
        if val is not None and val.strip() != "":
            return val.strip()
    return ""

