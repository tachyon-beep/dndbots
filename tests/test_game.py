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

    def test_create_dm_agent_with_rules_tools(self):
        """DM agent should have rules lookup tools by default."""
        agent = create_dm_agent(
            scenario="Test scenario",
            model="gpt-4o-mini",
            enable_rules_tools=True,
        )
        assert agent.name == "dm"
        # Check that tools are registered
        assert len(agent._tools) == 3
        tool_names = [t.name for t in agent._tools]
        assert "lookup_rules" in tool_names
        assert "list_rules_tool" in tool_names
        assert "search_rules_tool" in tool_names

    def test_create_dm_agent_without_rules_tools(self):
        """DM agent can be created without rules tools."""
        agent = create_dm_agent(
            scenario="Test scenario",
            model="gpt-4o-mini",
            enable_rules_tools=False,
        )
        assert agent.name == "dm"
        assert len(agent._tools) == 0


class TestRulesToolsIntegration:
    """Test rules tools work when invoked directly."""

    def test_rules_tools_can_be_invoked(self):
        """Tools can be called directly and return expected data."""
        from dndbots.rules_tools import create_rules_tools

        lookup, list_rules, search = create_rules_tools()

        # Test lookup_rules
        result = lookup("monsters/goblin", detail="stats")
        assert "Goblin" in result
        assert "AC6" in result

        # Test list_rules_tool
        result = list_rules("monsters", tags="undead")
        assert "entries" in result
        assert "ghoul" in result.lower() or "skeleton" in result.lower()

        # Test search_rules_tool
        result = search("poison", category="monsters")
        assert "poison" in result.lower()
        assert "Search results" in result

    def test_dm_agent_tools_are_callable(self):
        """Tools registered with DM agent can be called."""
        agent = create_dm_agent(
            scenario="Test scenario",
            model="gpt-4o-mini",
            enable_rules_tools=True,
        )

        # Get the lookup tool and invoke it directly
        lookup_tool = None
        for tool in agent._tools:
            if tool.name == "lookup_rules":
                lookup_tool = tool
                break

        assert lookup_tool is not None

        # Invoke the tool function (internal _func attribute)
        result = lookup_tool._func(path="monsters/orc", detail="summary")
        assert "Orc" in result or "orc" in result.lower()


class TestPlayerAgentCreation:
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


class TestGameEventBus:
    def test_game_uses_default_event_bus(self, monkeypatch):
        """Game creates default EventBus with ConsolePlugin when none provided."""
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

        # Verify game has an event bus
        assert game._event_bus is not None
        # Verify it has at least one plugin (ConsolePlugin)
        assert len(game._event_bus.plugins) == 1

    def test_game_accepts_custom_event_bus(self, monkeypatch):
        """Game can accept a custom EventBus."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        from dndbots.output import EventBus
        from dndbots.output.plugins import CallbackPlugin

        # Create custom bus
        custom_bus = EventBus()
        custom_bus.register(CallbackPlugin(
            name="test",
            callback=lambda e: None,
        ))

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
            event_bus=custom_bus,
        )

        # Verify game uses the custom bus
        assert game._event_bus is custom_bus
        assert len(game._event_bus.plugins) == 1
        assert game._event_bus.plugins[0].name == "test"


class TestDnDGamePartyDocument:
    def test_game_accepts_party_document(self):
        """DnDGame accepts optional party_document."""
        char = Character(
            name="Test",
            char_class="Fighter",
            level=1,
            hp=8,
            hp_max=8,
            ac=5,
            stats=Stats(str=14, dex=12, con=13, int=10, wis=11, cha=9),
            equipment=[],
            gold=0,
        )
        game = DnDGame(
            scenario="Test scenario",
            characters=[char],
            party_document="## Relationships\n- Test content",
        )
        assert game.party_document == "## Relationships\n- Test content"

    def test_game_works_without_party_document(self):
        """DnDGame works when party_document is None."""
        char = Character(
            name="Test",
            char_class="Fighter",
            level=1,
            hp=8,
            hp_max=8,
            ac=5,
            stats=Stats(str=14, dex=12, con=13, int=10, wis=11, cha=9),
            equipment=[],
            gold=0,
        )
        game = DnDGame(
            scenario="Test scenario",
            characters=[char],
        )
        assert game.party_document is None
