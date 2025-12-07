"""Tests for rules index and data models."""

import pytest
from dndbots.rules_index import RulesEntry


class TestRulesEntry:
    def test_rules_entry_creation(self):
        """RulesEntry can be created with required fields."""
        entry = RulesEntry(
            path="monsters/goblin",
            name="Goblin",
            category="monster",
            ruleset="basic",
            source_file="becmi_dm_rulebook.txt",
            source_lines=(2456, 2489),
            tags=["humanoid", "chaotic"],
            related=["monsters/hobgoblin"],
            summary="Small chaotic humanoids, -1 to hit in daylight",
            full_text="Goblins are small, evil humanoids...",
        )
        assert entry.path == "monsters/goblin"
        assert entry.name == "Goblin"
        assert entry.ruleset == "basic"

    def test_rules_entry_optional_fields(self):
        """RulesEntry handles optional fields correctly."""
        entry = RulesEntry(
            path="procedures/morale",
            name="Morale",
            category="procedure",
            ruleset="basic",
            source_file="becmi_dm_rulebook.txt",
            source_lines=(100, 150),
            tags=["combat"],
            related=[],
            summary="Rules for monster morale checks",
            full_text="When monsters take casualties...",
        )
        assert entry.min_level is None
        assert entry.max_level is None
        assert entry.stat_block is None
