#!/usr/bin/env python3
"""
Launcher for the packaged macOS app. Sets PATH to include bundled binaries
(ffmpeg, ffprobe, yt-dlp) and common system install locations before running
the main application.
"""
import os
import sys


def _inject_common_macos_paths():
    """Prepend common macOS package manager paths to PATH when running as .app.

    Double-clicked .app bundles do not inherit the terminal's PATH. Add
    /opt/homebrew/bin, /usr/local/bin, and ~/.local/bin so the app can find
    Homebrew and pip-installed tools (e.g. ffmpeg, yt-dlp).
    """
    if not getattr(sys, "frozen", False):
        return

    common_paths = [
        "/opt/homebrew/bin",  # Apple Silicon Homebrew
        "/usr/local/bin",     # Intel Homebrew
        os.path.expanduser("~/.local/bin"),  # Python user installs (yt-dlp)
    ]
    existing = [p for p in common_paths if os.path.isdir(p)]
    if existing:
        path = os.environ.get("PATH", "")
        os.environ["PATH"] = os.pathsep.join(existing) + os.pathsep + path


def setup_bundled_path():
    """Prepend bundled bin directory to PATH so ffmpeg, ffprobe, yt-dlp are found."""
    if not getattr(sys, "frozen", False):
        return

    _inject_common_macos_paths()

    exe_dir = os.path.dirname(sys.executable)
    candidates = [
        os.path.join(getattr(sys, "_MEIPASS", exe_dir), "bin"),
        os.path.join(exe_dir, "bin"),
        os.path.join(exe_dir, "..", "Resources", "bin"),
        os.path.join(exe_dir, "..", "Frameworks", "bin"),
    ]
    for bin_dir in candidates:
        bin_dir = os.path.abspath(bin_dir)
        if os.path.isdir(bin_dir):
            path = os.environ.get("PATH", "")
            os.environ["PATH"] = bin_dir + os.pathsep + path
            break


if __name__ == "__main__":
    setup_bundled_path()

    import tkinter as tk

    from main_original import App

    root = tk.Tk()
    app = App(root)
    root.mainloop()
