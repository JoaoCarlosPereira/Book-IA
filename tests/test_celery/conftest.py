"""Reload pipeline module before each test (isolation from test_services imports)."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture(autouse=True)
def fresh_process_book_module():
    import app.celery_tasks.process_book as process_book_module

    importlib.reload(process_book_module)
    yield process_book_module
