# Bundled Binaries for macOS App

Place the following executables in this directory before building the macOS app:

| Binary   | Purpose                          |
|----------|----------------------------------|
| `ffmpeg` | Audio conversion, metadata, WAV  |
| `ffprobe`| Duration verification            |
| `yt-dlp` | YouTube search and download      |

## How to obtain

### Option 1: Homebrew (simplest for local build)

If you have Homebrew installed:

```bash
brew install ffmpeg yt-dlp
```

Then create symlinks (run from this directory):

```bash
ln -sf "$(which ffmpeg)" ffmpeg
ln -sf "$(which ffprobe)" ffprobe
ln -sf "$(which yt-dlp)" yt-dlp
```

### Option 2: Static builds (for distribution)

For a standalone app that runs on machines without Homebrew:

- **ffmpeg / ffprobe**: Download static builds from [evermeet.cx/ffmpeg](https://evermeet.cx/ffmpeg/) or [ffmpeg.org](https://ffmpeg.org/download.html). Extract and copy `ffmpeg` and `ffprobe` into this directory. Use universal binaries if you need both Intel and Apple Silicon support.

- **yt-dlp**: Download the macOS binary from [yt-dlp releases](https://github.com/yt-dlp/yt-dlp/releases). Choose the appropriate architecture (e.g. `yt-dlp_macos` for Apple Silicon, or `yt-dlp_macos_legacy` for Intel). Rename to `yt-dlp` and make executable: `chmod +x yt-dlp`.

### Architecture notes

- Build on the same architecture you intend to run on, or use universal binaries.
- Apple Silicon (arm64): Use arm64 builds.
- Intel (x86_64): Use x86_64 builds.

## Verify

Before building, ensure the binaries are executable:

```bash
./ffmpeg -version
./ffprobe -version
./yt-dlp --version
```
