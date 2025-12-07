"""Tests for Session Zero."""

import pytest
from dndbots.session_zero import (
    SessionZeroResult,
    build_session_zero_dm_prompt,
    build_session_zero_player_prompt,
)
from dndbots.models import Character, Stats


class TestSessionZeroResult:
    def test_result_dataclass_exists(self):
        """SessionZeroResult holds session zero outputs."""
        char = Character(
            name="Test",
            char_class="Fighter",
            level=1,
            hp=8,
            hp_max=8,
            ac=5,
            stats=Stats(str=14, dex=12, con=13, int=10, wis=11, cha=9),
            equipment=["sword"],
            gold=10,
        )
        result = SessionZeroResult(
            scenario="Test scenario",
            characters=[char],
            party_document="Test party doc",
            transcript=[],
        )
        assert result.scenario == "Test scenario"
        assert len(result.characters) == 1
        assert result.party_document == "Test party doc"
        assert result.transcript == []


class TestSessionZeroPrompts:
    def test_dm_prompt_includes_phase_markers(self):
        """DM prompt tells them about phase marker phrases."""
        prompt = build_session_zero_dm_prompt()
        assert "PITCH COMPLETE" in prompt
        assert "CONVERGENCE COMPLETE" in prompt
        assert "SESSION ZERO LOCKED" in prompt

    def test_dm_prompt_includes_output_format(self):
        """DM prompt specifies output format."""
        prompt = build_session_zero_dm_prompt()
        assert "[SCENARIO]" in prompt
        assert "[PARTY_DOCUMENT]" in prompt

    def test_dm_prompt_mentions_guides(self):
        """DM prompt mentions guide lookups."""
        prompt = build_session_zero_dm_prompt()
        assert "guides/interesting-campaigns" in prompt

    def test_player_prompt_includes_output_format(self):
        """Player prompt specifies character output format."""
        prompt = build_session_zero_player_prompt(player_number=1)
        assert "[CHARACTER]" in prompt
        assert "Name:" in prompt
        assert "Class:" in prompt
        assert "Stats:" in prompt

    def test_player_prompt_mentions_guides(self):
        """Player prompt mentions guide lookups."""
        prompt = build_session_zero_player_prompt(player_number=1)
        assert "guides/interesting-characters" in prompt

    def test_player_prompt_includes_player_number(self):
        """Player prompt identifies which player they are."""
        prompt = build_session_zero_player_prompt(player_number=2)
        assert "Player 2" in prompt
