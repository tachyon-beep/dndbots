"""Tests for game loop."""

import os
import pytest

from dndbots.game import create_dm_agent, create_player_agent, DnDGame
from dndbots.models import Character, Stats


# Set dummy API key for testing
@pytest.fixture(autouse=True)
def mock_openai_key(monkeypatch):
    """Set a dummy OpenAI API key for testing."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-for-unit-tests")


class TestAgentCreation:
    def test_create_dm_agent(self):
        agent = create_dm_agent(
            scenario="Test scenario",
            model="gpt-4o-mini",  # Use mini for tests
        )
        assert agent.name == "dm"

    def test_create_player_agent(self):
        char = Character(
            name="Throk",
            char_class="Fighter",
            level=1,
            hp=8,
            hp_max=8,
            ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=["longsword"],
            gold=25,
        )
        agent = create_player_agent(
            character=char,
            model="gpt-4o-mini",
        )
        assert agent.name == "Throk"


class TestDnDGame:
    def test_game_initialization(self):
        char = Character(
            name="Throk",
            char_class="Fighter",
            level=1,
            hp=8,
            hp_max=8,
            ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=["longsword"],
            gold=25,
        )
        game = DnDGame(
            scenario="A goblin cave",
            characters=[char],
            dm_model="gpt-4o-mini",
            player_model="gpt-4o-mini",
        )
        assert game.dm is not None
        assert len(game.players) == 1
