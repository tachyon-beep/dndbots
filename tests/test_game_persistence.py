"""Tests for game loop with persistence integration."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from dndbots.game import DnDGame
from dndbots.campaign import Campaign
from dndbots.models import Character, Stats
from dndbots.events import EventType


@pytest.fixture
def mock_openai_key(monkeypatch):
    """Mock OpenAI API key for tests."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")


@pytest.fixture
async def campaign_with_char():
    """Create a campaign with a character."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        campaign = Campaign(
            campaign_id="test_001",
            name="Test Campaign",
            db_path=str(db_path),
        )
        await campaign.initialize()
        await campaign.start_session()

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
        await campaign.add_character(char)

        yield campaign
        await campaign.close()


class TestGameWithPersistence:
    def test_game_accepts_campaign_parameter(self, mock_openai_key):
        """Game should accept optional campaign parameter."""
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

        # Test without campaign (backward compatibility)
        game = DnDGame(
            scenario="Test scenario",
            characters=[char],
            dm_model="gpt-4o",
            player_model="gpt-4o",
        )
        assert game.campaign is None

        # Test with campaign
        mock_campaign = MagicMock()
        game_with_campaign = DnDGame(
            scenario="Test scenario",
            characters=[char],
            dm_model="gpt-4o",
            player_model="gpt-4o",
            campaign=mock_campaign,
        )
        assert game_with_campaign.campaign is mock_campaign

    @pytest.mark.asyncio
    async def test_game_records_events_during_gameplay(self, mock_openai_key, campaign_with_char):
        """Game should record events when campaign is provided."""
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

        # Create game with campaign
        game = DnDGame(
            scenario="Test scenario",
            characters=[char],
            dm_model="gpt-4o",
            player_model="gpt-4o",
            campaign=campaign_with_char,
        )

        # Mock the team's run_stream to simulate messages
        mock_message_dm = MagicMock()
        mock_message_dm.source = "dm"
        mock_message_dm.content = "The cave entrance looms before you."

        mock_message_player = MagicMock()
        mock_message_player.source = "Throk"
        mock_message_player.content = "I enter the cave cautiously."

        # Mock the async generator
        async def mock_run_stream(*args, **kwargs):
            yield mock_message_dm
            yield mock_message_player

        with patch.object(game.team, 'run_stream', side_effect=mock_run_stream):
            await game.run()

        # Verify events were recorded
        events = await campaign_with_char.get_session_events()

        # Should have session start event + 2 game events
        assert len(events) >= 3

        # Find the DM and player events (skip session start)
        dm_events = [e for e in events if e.event_type == EventType.DM_NARRATION]
        player_events = [e for e in events if e.event_type == EventType.PLAYER_ACTION]

        assert len(dm_events) >= 1
        assert len(player_events) >= 1

        # Check DM event
        dm_event = dm_events[0]
        assert dm_event.source == "dm"
        assert "cave entrance" in dm_event.content

        # Check player event
        player_event = player_events[0]
        assert player_event.source == "Throk"
        assert "enter the cave" in player_event.content

    @pytest.mark.asyncio
    async def test_game_without_campaign_still_works(self, mock_openai_key):
        """Game should work normally without campaign (backward compatibility)."""
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

        # Create game without campaign
        game = DnDGame(
            scenario="Test scenario",
            characters=[char],
            dm_model="gpt-4o",
            player_model="gpt-4o",
        )

        # Mock the team's run_stream to simulate messages
        mock_message = MagicMock()
        mock_message.source = "dm"
        mock_message.content = "Test message"

        async def mock_run_stream(*args, **kwargs):
            yield mock_message

        # Should not raise any errors even without campaign
        with patch.object(game.team, 'run_stream', side_effect=mock_run_stream):
            await game.run()
