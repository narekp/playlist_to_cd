"""Minimal GUI smoke tests for main_original.App."""

import tkinter as tk
from unittest.mock import patch

import pytest

# Regression: App instantiation, geometry, log tags, product naming
# Catches accidental shrinkage of window, removal of tag configuration, or layout breakage


@pytest.fixture
def mock_deps():
    with patch("main_original.check_dependencies", return_value=(True, [])):
        yield


def test_app_instantiates_with_hidden_root(mock_deps):
    import main_original

    root = tk.Tk()
    root.withdraw()
    try:
        app = main_original.App(root)
        assert app.log is not None
        assert app.progress is not None
        assert app.url_entry is not None
        assert app.csv_entry is not None
        assert app.out_entry is not None
        assert app.mode_var is not None
        assert root.title() == "Playlist to CD"
    finally:
        root.destroy()


def test_app_geometry_minsize(mock_deps):
    import main_original

    root = tk.Tk()
    root.withdraw()
    try:
        main_original.App(root)
        min_w, min_h = root.minsize()
        assert min_w >= 600
        assert min_h >= 550
    finally:
        root.destroy()


def test_app_log_accepts_tagged_inserts(mock_deps):
    import main_original

    root = tk.Tk()
    root.withdraw()
    try:
        app = main_original.App(root)
        tags = app.log.tag_names()
        assert "ok" in tags
        assert "warn" in tags
        assert "error" in tags

        app.log.insert(tk.END, "test ok\n", "ok")
        app.log.insert(tk.END, "test warn\n", "warn")
        app.log.insert(tk.END, "test error\n", "error")
        assert app.log.get("1.0", tk.END).count("test") == 3
    finally:
        root.destroy()
