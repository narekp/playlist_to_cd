# Architecture

## Module structure

```
playlist_to_cd/
├── main.py                 # CLI entry point (post-processing only)
├── main_original.py        # Legacy monolith (full GUI workflow)
├── core/
│   ├── artists.py          # Artist parsing, track keys, duration extraction
│   ├── constants.py        # Shared operational values for MP3 CD and Audio CD processing
│   ├── naming.py           # Safe filenames, artist formatting
│   ├── query.py            # YouTube search query variant building
│   └── ffmpeg_utils.py     # ffmpeg/ffprobe wrappers (convert, metadata, renumber, verify)
├── modes/
│   ├── mp3_cd.py           # MP3 CD pipeline (bitrate reduction to ~700 MB, metadata, renumbering)
│   └── audio_cd.py         # Audio CD pipeline (MP3 -> 44.1 kHz stereo WAV)
└── tests/
    ├── conftest.py          # Shared fixtures (stop_flag, log_queue)
    ├── test_artists.py
    ├── test_naming.py
    ├── test_query.py
    ├── test_ffmpeg_utils_unit.py
    ├── test_main.py
    └── modes/
        ├── test_mp3_cd.py
        └── test_audio_cd.py
```

## Dependency graph

```
main.py ──────────────┐
                      ├──> modes/mp3_cd.py ──> core/ffmpeg_utils.py ──> core/naming.py ──> core/artists.py
                      └──> modes/audio_cd.py ──> core/naming.py ──> core/artists.py

main_original.py ─────┬──> core/artists.py
                      ├──> core/naming.py
                      ├──> core/query.py ──> core/artists.py, core/naming.py
                      ├──> core/ffmpeg_utils.py
                      ├──> modes/mp3_cd.py
                      └──> modes/audio_cd.py
```

## main_original.py vs main.py

**`main_original.py`** is the original monolith. It is the Tkinter desktop application that handles the entire workflow: CSV parsing, YouTube search/download via yt-dlp, duration validation, resume state (`state.json`), report generation (downloaded/failed/rejected CSVs), and post-processing through the `modes/` pipelines. It remains the only supported way to run the full CSV-to-CD workflow.

**`main.py`** is a refactored CLI entry point that handles post-processing only. Given a directory of already-downloaded MP3 files, it runs either the MP3 CD or Audio CD pipeline. It does not handle downloading, CSV parsing, or state management.

The monolith is intentionally preserved as the working source of truth. It is not dead code -- it is the only complete path through the system.

## Input model decision

The project currently standardizes on a CSV-first input model:

1. Export playlist data with Exportify.
2. Load that CSV into the desktop app.
3. Let the app handle lookup, download, validation, and output generation.

An experimental branch, `feat/spotify-source`, explored direct Spotify-connected input by adding `spotipy` and local auth/config requirements. That route was not adopted because it introduces Spotify app registration, callback/env setup, and user-account friction into a packaged local utility while still leaving the later YouTube/`yt-dlp` acquisition path in place.

For this architecture, CSV import is the simpler and more supportable boundary.

## core/ responsibilities

- **`artists.py`** -- Parses artist fields from Exportify CSV rows. Handles semicolon- and comma-separated artist lists. Provides `make_track_key` for deduplication and `get_duration_ms` for extracting duration from various CSV column name variants (including BOM-prefixed).
- **`constants.py`** -- Centralizes shared operational values used by the extracted post-processing path, including the MP3 CD size target, bitrate ladder, and Audio CD conversion defaults.
- **`naming.py`** -- Produces filesystem-safe names (`safe_name`) and formats artist strings for filenames vs. metadata (metadata truncates to first two artists).
- **`query.py`** -- Builds an ordered list of YouTube search query variants from artist + track name, progressively simplifying (remove parentheticals, quotes) as fallbacks.
- **`ffmpeg_utils.py`** -- Wraps ffmpeg and ffprobe for: duration verification, total size calculation, required bitrate estimation, bitrate conversion, metadata tagging from filename, and chronological renumbering.

## modes/ responsibilities

- **`mp3_cd.py`** -- Post-processes a folder of MP3s to fit within the shared target defined in `core/constants.py`. Estimates a starting bitrate from total duration, iterates downward through the shared bitrate ladder until the output fits, then applies metadata and renumbers files.
- **`audio_cd.py`** -- Converts MP3s to WAV files using the shared Audio CD defaults defined in `core/constants.py`, writing them to an `audio_cd_ready/` subdirectory numbered for CD burning order.

## What is intentionally not refactored

The following remain in `main_original.py` by design, pending future extraction:

- **Download orchestration** -- yt-dlp search, candidate metadata retrieval, duration screening, download-with-retry logic.
- **CSV parsing and row validation** -- Reading Exportify CSVs, filtering invalid rows, computing average durations for imputation.
- **State management** -- `state.json` for resume support, report CSVs (downloaded, failed, rejected tracks).
- **GUI** -- Tkinter interface, progress bar, queue-based logging, start/stop controls.
- **`core/query.py` wiring** -- The module is extracted and tested, but only called from the monolith. `main.py` does not use it because it does not handle downloads.
