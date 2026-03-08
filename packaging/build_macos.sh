#!/usr/bin/env bash
# Build the playlist_to_cd macOS .app bundle.
# Run from project root: ./packaging/build_macos.sh
#
# Prerequisites:
#   pip install pyinstaller  (or use project .venv)
#   Place ffmpeg, ffprobe, yt-dlp in packaging/bin/ (see bin/README.md)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SPEC_FILE="$SCRIPT_DIR/playlist_to_cd.spec"

cd "$PROJECT_ROOT"

# Use project venv if it exists and has PyInstaller
if [[ -d ".venv" ]] && .venv/bin/python -c "import PyInstaller" 2>/dev/null; then
    export PATH="$(pwd)/.venv/bin:$PATH"
fi

# Check for binaries (warn but continue - app will fail at runtime if missing)
BIN_DIR="$SCRIPT_DIR/bin"
for name in ffmpeg ffprobe yt-dlp; do
    if [[ ! -f "$BIN_DIR/$name" ]]; then
        echo "WARNING: $BIN_DIR/$name not found. See $BIN_DIR/README.md" >&2
    fi
done

# Ensure PyInstaller is installed
if ! python -c "import PyInstaller" 2>/dev/null; then
    echo "PyInstaller not found. Install with: pip install pyinstaller" >&2
    exit 1
fi

# Build
pyinstaller --noconfirm --clean "$SPEC_FILE"

echo ""
echo "Build complete. App: $PROJECT_ROOT/dist/Spotify Playlist to Disk Converter.app"
