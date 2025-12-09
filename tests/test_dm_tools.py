"""Tests for DM narrative tools."""

import pytest
from unittest.mock import AsyncMock

from dndbots.dm_tools import create_dm_tools


class TestDMTools:
    """Test DM tool creation and basic functionality."""

    def test_create_dm_tools_returns_tools(self):
        """create_dm_tools returns a list of tools."""
        tools = create_dm_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_dm_tools_include_narrative_tools(self):
        """DM tools include narrative management tools."""
        tools = create_dm_tools()
        tool_names = [t.name for t in tools]

        assert "introduce_npc_tool" in tool_names
        assert "set_faction_tool" in tool_names
        assert "enrich_moment_tool" in tool_names

    def test_dm_tools_include_query_tools(self):
        """DM tools include graph query tools."""
        tools = create_dm_tools()
        tool_names = [t.name for t in tools]

        assert "recall_kills_tool" in tool_names
        assert "recall_moments_tool" in tool_names


class TestIntroduceNPCTool:
    """Test NPC introduction tool."""

    @pytest.mark.asyncio
    async def test_introduce_npc_creates_character_node(self):
        """introduce_npc_tool creates character node in Neo4j."""
        mock_neo4j = AsyncMock()
        mock_neo4j.create_character = AsyncMock(return_value="npc_grimfang_001")

        tools = create_dm_tools(
            neo4j=mock_neo4j,
            campaign_id="test_campaign",
        )

        introduce_tool = next(t for t in tools if t.name == "introduce_npc_tool")

        result = await introduce_tool.run_json(
            {
                "name": "Grimfang",
                "description": "A scarred goblin chieftain",
                "char_class": "Goblin",
                "faction": "Darkwood Goblins",
            },
            cancellation_token=None,
        )

        mock_neo4j.create_character.assert_called_once()
        assert "Grimfang" in result
        assert "npc_grimfang" in result.lower()


class TestRecallKillsTool:
    """Test kill recall tool."""

    @pytest.mark.asyncio
    async def test_recall_kills_queries_neo4j(self):
        """recall_kills_tool queries KILLED relationships."""
        mock_neo4j = AsyncMock()
        mock_neo4j.get_relationships = AsyncMock(return_value=[
            {"target_name": "Goblin", "rel_props": {"weapon": "sword", "damage": 8}},
            {"target_name": "Grimfang", "rel_props": {"weapon": "axe", "damage": 12}},
        ])

        tools = create_dm_tools(neo4j=mock_neo4j, campaign_id="test")

        recall_tool = next(t for t in tools if t.name == "recall_kills_tool")

        result = await recall_tool.run_json(
            {"character_id": "pc_throk"},
            cancellation_token=None,
        )

        mock_neo4j.get_relationships.assert_called_with("pc_throk", "KILLED")
        assert "Goblin" in result
        assert "Grimfang" in result


class TestEnrichMomentTool:
    """Test moment enrichment tool."""

    @pytest.mark.asyncio
    async def test_enrich_moment_updates_narrative(self):
        """enrich_moment_tool updates moment narrative."""
        mock_neo4j = AsyncMock()
        mock_neo4j.update_moment_narrative = AsyncMock(return_value=True)

        tools = create_dm_tools(neo4j=mock_neo4j, campaign_id="test")

        enrich_tool = next(t for t in tools if t.name == "enrich_moment_tool")

        result = await enrich_tool.run_json(
            {
                "moment_id": "moment_abc123",
                "narrative": "Throk's blade sang through the air, cleaving the goblin in two",
            },
            cancellation_token=None,
        )

        mock_neo4j.update_moment_narrative.assert_called_once()
        assert "updated" in result.lower() or "enriched" in result.lower()
