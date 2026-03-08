# playlist_to_cd

A tool that converts Spotify playlist CSVs (exported via [Exportify](https://exportify.net/)) into CD-ready output: either an **MP3 CD** (~700 MB, bitrate-fitted) or an **Audio CD** (44.1 kHz / 16-bit stereo WAV).

## What problem it solves

Burning a Spotify playlist to a physical CD requires downloading each track, normalising formats, fitting the collection to disc capacity, applying metadata, and renumbering files. This project automates that pipeline.

## What it currently does

There are two entry points:

| Entry point | Interface | Scope |
|---|---|---|
| `main_original.py` | Tkinter GUI | Full workflow: CSV parsing, YouTube download via yt-dlp, duration validation, post-processing (MP3 CD or Audio CD) |
| `main.py` | CLI | Post-processing only: takes an existing directory of MP3 files and runs the MP3 CD or Audio CD pipeline |

The core logic (artist parsing, filename safety, search query building, ffmpeg operations) has been extracted into reusable modules under `core/` and `modes/`.

## Current limitations

- `main.py` cannot drive the full CSV-to-CD workflow; download/acquisition is only available through the legacy monolith (`main_original.py`).
- `core/query.py` (search query building) is extracted but only called from the monolith; it is not yet wired into `main.py`.
- No headless or server mode exists.
- Requires `ffmpeg`, `ffprobe`, and `yt-dlp` installed and available on `PATH`.

## Current workflow

### Full workflow (GUI)

1. Export a Spotify playlist to CSV via Exportify.
2. Run `python main_original.py`.
3. Select the CSV, choose an output folder and output mode (MP3 CD or Audio CD).
4. The app downloads tracks from YouTube, validates durations, and runs the selected post-processing pipeline.
5. Output is a directory of numbered, metadata-tagged files ready to burn.

### Post-processing only (CLI)

If you already have a directory of MP3 files (e.g. from a previous interrupted run):

```
# MP3 CD mode (requires accepted duration)
python main.py --mode mp3 --processed-dir /path/to/mp3s --accepted-duration-sec 3600

# Audio CD mode
python main.py --mode audio --processed-dir /path/to/mp3s
```

## Where it is heading

Near-term goals focus on extracting the remaining monolith logic (download orchestration, CSV parsing, state management) into the modular path so `main.py` can drive the full workflow without the GUI.

A possible longer-term direction is replacing the Tkinter GUI with a web interface, but no code exists for that yet and no decisions have been made.

## How to run

### Prerequisites

- Python 3.9+
- `ffmpeg` and `ffprobe` on PATH
- `yt-dlp` on PATH (for the full workflow via `main_original.py`)

### Install

```
pip install -r requirements.txt
```

(`requirements.txt` currently contains only `pytest>=7.0` for testing.)

## How to run tests

```
pytest
```

Test configuration lives in `pyproject.toml`. The suite contains 70 test functions across 7 test files, covering all extracted modules (`core/` and `modes/`). Tests mock external boundaries (ffmpeg, ffprobe, subprocess, filesystem) and do not require network access.
