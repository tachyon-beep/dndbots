"""Tests for Session Zero."""

import pytest
from dndbots.session_zero import SessionZeroResult
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
