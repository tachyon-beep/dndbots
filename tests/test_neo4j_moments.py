"""Tests for Neo4j moment recording."""

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
    await store.clear_campaign("test_moments")

    yield store

    await store.clear_campaign("test_moments")
    await store.close()


class TestMomentRecording:
    """Test moment and relationship recording."""

    async def test_record_kill_creates_relationship_and_moment(self, graph_store):
        """record_kill should create KILLED edge and Moment node."""
        # Setup: create attacker and target
        await graph_store.create_character(
            campaign_id="test_moments",
            char_id="pc_hero_001",
            name="Hero",
            char_class="Fighter",
            level=1,
        )
        await graph_store.create_character(
            campaign_id="test_moments",
            char_id="npc_goblin_001",
            name="Goblin",
            char_class="Goblin",
            level=1,
        )

        # Act
        moment_id = await graph_store.record_kill(
            campaign_id="test_moments",
            attacker_id="pc_hero_001",
            target_id="npc_goblin_001",
            weapon="longsword",
            damage=8,
            session="session_001",
            turn=5,
        )

        # Assert: moment exists
        assert moment_id is not None
        assert moment_id.startswith("moment_")

        # Assert: KILLED relationship exists
        kills = await graph_store.get_relationships("pc_hero_001", "KILLED")
        assert len(kills) == 1
        assert kills[0]["target_name"] == "Goblin"

    async def test_record_kill_includes_moment_reference(self, graph_store):
        """KILLED relationship should reference the Moment node."""
        await graph_store.create_character(
            campaign_id="test_moments",
            char_id="pc_hero_002",
            name="Hero2",
            char_class="Fighter",
            level=1,
        )
        await graph_store.create_character(
            campaign_id="test_moments",
            char_id="npc_goblin_002",
            name="Goblin2",
            char_class="Goblin",
            level=1,
        )

        moment_id = await graph_store.record_kill(
            campaign_id="test_moments",
            attacker_id="pc_hero_002",
            target_id="npc_goblin_002",
            weapon="axe",
            damage=12,
            session="session_001",
            turn=10,
        )

        # Query the relationship properties
        kills = await graph_store.get_relationships("pc_hero_002", "KILLED")
        assert kills[0]["rel_props"]["moment_id"] == moment_id
        assert kills[0]["rel_props"]["weapon"] == "axe"
        assert kills[0]["rel_props"]["damage"] == 12

    async def test_record_crit_creates_moment(self, graph_store):
        """record_crit should create a Moment node."""
        await graph_store.create_character(
            campaign_id="test_moments",
            char_id="pc_hero_003",
            name="Hero3",
            char_class="Fighter",
            level=1,
        )

        moment_id = await graph_store.record_moment(
            campaign_id="test_moments",
            actor_id="pc_hero_003",
            moment_type="crit_hit",
            description="Natural 20 against the ogre",
            session="session_001",
            turn=15,
        )

        assert moment_id is not None

        # Verify moment can be retrieved
        moment = await graph_store.get_moment(moment_id)
        assert moment is not None
        assert moment["moment_type"] == "crit_hit"
        assert "Natural 20" in moment["description"]
