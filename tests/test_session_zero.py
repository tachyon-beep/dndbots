"""Tests for Session Zero."""

import os
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


# Mock API key for tests
@pytest.fixture(autouse=True)
def mock_openai_key(monkeypatch):
    """Set a dummy OpenAI API key for testing."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-for-unit-tests")


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


class TestSessionZeroClass:
    def test_session_zero_init(self):
        """SessionZero initializes with agents."""
        from dndbots.session_zero import SessionZero

        sz = SessionZero(num_players=3)
        assert sz.dm is not None
        assert len(sz.players) == 3
        assert sz.num_players == 3

    def test_session_zero_agents_have_tools(self):
        """All agents have rules tools."""
        from dndbots.session_zero import SessionZero

        sz = SessionZero(num_players=2)
        # DM should have tools
        assert len(sz.dm._tools) == 3
        # Players should have tools
        for player in sz.players:
            assert len(player._tools) == 3

    def test_session_zero_has_team(self):
        """SessionZero creates a SelectorGroupChat team."""
        from dndbots.session_zero import SessionZero
        from autogen_agentchat.teams import SelectorGroupChat

        sz = SessionZero(num_players=2)
        assert hasattr(sz, "team")
        assert isinstance(sz.team, SelectorGroupChat)
        # Verify participants include DM and all players
        assert len(sz.team._participants) == 3  # DM + 2 players


class TestPhaseDetection:
    def test_phase_enum_exists(self):
        """Phase enum has expected values."""
        from dndbots.session_zero import Phase

        assert Phase.PITCH.value == "pitch"
        assert Phase.CONVERGE.value == "converge"
        assert Phase.LOCK.value == "lock"
        assert Phase.DONE.value == "done"

    def test_detect_pitch_complete(self):
        """Detect PITCH COMPLETE marker."""
        from dndbots.session_zero import detect_phase_marker, Phase

        text = "Great ideas everyone! PITCH COMPLETE"
        result = detect_phase_marker(text)
        assert result == Phase.CONVERGE

    def test_detect_convergence_complete(self):
        """Detect CONVERGENCE COMPLETE marker."""
        from dndbots.session_zero import detect_phase_marker, Phase

        text = "The party is taking shape. CONVERGENCE COMPLETE"
        result = detect_phase_marker(text)
        assert result == Phase.LOCK

    def test_detect_session_zero_locked(self):
        """Detect SESSION ZERO LOCKED marker."""
        from dndbots.session_zero import detect_phase_marker, Phase

        text = "Everything is finalized. SESSION ZERO LOCKED"
        result = detect_phase_marker(text)
        assert result == Phase.DONE

    def test_detect_no_marker(self):
        """Return None when no marker present."""
        from dndbots.session_zero import detect_phase_marker

        text = "Just regular conversation here."
        result = detect_phase_marker(text)
        assert result is None

    def test_detect_marker_case_insensitive(self):
        """Markers should work regardless of case."""
        from dndbots.session_zero import detect_phase_marker, Phase

        text = "pitch complete"
        result = detect_phase_marker(text)
        assert result == Phase.CONVERGE


class TestSessionZeroSelector:
    def test_dm_starts_first(self):
        """DM speaks first when no messages."""
        from unittest.mock import Mock
        from dndbots.session_zero import session_zero_selector

        result = session_zero_selector([])
        assert result == "dm"

    def test_dm_speaks_after_player(self):
        """DM speaks after any player."""
        from unittest.mock import Mock
        from dndbots.session_zero import session_zero_selector

        msg = Mock()
        msg.source = "player_1"
        result = session_zero_selector([msg])
        assert result == "dm"

    def test_model_selects_after_dm(self):
        """Model-based selection after DM speaks."""
        from unittest.mock import Mock
        from dndbots.session_zero import session_zero_selector

        msg = Mock()
        msg.source = "dm"
        result = session_zero_selector([msg])
        assert result is None  # Let model decide


class TestSessionZeroRun:
    def test_session_zero_has_run_method(self):
        """SessionZero has async run method."""
        from dndbots.session_zero import SessionZero
        import inspect

        sz = SessionZero(num_players=2)
        assert hasattr(sz, "run")
        assert inspect.iscoroutinefunction(sz.run)
