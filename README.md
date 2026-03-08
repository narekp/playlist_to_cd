# playlist_to_cd

`playlist_to_cd` is a small macOS desktop utility that turns Spotify playlist CSV exports into CD-ready output: either an **MP3 CD** (~700 MB, bitrate-fitted) or an **Audio CD** (44.1 kHz / 16-bit stereo WAV).

## What problem it solves

Burning a Spotify playlist to a physical CD requires downloading each track, normalising formats, fitting the collection to disc capacity, applying metadata, and renumbering files. This project automates that pipeline.

## What it currently does

There are two entry points:

| Entry point | Interface | Scope |
|---|---|---|
| `main_original.py` | Tkinter GUI desktop app | Full workflow: CSV parsing, YouTube download via yt-dlp, duration validation, post-processing (MP3 CD or Audio CD) |
| `main.py` | CLI | Post-processing only: takes an existing directory of MP3 files and runs the MP3 CD or Audio CD pipeline |

The core logic (artist parsing, filename safety, search query building, ffmpeg operations) lives in reusable modules under `core/` and `modes/`.

## Recommended path

The supported product path is:

1. Export the Spotify playlist to CSV with [Exportify](https://exportify.net/).
2. Open the Tkinter desktop app.
3. Choose the CSV, choose an output folder, select MP3 CD or Audio CD, and run.

That CSV-first flow is the one this project is actively optimized around.

## Current limitations

- `main.py` cannot drive the full CSV-to-CD workflow; download/acquisition is only available through the desktop app (`main_original.py`).
- `core/query.py` (search query building) is extracted but only called from the monolith; it is not yet wired into `main.py`.
- No web app, server mode, or headless full-workflow entry point exists.
- Requires `ffmpeg`, `ffprobe`, and `yt-dlp` installed and available on `PATH`.

## Current workflow

### Full workflow (desktop app)

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

## Example workflow

**Full workflow (GUI):**

1. Export your Spotify playlist as a CSV using [Exportify](https://exportify.net/) and save as CSV.
2. Run `python main_original.py`, choose the CSV and an output folder, pick "MP3 CD" or "Audio CD", then Start.
3. When finished, burn the output folder to disc (for Audio CD, burn the `audio_cd_ready/` subfolder).

**Post-processing only (CLI):**

```bash
# Folder of MP3s → MP3 CD (~700 MB). Example: 1 hour of accepted audio.
python main.py --mode mp3 --processed-dir ./my_tracks --accepted-duration-sec 3600

# Same folder → Audio CD WAVs
python main.py --mode audio --processed-dir ./my_tracks
```

## Why the project is CSV-first

An experimental branch, `feat/spotify-source`, explored a direct Spotify-connected route by adding `spotipy` plus local environment and callback configuration.

That route is not the chosen product direction for this app:

- It adds Spotify app registration, local callback setup, and per-user credential/config management.
- It creates more account/auth friction for a simple local utility.
- It is a worse fit for a packaged desktop app than a plain CSV import flow.
- It still does not remove the downstream dependency on `yt-dlp`/YouTube matching for acquisition.

The decision is to keep the app centered on a simple user-owned workflow: export the playlist to CSV, then feed that CSV back into the desktop app. That path is more practical, easier to support, and avoids tying normal use to Spotify-specific auth requirements.

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

```bash
pytest
```

Test configuration lives in `pyproject.toml`. The suite currently includes 83 tests, including coverage for the extracted modules plus a minimal GUI smoke test. Tests mock external boundaries (ffmpeg, ffprobe, subprocess, filesystem) and do not require network access.

## Building the macOS app

To package the GUI as a standalone macOS `.app`:

1. **Prerequisites:** PyInstaller (`pip install pyinstaller`), and the external binaries in `packaging/bin/`. See `packaging/bin/README.md` for how to obtain ffmpeg, ffprobe, and yt-dlp.

2. **Build:**
   ```bash
   ./packaging/build_macos.sh
   ```

3. **Output:** `dist/Spotify Playlist to Disk Converter.app` — double-click it or run:

   ```bash
   open "dist/Spotify Playlist to Disk Converter.app"
   ```

The build script uses the project `.venv` if it exists and has PyInstaller installed.
