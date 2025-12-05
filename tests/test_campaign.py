"""Tests for campaign manager."""

import pytest
import tempfile
from pathlib import Path

from dndbots.campaign import Campaign
from dndbots.models import Character, Stats
from dndbots.events import GameEvent, EventType


@pytest.fixture
async def campaign():
    """Create a test campaign with temporary storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "campaign.db"
        campaign = Campaign(
            campaign_id="test_campaign_001",
            name="Test Campaign",
            db_path=str(db_path),
        )
        await campaign.initialize()
        yield campaign
        await campaign.close()


class TestCampaign:
    @pytest.mark.asyncio
    async def test_campaign_creation(self, campaign):
        assert campaign.campaign_id == "test_campaign_001"
        assert campaign.name == "Test Campaign"

    @pytest.mark.asyncio
    async def test_add_character(self, campaign):
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

        char_id = await campaign.add_character(char)
        assert char_id is not None
        assert "throk" in char_id.lower()

        # Should be retrievable
        characters = await campaign.get_characters()
        assert len(characters) == 1
        assert characters[0].name == "Throk"

    @pytest.mark.asyncio
    async def test_start_session(self, campaign):
        session_id = await campaign.start_session()
        assert session_id is not None
        assert campaign.current_session_id == session_id

    @pytest.mark.asyncio
    async def test_record_event(self, campaign):
        await campaign.start_session()

        event = GameEvent(
            event_type=EventType.DM_NARRATION,
            source="dm",
            content="The adventure begins!",
            session_id=campaign.current_session_id,
        )

        event_id = await campaign.record_event(event)
        assert event_id is not None

        # Should be in session events (along with SESSION_START)
        events = await campaign.get_session_events()
        assert len(events) == 2
        assert events[0].event_type == EventType.SESSION_START
        assert events[1].content == "The adventure begins!"

    @pytest.mark.asyncio
    async def test_get_recent_events(self, campaign):
        await campaign.start_session()

        # Record several events
        for i in range(10):
            event = GameEvent(
                event_type=EventType.PLAYER_ACTION,
                source="pc_throk_001",
                content=f"Action {i}",
                session_id=campaign.current_session_id,
            )
            await campaign.record_event(event)

        # Get last 5
        recent = await campaign.get_recent_events(limit=5)
        assert len(recent) == 5
