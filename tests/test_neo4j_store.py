"""Tests for Neo4j graph store."""

import pytest
import os

# Skip all tests if NEO4J_URI not set
pytestmark = pytest.mark.skipif(
    not os.getenv("NEO4J_URI"),
    reason="NEO4J_URI not set - skipping Neo4j tests"
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

    # Clean test data
    await store.clear_campaign("test_campaign")

    yield store

    # Cleanup
    await store.clear_campaign("test_campaign")
    await store.close()


class TestNeo4jStore:
    @pytest.mark.asyncio
    async def test_create_character_node(self, graph_store):
        char_id = await graph_store.create_character(
            campaign_id="test_campaign",
            char_id="pc_throk_001",
            name="Throk",
            char_class="Fighter",
            level=1,
        )
        assert char_id == "pc_throk_001"

        # Verify node exists
        char = await graph_store.get_character("pc_throk_001")
        assert char is not None
        assert char["name"] == "Throk"

    @pytest.mark.asyncio
    async def test_create_location_node(self, graph_store):
        loc_id = await graph_store.create_location(
            campaign_id="test_campaign",
            location_id="loc_caves_001",
            name="Caves of Chaos",
            description="A dark cave entrance",
        )
        assert loc_id == "loc_caves_001"

    @pytest.mark.asyncio
    async def test_create_relationship(self, graph_store):
        # Create nodes
        await graph_store.create_character(
            campaign_id="test_campaign",
            char_id="pc_throk_001",
            name="Throk",
            char_class="Fighter",
            level=1,
        )
        await graph_store.create_character(
            campaign_id="test_campaign",
            char_id="npc_goblin_001",
            name="Grimfang",
            char_class="Goblin",
            level=2,
        )

        # Create relationship
        await graph_store.create_relationship(
            from_id="pc_throk_001",
            to_id="npc_goblin_001",
            rel_type="KILLED",
            properties={"session": "session_001", "weapon": "longsword"},
        )

        # Query relationships
        killed = await graph_store.get_relationships(
            char_id="pc_throk_001",
            rel_type="KILLED",
        )
        assert len(killed) == 1
        assert killed[0]["target_name"] == "Grimfang"

    @pytest.mark.asyncio
    async def test_character_at_location(self, graph_store):
        await graph_store.create_character(
            campaign_id="test_campaign",
            char_id="pc_throk_001",
            name="Throk",
            char_class="Fighter",
            level=1,
        )
        await graph_store.create_location(
            campaign_id="test_campaign",
            location_id="loc_caves_001",
            name="Caves of Chaos",
        )

        await graph_store.set_character_location(
            char_id="pc_throk_001",
            location_id="loc_caves_001",
        )

        location = await graph_store.get_character_location("pc_throk_001")
        assert location is not None
        assert location["name"] == "Caves of Chaos"
