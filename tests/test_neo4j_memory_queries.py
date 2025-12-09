"""Tests for Neo4j memory-related queries."""

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
    await store.clear_campaign("test_memory")

    yield store

    await store.clear_campaign("test_memory")
    await store.close()


class TestMemoryQueries:
    """Test queries needed for DCML memory building."""

    @pytest.mark.asyncio
    async def test_get_character_kills(self, graph_store):
        """get_character_kills returns kill relationships with details."""
        # Setup
        await graph_store.create_character(
            campaign_id="test_memory",
            char_id="pc_hero",
            name="Hero",
            char_class="Fighter",
            level=1,
        )
        await graph_store.create_character(
            campaign_id="test_memory",
            char_id="npc_goblin_01",
            name="Goblin Scout",
            char_class="Goblin",
            level=1,
        )
        await graph_store.record_kill(
            campaign_id="test_memory",
            attacker_id="pc_hero",
            target_id="npc_goblin_01",
            weapon="sword",
            damage=8,
            session="session_001",
            turn=5,
            narrative="Clean strike through the heart",
        )

        # Query
        kills = await graph_store.get_character_kills("pc_hero")

        assert len(kills) == 1
        assert kills[0]["target_name"] == "Goblin Scout"
        assert kills[0]["weapon"] == "sword"
        assert kills[0]["narrative"] == "Clean strike through the heart"

    @pytest.mark.asyncio
    async def test_get_witnessed_moments(self, graph_store):
        """get_witnessed_moments returns moments character was present for."""
        await graph_store.create_character(
            campaign_id="test_memory",
            char_id="pc_hero",
            name="Hero",
            char_class="Fighter",
            level=1,
        )
        await graph_store.create_character(
            campaign_id="test_memory",
            char_id="pc_ally",
            name="Ally",
            char_class="Thief",
            level=1,
        )

        # Hero performs a moment
        moment_id = await graph_store.record_moment(
            campaign_id="test_memory",
            actor_id="pc_hero",
            moment_type="creative",
            description="Hero swings from chandelier",
            session="session_001",
            turn=10,
        )

        # Mark ally as witness
        await graph_store.add_witness(moment_id, "pc_ally")

        # Query ally's witnessed moments
        witnessed = await graph_store.get_witnessed_moments("pc_ally")

        assert len(witnessed) >= 1
        assert any("chandelier" in m.get("description", "") for m in witnessed)

    @pytest.mark.asyncio
    async def test_get_known_entities(self, graph_store):
        """get_known_entities returns entities character has interacted with."""
        await graph_store.create_character(
            campaign_id="test_memory",
            char_id="pc_hero",
            name="Hero",
            char_class="Fighter",
            level=1,
        )
        await graph_store.create_character(
            campaign_id="test_memory",
            char_id="npc_elena",
            name="Elena",
            char_class="Villager",
            level=1,
        )
        await graph_store.create_location(
            campaign_id="test_memory",
            location_id="loc_village",
            name="Millbrook Village",
        )

        # Create interactions
        await graph_store.create_relationship(
            from_id="pc_hero",
            to_id="npc_elena",
            rel_type="MET",
            properties={"session": "session_001"},
        )
        await graph_store.create_relationship(
            from_id="pc_hero",
            to_id="loc_village",
            rel_type="VISITED",
            properties={"session": "session_001"},
        )

        # Query
        entities = await graph_store.get_known_entities("pc_hero")

        assert len(entities) >= 2
        entity_ids = [e["entity_id"] for e in entities]
        assert "npc_elena" in entity_ids
        assert "loc_village" in entity_ids
