# Current State

## What is working

- **Full CSV-to-CD workflow** via the desktop app (`main_original.py`): CSV import, YouTube download, duration validation, MP3 CD or Audio CD post-processing, resume support, and report generation. This runs through the Tkinter GUI and is the main supported product path.
- **Post-processing / disc-prep** via the extracted modular path (`main.py` + `core/` + `modes/`): given a directory of MP3 files, the CLI can run either the MP3 CD pipeline (bitrate fitting, metadata, renumbering) or the Audio CD pipeline (WAV conversion).
- **Packaged macOS app build** via PyInstaller: the Tkinter workflow can be shipped and launched as a standalone `.app`.

## What has been refactored

Extracted from the monolith into standalone, tested modules:

| Module | Extracted logic |
|---|---|
| `core/artists.py` | Artist string parsing, track key generation, duration field extraction |
| `core/constants.py` | Shared operational values for MP3 CD sizing and Audio CD conversion defaults |
| `core/naming.py` | Filesystem-safe name generation, artist formatting for filenames and metadata |
| `core/query.py` | YouTube search query variant building (extracted and tested, but only called from the monolith) |
| `core/ffmpeg_utils.py` | Duration verification, size calculation, bitrate estimation, conversion, metadata tagging, file renumbering |
| `modes/mp3_cd.py` | MP3 CD pipeline (bitrate reduction loop, metadata, renumbering) |
| `modes/audio_cd.py` | Audio CD pipeline (MP3 to WAV conversion) |
| `main.py` | CLI entry point for post-processing (replaces the GUI path for disc-prep tasks) |

Both `main.py` and `main_original.py` import from `core/` and `modes/`. Shared operational values for the extracted post-processing path now live in `core/constants.py`, which centralizes the MP3 CD target/bitrate ladder and the Audio CD WAV conversion defaults. The monolith still contains its own copy of `process_folder` (the post-processing function that predates `modes/mp3_cd.process_mp3_folder`), though it now delegates to `modes/` for the actual pipeline execution.

## What has been tested

83 tests across the current suite:

- `test_artists.py` -- `split_artists`, `get_duration_ms`, `make_track_key`
- `test_naming.py` -- `safe_name`, `format_artists_for_filename`, `format_artists_for_metadata`
- `test_query.py` -- `build_query_variants` (single/multi artist, parentheticals, quotes, edge cases)
- `test_ffmpeg_utils_unit.py` -- `get_total_size`, `estimate_required_bitrate`, `renumber_files`, `verify_duration`, `convert_to_bitrate`, `set_metadata`
- `test_gui_smoke.py` -- desktop app initialization smoke test
- `test_main.py` -- CLI routing to MP3 and Audio CD pipelines
- `modes/test_mp3_cd.py` -- `process_mp3_folder`, `run_mp3_pipeline`
- `modes/test_audio_cd.py` -- `renumber_wavs`, `convert_to_wav`, `run_audio_cd_pipeline`
- `sources/test_csv_source.py` and `sources/test_source_contract.py` -- CSV loading and row-shape compatibility

Tests mock external boundaries (ffmpeg, ffprobe, subprocess, filesystem side effects). No tests require network access. GUI coverage remains intentionally light.

## Explicitly dropped route

The branch `feat/spotify-source` is not the path this project is continuing with.

That branch introduced Spotify-specific setup (`spotipy`, `.env`, client ID, localhost redirect URI), but it was dropped as a product direction because it adds account/auth friction and developer-app setup to what is supposed to be a simple local utility. It also does not eliminate the later YouTube/`yt-dlp` acquisition step.

The chosen direction is the simpler CSV-first loop:

1. User exports the playlist to CSV with Exportify.
2. User feeds that CSV into the desktop app.
3. The app handles download, validation, and CD-ready output.

## Deferred / next milestones

- **Continue reducing monolith internals carefully** without changing the CSV-first product flow.
- **Wire `core/query.py`** into more extracted code where useful (it is still only called from the monolith today).
- **Extract more reusable non-UI logic** from `main_original.py` as low-risk opportunities appear.
- **Keep improving packaged-app usability** on macOS.
- **Add integration tests** that exercise ffmpeg/ffprobe with real files (current tests are fully mocked).
