"""Tests for Campaign session recap generation."""

import os
import pytest
import tempfile

from dndbots.campaign import Campaign
from dndbots.models import Character, Stats


# Skip if Neo4j not configured
pytestmark = pytest.mark.skipif(
    not os.getenv("NEO4J_URI"),
    reason="NEO4J_URI not set"
)


@pytest.fixture
def neo4j_config():
    return {
        "uri": os.getenv("NEO4J_URI"),
        "username": os.getenv("NEO4J_USER", "neo4j"),
        "password": os.getenv("NEO4J_PASSWORD", ""),
    }


@pytest.fixture
async def campaign_with_history(neo4j_config):
    """Create campaign with some session history."""
    with tempfile.TemporaryDirectory() as tmpdir:
        campaign = Campaign(
            campaign_id="test_recap_campaign",
            name="Test Campaign",
            db_path=f"{tmpdir}/test.db",
            neo4j_config=neo4j_config,
        )
        await campaign.initialize()

        # Add a character
        char = Character(
            name="TestHero",
            char_class="Fighter",
            level=1,
            hp=10, hp_max=10, ac=5,
            stats=Stats(str=14, dex=12, con=13, int=10, wis=11, cha=9),
            equipment=["sword"],
            gold=50,
        )
        await campaign.add_character(char)

        # Simulate session 001 with some moments
        if campaign._neo4j:
            # Need to create characters for the kill relationship
            await campaign._neo4j.create_character(
                campaign_id="test_recap_campaign",
                char_id="pc_testhero_001",
                name="TestHero",
                char_class="Fighter",
                level=1,
            )
            await campaign._neo4j.create_character(
                campaign_id="test_recap_campaign",
                char_id="npc_goblin_001",
                name="Goblin",
                char_class="Goblin",
                level=1,
            )

            await campaign._neo4j.record_kill(
                campaign_id="test_recap_campaign",
                attacker_id="pc_testhero_001",
                target_id="npc_goblin_001",
                weapon="sword",
                damage=8,
                session="session_test_recap_campaign_001",
                turn=5,
            )
            await campaign._neo4j.record_moment(
                campaign_id="test_recap_campaign",
                actor_id="pc_testhero_001",
                moment_type="crit_hit",
                description="Natural 20 against the ogre",
                session="session_test_recap_campaign_001",
                turn=10,
            )

        yield campaign

        # Cleanup
        if campaign._neo4j:
            await campaign._neo4j.clear_campaign("test_recap_campaign")
        await campaign.close()


class TestCampaignRecap:
    """Test Campaign session recap generation."""

    @pytest.mark.asyncio
    async def test_has_previous_session(self, campaign_with_history):
        """has_previous_session returns True when history exists."""
        has_history = await campaign_with_history.has_previous_session()
        assert has_history is True

    @pytest.mark.asyncio
    async def test_generate_session_recap(self, campaign_with_history):
        """generate_session_recap returns formatted recap."""
        recap = await campaign_with_history.generate_session_recap()

        assert recap is not None
        assert "PREVIOUSLY" in recap or "Previously" in recap
        # Should mention the kill
        assert "kill" in recap.lower() or "killed" in recap.lower()

    @pytest.mark.asyncio
    async def test_generate_session_recap_empty_campaign(self, neo4j_config):
        """generate_session_recap returns None for empty campaign."""
        with tempfile.TemporaryDirectory() as tmpdir:
            campaign = Campaign(
                campaign_id="test_empty_recap",
                name="Empty Campaign",
                db_path=f"{tmpdir}/test.db",
                neo4j_config=neo4j_config,
            )
            await campaign.initialize()

            recap = await campaign.generate_session_recap()

            assert recap is None

            if campaign._neo4j:
                await campaign._neo4j.clear_campaign("test_empty_recap")
            await campaign.close()
