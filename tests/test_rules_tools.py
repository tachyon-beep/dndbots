"""Tests for rules tool functions."""

import json
import tempfile
from pathlib import Path

import pytest

from dndbots.rules_tools import get_rules
from dndbots.rules_index import RulesIndex, RulesResult


@pytest.fixture
def rules_index():
    """Create a RulesIndex with test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        index_dir = Path(tmpdir) / "indexed" / "basic"
        index_dir.mkdir(parents=True)

        monsters = {
            "goblin": {
                "path": "monsters/goblin",
                "name": "Goblin",
                "category": "monster",
                "ruleset": "basic",
                "source_file": "becmi_dm_rulebook.txt",
                "source_lines": [2456, 2489],
                "tags": ["humanoid", "chaotic"],
                "related": ["monsters/hobgoblin"],
                "summary": "Small chaotic humanoids, -1 to hit in daylight",
                "full_text": "Goblins are small, evil humanoids that live in caves...",
                "stat_block": "AC6 HD1-1 Mv90'(30') Atk1wpn Dm(wpn) ML7 XP5",
                "ac": 6,
                "hd": "1-1",
                "move": "90' (30')",
                "attacks": "1 weapon",
                "damage": "By weapon",
                "no_appearing": "2-8 (6-60)",
                "save_as": "Normal Man",
                "morale": 7,
                "treasure_type": "(R) C",
                "alignment": "Chaotic",
                "xp": 5,
                "special_abilities": ["infravision 90'", "-1 to hit in daylight"],
            }
        }
        (index_dir / "monsters.json").write_text(json.dumps(monsters))

        yield RulesIndex(Path(tmpdir))


class TestGetRules:
    def test_get_rules_summary(self, rules_index):
        """get_rules returns summary by default."""
        result = get_rules(rules_index, "monsters/goblin", detail="summary")
        assert isinstance(result, RulesResult)
        assert result.name == "Goblin"
        assert "Small chaotic humanoids" in result.content
        assert result.ruleset == "basic"

    def test_get_rules_stats(self, rules_index):
        """get_rules with detail='stats' returns stat block."""
        result = get_rules(rules_index, "monsters/goblin", detail="stats")
        assert "AC6" in result.content
        assert "HD1-1" in result.content

    def test_get_rules_full(self, rules_index):
        """get_rules with detail='full' returns full text."""
        result = get_rules(rules_index, "monsters/goblin", detail="full")
        assert "Goblins are small, evil humanoids" in result.content
        assert "caves" in result.content

    def test_get_rules_not_found(self, rules_index):
        """get_rules returns None for missing entries."""
        result = get_rules(rules_index, "monsters/dragon", detail="summary")
        assert result is None

    def test_get_rules_includes_metadata(self, rules_index):
        """get_rules includes metadata in result."""
        result = get_rules(rules_index, "monsters/goblin", detail="summary")
        assert result.metadata["ac"] == 6
        assert result.metadata["xp"] == 5
        assert result.source_reference == "becmi_dm_rulebook.txt:2456-2489"
