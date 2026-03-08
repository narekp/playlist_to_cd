"""Minimal smoke test for the GUI App. Ensures App initializes without crashes."""

import tkinter as tk

import pytest


def test_app_initializes_without_crash(monkeypatch):
    """App starts without missing references after Exportify removal and layout changes."""
    import main_original

    monkeypatch.setattr(main_original, "check_dependencies", lambda: (True, []))

    root = tk.Tk()
    root.withdraw()
    app = main_original.App(root)
    root.destroy()

    assert app.url_entry is not None
    assert app.csv_entry is not None
    assert app.out_entry is not None
    assert app.mode_var is not None
    assert app.log is not None
    assert root.title() == "Playlist to CD"
