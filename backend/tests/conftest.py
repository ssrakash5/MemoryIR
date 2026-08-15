from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings
from app.services.container import build_services


@pytest.fixture
def services():
    return build_services(Settings(provider="mock", database_backend="memory"))
