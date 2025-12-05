"""Tests for game loop."""

import os
import pytest
from unittest.mock import Mock

from dndbots.game import create_dm_agent, create_player_agent, DnDGame, dm_selector
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


class TestDmSelector:
    def test_dm_selector_empty_messages_returns_dm(self):
        """When no messages, DM should start."""
        result = dm_selector([])
        assert result == "dm"

    def test_dm_selector_after_player_returns_dm(self):
        """After player speaks, control returns to DM."""
        mock_message = Mock()
        mock_message.source = "Throk"
        result = dm_selector([mock_message])
        assert result == "dm"

    def test_dm_selector_after_dm_returns_none(self):
        """After DM speaks, let model selector determine next speaker."""
        mock_message = Mock()
        mock_message.source = "dm"
        result = dm_selector([mock_message])
        assert result is None


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
