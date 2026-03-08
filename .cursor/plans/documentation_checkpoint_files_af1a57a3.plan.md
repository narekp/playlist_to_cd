---
name: Documentation checkpoint files
overview: Create three concise documentation files (README.md, ARCHITECTURE.md, CURRENT_STATE.md) that accurately reflect the current state of the playlist_to_cd codebase without overstating progress or implying future architecture that does not yet exist.
todos:
  - id: readme
    content: Create README.md with project overview, usage, limitations, future direction, and test instructions
    status: completed
  - id: architecture
    content: Create ARCHITECTURE.md with module map, responsibilities, monolith vs CLI explanation, and intentional non-refactored areas
    status: completed
  - id: current-state
    content: Create CURRENT_STATE.md with working features, refactored modules, test coverage summary, and deferred milestones
    status: completed
isProject: false
---

# Documentation Checkpoint

## Files to inspect (already done)

- [main.py](main.py) -- CLI entry point (post-processing only)
- [main_original.py](main_original.py) -- monolith GUI app (CSV import, yt-dlp download, post-processing)
- [core/artists.py](core/artists.py), [core/naming.py](core/naming.py), [core/query.py](core/query.py), [core/ffmpeg_utils.py](core/ffmpeg_utils.py)
- [modes/mp3_cd.py](modes/mp3_cd.py), [modes/audio_cd.py](modes/audio_cd.py)
- All test files under `tests/`
- [pyproject.toml](pyproject.toml), [requirements.txt](requirements.txt)
- `.cursor/rules/*.mdc` (workflow rules)

## What each file will contain

### README.md

- **What it is:** A tool that turns Spotify playlist CSVs (via Exportify) into CD-ready output -- either MP3 CDs (~700 MB) or audio CDs (WAV, 44.1 kHz stereo).
- **Problem it solves:** Automates the download-from-YouTube + post-processing pipeline so a playlist can be burned to a physical CD.
- **What it currently does:** Two entry points exist -- `main_original.py` (full GUI: CSV parse, download, post-process) and `main.py` (CLI: post-processing only on an already-downloaded folder).
- **Current limitations:** `main.py` cannot yet drive the full workflow (download is only in the monolith). No headless/server mode. Requires ffmpeg, ffprobe, and yt-dlp installed locally.
- **Workflow:** brief step-by-step of both entry points.
- **Future direction:** mention possible webapp direction briefly, without implying any code exists for it.
- **How to run:** `python main.py --mode mp3 --processed-dir ... --accepted-duration-sec ...` and `python main_original.py` for the GUI.
- **How to test:** `pytest` (70 test functions across 7 test files, configured via `pyproject.toml`).

### ARCHITECTURE.md

- **Module map:** A diagram showing `main.py` and `main_original.py` both depending on `core/` and `modes/`.
- **core/ responsibilities:** `artists.py` (CSV field parsing), `naming.py` (safe filenames, artist formatting), `query.py` (YouTube search query building), `ffmpeg_utils.py` (ffmpeg/ffprobe wrappers).
- **modes/ responsibilities:** `mp3_cd.py` (bitrate reduction to fit 700 MB, metadata, renumbering), `audio_cd.py` (MP3-to-WAV conversion for CD burning).
- **main_original.py vs main.py:** The monolith is the only way to run the full workflow (CSV -> download -> post-process). `main.py` is the refactored CLI that only handles post-processing. The monolith is intentionally preserved as the source of truth until modular extraction is complete.
- **What is intentionally not refactored:** Download/acquisition orchestration, CSV parsing, yt-dlp integration, GUI, and state management (`state.json`) all remain in `main_original.py`. `core/query.py` is extracted but only called from the monolith.

### CURRENT_STATE.md

- **Working:** The legacy monolith (`main_original.py`) handles the full CSV -> download -> post-processing workflow via a Tkinter GUI. The extracted modular path (`main.py` + `core/` + `modes/`) currently covers post-processing / disc-prep behavior only.
- **Refactored:** `core/` (artists, naming, query, ffmpeg_utils) and `modes/` (mp3_cd, audio_cd) extracted from the monolith. `main.py` created as a clean CLI entry point for post-processing.
- **Tested:** 70 test functions across 7 test files covering all `core/` modules and both `modes/`. Tests use mocks at external boundaries (ffmpeg, subprocess, filesystem). `conftest.py` provides shared fixtures.
- **Deferred / next milestones:** Extract download orchestration from monolith. Wire `core/query.py` into the modular path. Replace Tkinter GUI with a possible web interface. Add integration tests with real ffmpeg. Add CLI support for the full CSV-to-CD workflow.

## Assumptions to avoid

- Do not imply `main.py` can drive the full workflow (it cannot; it only post-processes).
- Do not imply `core/query.py` is used by `main.py` (it is only used by the monolith).
- Do not imply any web framework code exists.
- Do not describe planned architecture as if it is implemented.

## What should explicitly not be overstated

- The refactoring scope: only post-processing logic has been extracted; acquisition remains monolithic.
- Test coverage: tests cover extracted modules well, but `main_original.py` has no dedicated tests.
- `main.py` maturity: it is a functional CLI but only covers half the workflow.
- Future webapp: it is a possible direction, not a decision or existing code.
