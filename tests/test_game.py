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


class TestGameMemory:
    @pytest.mark.asyncio
    async def test_game_builds_player_memory(self, monkeypatch):
        """Game builds DCML memory for player agents."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        char = Character(
            name="Throk",
            char_class="Fighter",
            level=1,
            hp=8, hp_max=8, ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=["longsword"],
            gold=25,
        )

        game = DnDGame(
            scenario="Test scenario",
            characters=[char],
            dm_model="gpt-4o",
            player_model="gpt-4o",
        )

        # Verify game initialization
        assert game.dm is not None
        assert len(game.players) == 1

        # Get the player agent's system messages
        player_agent = game.players[0]

        # Check that system messages include character name
        # AssistantAgent stores system message in _system_messages
        assert hasattr(player_agent, '_system_messages')
        system_messages = player_agent._system_messages
        assert len(system_messages) > 0
        assert "Throk" in str(system_messages)

    def test_build_player_memory_creates_dcml(self, monkeypatch):
        """_build_player_memory() creates DCML memory document."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        char = Character(
            name="Throk",
            char_class="Fighter",
            level=1,
            hp=8, hp_max=8, ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=["longsword"],
            gold=25,
        )

        game = DnDGame(
            scenario="Test scenario",
            characters=[char],
            dm_model="gpt-4o",
            player_model="gpt-4o",
            enable_memory=True,
        )

        # Call _build_player_memory
        memory = game._build_player_memory(char)

        # Verify DCML structure
        assert memory is not None
        assert "## LEXICON" in memory
        assert "## MEMORY_pc_throk_001" in memory
        assert "Throk" in memory

    def test_build_player_memory_disabled(self, monkeypatch):
        """_build_player_memory() returns None when memory disabled."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        char = Character(
            name="Throk",
            char_class="Fighter",
            level=1,
            hp=8, hp_max=8, ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=["longsword"],
            gold=25,
        )

        game = DnDGame(
            scenario="Test scenario",
            characters=[char],
            dm_model="gpt-4o",
            player_model="gpt-4o",
            enable_memory=False,
        )

        # Call _build_player_memory
        memory = game._build_player_memory(char)

        # Verify it returns None
        assert memory is None
