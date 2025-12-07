"""Tests for rules prompt generation."""

import json
import tempfile
from pathlib import Path

import pytest

from dndbots.rules_prompts import build_rules_summary
from dndbots.rules_index import RulesIndex


@pytest.fixture
def rules_index_for_summary():
    """Create a RulesIndex with varied test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        index_dir = Path(tmpdir) / "indexed" / "basic"
        index_dir.mkdir(parents=True)

        monsters = {
            "goblin": {
                "path": "monsters/goblin",
                "name": "Goblin",
                "category": "monster",
                "ruleset": "basic",
                "source_file": "dm.txt",
                "source_lines": [100, 120],
                "tags": ["humanoid"],
                "related": [],
                "summary": "Small humanoids",
                "full_text": "...",
                "stat_block": "AC6 HD1-1 ML7 XP5",
                "ac": 6, "hd": "1-1", "move": "90'", "attacks": "1",
                "damage": "1d6", "no_appearing": "2-8", "save_as": "NM",
                "morale": 7, "treasure_type": "C", "alignment": "C", "xp": 5,
                "special_abilities": [],
            },
        }
        spells = {
            "cure_light_wounds": {
                "path": "spells/cleric/1/cure_light_wounds",
                "name": "Cure Light Wounds",
                "category": "spell",
                "ruleset": "basic",
                "source_file": "player.txt",
                "source_lines": [200, 210],
                "tags": ["healing"],
                "related": [],
                "summary": "Touch, heal 1d6+1",
                "full_text": "...",
                "spell_class": "cleric",
                "spell_level": 1,
                "range": "Touch",
                "duration": "Permanent",
                "reversible": True,
                "reverse_name": "Cause Light Wounds",
            },
        }
        (index_dir / "monsters.json").write_text(json.dumps(monsters))
        (index_dir / "spells.json").write_text(json.dumps(spells))

        yield RulesIndex(Path(tmpdir))


class TestBuildRulesSummary:
    def test_summary_includes_core_mechanics(self, rules_index_for_summary):
        """Summary includes core D&D mechanics."""
        summary = build_rules_summary(rules_index_for_summary)
        assert "THAC0" in summary
        assert "Combat" in summary or "COMBAT" in summary

    def test_summary_includes_monster_list(self, rules_index_for_summary):
        """Summary includes monster quick reference."""
        summary = build_rules_summary(rules_index_for_summary)
        assert "Goblin" in summary
        assert "monsters/goblin" in summary

    def test_summary_includes_spell_list(self, rules_index_for_summary):
        """Summary includes spell quick reference."""
        summary = build_rules_summary(rules_index_for_summary)
        assert "Cure Light Wounds" in summary

    def test_summary_includes_tool_syntax(self, rules_index_for_summary):
        """Summary includes tool usage instructions."""
        summary = build_rules_summary(rules_index_for_summary)
        assert "get_rules" in summary
        assert "list_rules" in summary

    def test_summary_reasonable_length(self, rules_index_for_summary):
        """Summary is approximately 300 lines."""
        summary = build_rules_summary(rules_index_for_summary)
        lines = summary.strip().split("\n")
        # With minimal test data, should be less than 100 lines
        # Full index would be ~300 lines
        assert 20 < len(lines) < 400
