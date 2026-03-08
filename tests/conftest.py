"""Shared pytest fixtures for playlist_to_cd tests."""
import sys
import threading
from pathlib import Path

import pytest

# Ensure project root is on path for imports
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


@pytest.fixture
def stop_flag():
    """A threading.Event used as stop signal. Not set by default."""
    return threading.Event()


@pytest.fixture
def log_queue():
    """A queue.Queue for log messages. Tests can drain it to verify messages."""
    from queue import Queue
    return Queue()
