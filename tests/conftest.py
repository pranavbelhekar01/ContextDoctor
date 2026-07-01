"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from contextdoctor.config import Config

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = REPO_ROOT / "examples"


@pytest.fixture
def config() -> Config:
    return Config()


@pytest.fixture
def examples_dir() -> Path:
    return EXAMPLES
