#!/usr/bin/env python3
"""
Launcher for the packaged macOS app. Sets PATH to include bundled binaries
(ffmpeg, ffprobe, yt-dlp) before running the main application.
"""
import os
import sys


def setup_bundled_path():
    """Prepend bundled bin directory to PATH so ffmpeg, ffprobe, yt-dlp are found."""
    if not getattr(sys, "frozen", False):
        return

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
