"""Tests for MemoryBuilder graph-based memory construction."""

import pytest
from unittest.mock import AsyncMock

from dndbots.memory import MemoryBuilder
from dndbots.models import Character, Stats


class TestMemoryBuilderFromGraph:
    """Test DCML memory building from Neo4j graph."""

    @pytest.mark.asyncio
    async def test_build_from_graph_returns_dcml(self):
        """build_from_graph returns valid DCML format."""
        mock_neo4j = AsyncMock()
        mock_neo4j.get_character_kills = AsyncMock(return_value=[
            {"target_name": "Goblin", "target_id": "npc_goblin_01", "weapon": "sword", "damage": 8},
        ])
        mock_neo4j.get_witnessed_moments = AsyncMock(return_value=[
            {"moment_type": "crit_hit", "description": "Natural 20 on ogre", "session": "s001", "turn": 5},
        ])
        mock_neo4j.get_known_entities = AsyncMock(return_value=[
            {"entity_id": "npc_elena", "name": "Elena", "entity_type": "character"},
            {"entity_id": "loc_caves", "name": "Caves of Chaos", "entity_type": "location"},
        ])
        mock_neo4j.get_character = AsyncMock(return_value={"name": "Hero", "char_class": "Fighter"})

        char = Character(
            name="Hero",
            char_class="Fighter",
            level=3,
            hp=24, hp_max=24, ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=["sword"],
            gold=100,
        )

        builder = MemoryBuilder()
        dcml = await builder.build_from_graph(
            pc_id="pc_hero",
            character=char,
            neo4j=mock_neo4j,
        )

        # Check DCML structure
        assert "## LEXICON" in dcml
        assert "## MEMORY_pc_hero" in dcml
        assert "[PC:pc_hero:Hero]" in dcml

    @pytest.mark.asyncio
    async def test_build_from_graph_includes_kills(self):
        """build_from_graph includes kill relationships."""
        mock_neo4j = AsyncMock()
        mock_neo4j.get_character_kills = AsyncMock(return_value=[
            {"target_name": "Grimfang", "target_id": "npc_grimfang", "weapon": "axe", "damage": 15,
             "narrative": "Cleaved in two"},
        ])
        mock_neo4j.get_witnessed_moments = AsyncMock(return_value=[])
        mock_neo4j.get_known_entities = AsyncMock(return_value=[])

        char = Character(
            name="Hero", char_class="Fighter", level=1,
            hp=10, hp_max=10, ac=5,
            stats=Stats(str=14, dex=12, con=13, int=10, wis=11, cha=9),
            equipment=[], gold=0,
        )

        builder = MemoryBuilder()
        dcml = await builder.build_from_graph(
            pc_id="pc_hero",
            character=char,
            neo4j=mock_neo4j,
        )

        assert "KILLED" in dcml or "killed" in dcml.lower()
        assert "npc_grimfang" in dcml or "Grimfang" in dcml

    @pytest.mark.asyncio
    async def test_build_from_graph_includes_known_entities_in_lexicon(self):
        """build_from_graph adds known entities to LEXICON."""
        mock_neo4j = AsyncMock()
        mock_neo4j.get_character_kills = AsyncMock(return_value=[])
        mock_neo4j.get_witnessed_moments = AsyncMock(return_value=[])
        mock_neo4j.get_known_entities = AsyncMock(return_value=[
            {"entity_id": "npc_elena", "name": "Elena", "entity_type": "character"},
            {"entity_id": "loc_caves", "name": "Caves of Chaos", "entity_type": "location"},
        ])

        char = Character(
            name="Hero", char_class="Fighter", level=1,
            hp=10, hp_max=10, ac=5,
            stats=Stats(str=14, dex=12, con=13, int=10, wis=11, cha=9),
            equipment=[], gold=0,
        )

        builder = MemoryBuilder()
        dcml = await builder.build_from_graph(
            pc_id="pc_hero",
            character=char,
            neo4j=mock_neo4j,
        )

        assert "[NPC:npc_elena:Elena]" in dcml
        assert "[LOC:loc_caves:Caves of Chaos]" in dcml
