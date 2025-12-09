"""Tests for Referee moment recording tool."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from dndbots.mechanics import MechanicsEngine
from dndbots.referee_tools import create_referee_tools


class TestRecordMomentTool:
    """Test the record_moment_tool."""

    def test_record_moment_tool_exists(self):
        """record_moment_tool should be in referee tools."""
        engine = MechanicsEngine()
        tools = create_referee_tools(engine)

        tool_names = [t.name for t in tools]
        assert "record_moment_tool" in tool_names

    @pytest.mark.asyncio
    async def test_record_moment_tool_calls_neo4j(self):
        """record_moment_tool should call neo4j.record_moment."""
        engine = MechanicsEngine()
        mock_neo4j = AsyncMock()
        mock_neo4j.record_moment = AsyncMock(return_value="moment_abc123")

        tools = create_referee_tools(
            engine,
            neo4j=mock_neo4j,
            campaign_id="test_campaign",
            session_id="session_001",
        )

        # Find the record_moment_tool
        record_tool = next(t for t in tools if t.name == "record_moment_tool")

        # Call it
        result = await record_tool.run_json(
            {
                "actor_id": "pc_throk",
                "moment_type": "creative",
                "description": "Throk swings from the chandelier to kick the goblin",
            },
            cancellation_token=None,
        )

        # Verify neo4j was called
        mock_neo4j.record_moment.assert_called_once()
        call_args = mock_neo4j.record_moment.call_args
        assert call_args.kwargs["actor_id"] == "pc_throk"
        assert call_args.kwargs["moment_type"] == "creative"
        assert "chandelier" in call_args.kwargs["description"]

    @pytest.mark.asyncio
    async def test_record_moment_tool_without_neo4j(self):
        """record_moment_tool should return gracefully without neo4j."""
        engine = MechanicsEngine()
        tools = create_referee_tools(engine)  # No neo4j

        record_tool = next(t for t in tools if t.name == "record_moment_tool")

        # Should not raise, just return acknowledgment
        result = await record_tool.run_json(
            {
                "actor_id": "pc_throk",
                "moment_type": "creative",
                "description": "Some cool move",
            },
            cancellation_token=None,
        )

        assert "recorded" in result.lower() or "noted" in result.lower()
