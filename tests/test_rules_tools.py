"""Tests for rules tool functions."""

import json
import tempfile
from pathlib import Path

import pytest

from dndbots.rules_tools import get_rules, list_rules
from dndbots.rules_index import RulesIndex, RulesResult, RulesIndexEntry


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


# Add more monsters to fixture
@pytest.fixture
def rules_index_with_multiple():
    """Create a RulesIndex with multiple test entries."""
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
                "tags": ["humanoid", "chaotic", "low-level"],
                "related": ["monsters/hobgoblin"],
                "summary": "Small chaotic humanoids",
                "full_text": "Goblins are...",
                "stat_block": "AC6 HD1-1",
                "ac": 6, "hd": "1-1", "move": "90' (30')", "attacks": "1 weapon",
                "damage": "By weapon", "no_appearing": "2-8", "save_as": "Normal Man",
                "morale": 7, "treasure_type": "C", "alignment": "Chaotic",
                "xp": 5, "special_abilities": [],
            },
            "skeleton": {
                "path": "monsters/skeleton",
                "name": "Skeleton",
                "category": "monster",
                "ruleset": "basic",
                "source_file": "becmi_dm_rulebook.txt",
                "source_lines": [3000, 3030],
                "tags": ["undead", "low-level"],
                "related": ["monsters/zombie"],
                "summary": "Animated bones, mindless",
                "full_text": "Skeletons are...",
                "stat_block": "AC7 HD1",
                "ac": 7, "hd": "1", "move": "60' (20')", "attacks": "1 weapon",
                "damage": "By weapon", "no_appearing": "3-12", "save_as": "F1",
                "morale": 12, "treasure_type": "None", "alignment": "Chaotic",
                "xp": 10, "special_abilities": [],
            },
            "ghoul": {
                "path": "monsters/ghoul",
                "name": "Ghoul",
                "category": "monster",
                "ruleset": "basic",
                "source_file": "becmi_dm_rulebook.txt",
                "source_lines": [2200, 2240],
                "tags": ["undead", "paralyze"],
                "related": ["monsters/wight"],
                "summary": "Paralyzing touch, eats corpses",
                "full_text": "Ghouls are...",
                "stat_block": "AC6 HD2",
                "ac": 6, "hd": "2", "move": "90' (30')", "attacks": "2 claws/1 bite",
                "damage": "1d3/1d3/1d3+paralysis", "no_appearing": "1-6", "save_as": "F2",
                "morale": 9, "treasure_type": "B", "alignment": "Chaotic",
                "xp": 25, "special_abilities": ["paralyze on touch"],
            },
        }
        (index_dir / "monsters.json").write_text(json.dumps(monsters))

        yield RulesIndex(Path(tmpdir))


class TestListRules:
    def test_list_rules_all_monsters(self, rules_index_with_multiple):
        """list_rules returns all monsters in category."""
        results = list_rules(rules_index_with_multiple, "monsters")
        assert len(results) == 3
        names = [r.name for r in results]
        assert "Goblin" in names
        assert "Skeleton" in names
        assert "Ghoul" in names

    def test_list_rules_filter_by_tags(self, rules_index_with_multiple):
        """list_rules can filter by tags."""
        results = list_rules(rules_index_with_multiple, "monsters", tags=["undead"])
        assert len(results) == 2
        names = [r.name for r in results]
        assert "Skeleton" in names
        assert "Ghoul" in names
        assert "Goblin" not in names

    def test_list_rules_returns_index_entries(self, rules_index_with_multiple):
        """list_rules returns RulesIndexEntry objects."""
        results = list_rules(rules_index_with_multiple, "monsters")
        assert all(isinstance(r, RulesIndexEntry) for r in results)
        goblin = next(r for r in results if r.name == "Goblin")
        assert goblin.summary == "Small chaotic humanoids"
        assert "humanoid" in goblin.tags
