# Current State

## What is working

- **Full CSV-to-CD workflow** via the legacy monolith (`main_original.py`): CSV import, YouTube download, duration validation, MP3 CD or Audio CD post-processing, resume support, and report generation. This runs through a Tkinter GUI.
- **Post-processing / disc-prep** via the extracted modular path (`main.py` + `core/` + `modes/`): given a directory of MP3 files, the CLI can run either the MP3 CD pipeline (bitrate fitting, metadata, renumbering) or the Audio CD pipeline (WAV conversion).
- **Local macOS packaging** via `packaging/build_macos.sh`: builds `Spotify Playlist to Disk Converter.app` and a local distribution DMG (`Spotify_Playlist_to_Disk_Converter_0.1.0.dmg`) using `hdiutil`.

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

70 test functions across 7 test files:

- `test_artists.py` -- `split_artists`, `get_duration_ms`, `make_track_key`
- `test_naming.py` -- `safe_name`, `format_artists_for_filename`, `format_artists_for_metadata`
- `test_query.py` -- `build_query_variants` (single/multi artist, parentheticals, quotes, edge cases)
- `test_ffmpeg_utils_unit.py` -- `get_total_size`, `estimate_required_bitrate`, `renumber_files`, `verify_duration`, `convert_to_bitrate`, `set_metadata`
- `test_main.py` -- CLI routing to MP3 and Audio CD pipelines
- `modes/test_mp3_cd.py` -- `process_mp3_folder`, `run_mp3_pipeline`
- `modes/test_audio_cd.py` -- `renumber_wavs`, `convert_to_wav`, `run_audio_cd_pipeline`

Tests mock external boundaries (ffmpeg, ffprobe, subprocess, filesystem side effects). No tests require network access. `main_original.py` has no dedicated test coverage.

## Deferred / next milestones

- **Extract download orchestration** from the monolith into a reusable module so `main.py` can drive the full CSV-to-CD workflow.
- **Wire `core/query.py`** into the modular path (currently only called from the monolith).
- **Extract CSV parsing and state management** (`state.json`, report CSVs) from the monolith.
- **Add CLI support for the full workflow** (CSV input, download, post-processing) without requiring the Tkinter GUI.
- **Explore web interface** as a possible replacement for the Tkinter GUI (no code or decisions exist for this yet).
- **Add integration tests** that exercise ffmpeg/ffprobe with real files (current tests are fully mocked).
- **Add macOS signing/notarization** for smoother Gatekeeper behavior in public distribution.
