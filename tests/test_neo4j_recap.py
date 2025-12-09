"""Tests for Neo4j session recap functionality."""

import os
import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("NEO4J_URI"),
    reason="NEO4J_URI not set"
)


@pytest.fixture
async def graph_store():
    """Create Neo4j store for testing."""
    from dndbots.storage.neo4j_store import Neo4jStore

    store = Neo4jStore(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        username=os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "password"),
    )
    await store.initialize()
    await store.clear_campaign("test_recap")

    yield store

    await store.clear_campaign("test_recap")
    await store.close()


class TestSessionRecap:
    """Test session recap queries."""

    @pytest.mark.asyncio
    async def test_get_session_moments(self, graph_store):
        """get_session_moments returns moments from a specific session."""
        # Setup: create character and moments in session_001
        await graph_store.create_character(
            campaign_id="test_recap",
            char_id="pc_hero",
            name="Hero",
            char_class="Fighter",
            level=1,
        )

        await graph_store.record_moment(
            campaign_id="test_recap",
            actor_id="pc_hero",
            moment_type="kill",
            description="Hero killed a goblin",
            session="session_001",
            turn=5,
        )

        await graph_store.record_moment(
            campaign_id="test_recap",
            actor_id="pc_hero",
            moment_type="crit_hit",
            description="Natural 20 against ogre",
            session="session_001",
            turn=10,
        )

        # Create moment in different session
        await graph_store.record_moment(
            campaign_id="test_recap",
            actor_id="pc_hero",
            moment_type="creative",
            description="Something in session 2",
            session="session_002",
            turn=1,
        )

        # Query session_001 only
        moments = await graph_store.get_session_moments("test_recap", "session_001")

        assert len(moments) == 2
        assert all(m["session"] == "session_001" for m in moments)

    @pytest.mark.asyncio
    async def test_get_last_session_id(self, graph_store):
        """get_last_session_id returns most recent session."""
        await graph_store.create_character(
            campaign_id="test_recap",
            char_id="pc_hero",
            name="Hero",
            char_class="Fighter",
            level=1,
        )

        # Create moments in multiple sessions
        await graph_store.record_moment(
            campaign_id="test_recap",
            actor_id="pc_hero",
            moment_type="test",
            description="Session 1",
            session="session_001",
            turn=1,
        )
        await graph_store.record_moment(
            campaign_id="test_recap",
            actor_id="pc_hero",
            moment_type="test",
            description="Session 2",
            session="session_002",
            turn=1,
        )

        last_session = await graph_store.get_last_session_id("test_recap")

        assert last_session == "session_002"

    @pytest.mark.asyncio
    async def test_get_active_npcs(self, graph_store):
        """get_active_npcs returns NPCs encountered in session."""
        await graph_store.create_character(
            campaign_id="test_recap",
            char_id="npc_grimfang",
            name="Grimfang",
            char_class="Goblin",
            level=2,
        )
        await graph_store.create_character(
            campaign_id="test_recap",
            char_id="npc_elena",
            name="Elena",
            char_class="Villager",
            level=1,
        )

        # Mark NPCs as encountered in session
        await graph_store.mark_npc_encountered(
            "npc_grimfang",
            "session_001",
            status="hostile",
        )
        await graph_store.mark_npc_encountered(
            "npc_elena",
            "session_001",
            status="friendly",
        )

        npcs = await graph_store.get_active_npcs("test_recap", "session_001")

        assert len(npcs) == 2
        names = [n["name"] for n in npcs]
        assert "Grimfang" in names
        assert "Elena" in names
