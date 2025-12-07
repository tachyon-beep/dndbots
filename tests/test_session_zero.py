"""Tests for Session Zero."""

import pytest
from dndbots.session_zero import (
    SessionZeroResult,
    build_session_zero_dm_prompt,
    build_session_zero_player_prompt,
    parse_scenario,
    parse_party_document,
    parse_character,
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


class TestSessionZeroParsers:
    def test_parse_scenario(self):
        """Extract scenario from DM output."""
        text = """Some preamble text.

[SCENARIO]
The town of Thornwall sits at the edge of the frontier.
Dark things stir in the ruins to the north.
[/SCENARIO]

Some other text."""
        result = parse_scenario(text)
        assert "Thornwall" in result
        assert "frontier" in result
        assert "preamble" not in result

    def test_parse_scenario_not_found(self):
        """Return empty string if no scenario block."""
        text = "No scenario here"
        result = parse_scenario(text)
        assert result == ""

    def test_parse_party_document(self):
        """Extract party document from DM output."""
        text = """Blah blah.

[PARTY_DOCUMENT]
## Relationships
- Kira and Marcus share a dark history
[/PARTY_DOCUMENT]

More text."""
        result = parse_party_document(text)
        assert "Relationships" in result
        assert "Kira and Marcus" in result

    def test_parse_character(self):
        """Parse character block into Character object."""
        text = """Here is my character:

[CHARACTER]
Name: Kira Ashford
Class: Fighter
Stats: STR 15, INT 10, WIS 12, DEX 13, CON 14, CHA 8
HP: 7
AC: 4
Equipment: longsword, shield, chain mail, backpack
Background: Deserted soldier seeking redemption
[/CHARACTER]

That's my character!"""
        char = parse_character(text)
        assert char is not None
        assert char.name == "Kira Ashford"
        assert char.char_class == "Fighter"
        assert char.stats.str == 15
        assert char.stats.int == 10
        assert char.hp == 7
        assert char.ac == 4
        assert "longsword" in char.equipment

    def test_parse_character_not_found(self):
        """Return None if no character block."""
        text = "No character here"
        result = parse_character(text)
        assert result is None
