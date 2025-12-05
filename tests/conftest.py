"""Shared pytest fixtures."""

import pytest


@pytest.fixture
def sample_character() -> dict:
    """A basic fighter character for testing."""
    return {
        "name": "Throk",
        "class": "Fighter",
        "level": 1,
        "hp": 8,
        "hp_max": 8,
        "ac": 5,  # Chain mail + shield in Basic D&D
        "stats": {"str": 16, "dex": 12, "con": 14, "int": 9, "wis": 10, "cha": 11},
        "equipment": ["longsword", "chain mail", "shield", "backpack", "torch x3"],
        "gold": 25,
    }
