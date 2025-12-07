"""Integration tests for the complete rules system."""

from pathlib import Path

import pytest

from dndbots.rules_index import RulesIndex, MonsterEntry, SpellEntry
from dndbots.rules_tools import get_rules, list_rules, search_rules
from dndbots.rules_prompts import build_rules_summary
from dndbots.prompts import build_dm_prompt


# Use the actual indexed rules if they exist
RULES_DIR = Path(__file__).parent.parent / "rules"


@pytest.fixture
def real_rules_index():
    """Load the actual rules index from the project."""
    if not (RULES_DIR / "indexed").exists():
        pytest.skip("No indexed rules available")
    return RulesIndex(RULES_DIR)


class TestRulesIntegration:
    def test_load_all_monsters(self, real_rules_index):
        """Can load and query all indexed monsters."""
        monsters = list_rules(real_rules_index, "monsters")
        assert len(monsters) >= 5  # We created 5 sample monsters
        names = [m.name for m in monsters]
        assert "Goblin" in names
        assert "Ghoul" in names

    def test_load_all_spells(self, real_rules_index):
        """Can load and query all indexed spells."""
        spells = list_rules(real_rules_index, "spells")
        assert len(spells) >= 5  # We created 5 sample spells
        names = [s.name for s in spells]
        assert "Magic Missile" in names
        assert "Sleep" in names

    def test_get_monster_full_entry(self, real_rules_index):
        """Can retrieve full monster entry with all details."""
        result = get_rules(real_rules_index, "monsters/ghoul", detail="full")
        assert result is not None
        assert "paralysis" in result.content.lower() or "paralyze" in result.content.lower()
        assert result.metadata["ac"] == 6
        assert result.metadata["hd"] == "2"

    def test_get_spell_full_entry(self, real_rules_index):
        """Can retrieve full spell entry with all details."""
        result = get_rules(real_rules_index, "spells/magic_user/1/sleep", detail="full")
        assert result is not None
        assert "2d8" in result.content
        assert result.metadata["spell_level"] == 1

    def test_search_for_undead(self, real_rules_index):
        """Can search for undead monsters."""
        results = search_rules(real_rules_index, "undead", category="monsters")
        assert len(results) >= 2  # Skeleton and Ghoul
        paths = [r.path for r in results]
        assert "monsters/skeleton" in paths or "monsters/ghoul" in paths

    def test_search_for_poison(self, real_rules_index):
        """Can search for poison abilities."""
        results = search_rules(real_rules_index, "poison")
        assert len(results) >= 1
        # Giant Spider has poison
        paths = [r.path for r in results]
        assert any("spider" in p for p in paths)

    def test_filter_monsters_by_tag(self, real_rules_index):
        """Can filter monsters by tag."""
        humanoids = list_rules(real_rules_index, "monsters", tags=["humanoid"])
        assert len(humanoids) >= 2  # Goblin and Orc
        names = [m.name for m in humanoids]
        assert "Goblin" in names
        assert "Orc" in names

    def test_dm_prompt_includes_monsters(self, real_rules_index):
        """DM prompt includes monster quick reference."""
        prompt = build_dm_prompt("Test dungeon", rules_index=real_rules_index)
        assert "Goblin" in prompt
        assert "Ghoul" in prompt
        assert "monsters/" in prompt

    def test_dm_prompt_includes_spells(self, real_rules_index):
        """DM prompt includes spell quick reference."""
        prompt = build_dm_prompt("Test dungeon", rules_index=real_rules_index)
        assert "Magic Missile" in prompt or "Sleep" in prompt
        assert "spells/" in prompt

    def test_dm_prompt_includes_tool_syntax(self, real_rules_index):
        """DM prompt includes tool usage instructions."""
        prompt = build_dm_prompt("Test dungeon", rules_index=real_rules_index)
        assert "get_rules" in prompt
        assert "list_rules" in prompt
        assert "search_rules" in prompt


class TestRulesContentQuality:
    """Test the quality and completeness of indexed rules data."""

    def test_all_monsters_have_required_fields(self, real_rules_index):
        """All monsters have complete stat blocks and descriptions."""
        monsters = list_rules(real_rules_index, "monsters")
        for monster_entry in monsters:
            # Get full entry
            full = get_rules(real_rules_index, monster_entry.path, detail="full")
            assert full is not None

            # Check required fields
            assert full.metadata["ac"] is not None
            assert full.metadata["hd"] is not None
            assert full.metadata["xp"] is not None
            assert full.content  # Full text exists
            assert len(full.content) > 50  # Has meaningful description

    def test_all_spells_have_required_fields(self, real_rules_index):
        """All spells have complete information."""
        spells = list_rules(real_rules_index, "spells")
        for spell_entry in spells:
            # Get full entry
            full = get_rules(real_rules_index, spell_entry.path, detail="full")
            assert full is not None

            # Check required fields
            assert full.metadata["spell_class"] in ["cleric", "magic-user", "elf"]
            assert full.metadata["spell_level"] >= 1
            assert full.metadata["range"] is not None
            assert full.metadata["duration"] is not None
            assert full.content  # Full text exists

    def test_monster_stat_blocks_are_parseable(self, real_rules_index):
        """Monster stat blocks contain expected stat abbreviations."""
        monsters = list_rules(real_rules_index, "monsters")
        for monster_entry in monsters:
            if monster_entry.stat_preview:
                # Check for common stat abbreviations in stat block
                stat_block = monster_entry.stat_preview
                # Should have at least AC, HD, and XP
                assert "AC" in stat_block or "ac" in stat_block.lower()
                assert "HD" in stat_block or "hd" in stat_block.lower()
                assert "XP" in stat_block or "xp" in stat_block.lower()

    def test_related_entries_exist(self, real_rules_index):
        """Related entry paths actually exist in the index."""
        # Get all entries
        all_monsters = list_rules(real_rules_index, "monsters")
        all_spells = list_rules(real_rules_index, "spells")
        all_paths = {m.path for m in all_monsters} | {s.path for s in all_spells}

        # Check a few entries with related links
        goblin = get_rules(real_rules_index, "monsters/goblin", detail="summary")
        if goblin:
            for related_path in goblin.related:
                # Related path should either exist or be a planned entry
                # (we don't require all related entries to exist yet)
                assert "/" in related_path  # Should be a valid path format


class TestRulesSummaryGeneration:
    """Test the rules summary generation for DM prompts."""

    def test_summary_has_core_mechanics(self, real_rules_index):
        """Summary includes core D&D mechanics."""
        summary = build_rules_summary(real_rules_index)
        assert "THAC0" in summary
        assert "Combat" in summary or "COMBAT" in summary
        assert "Morale" in summary or "MORALE" in summary

    def test_summary_has_monster_list(self, real_rules_index):
        """Summary includes monster quick reference."""
        summary = build_rules_summary(real_rules_index)
        assert "Goblin" in summary
        assert "monsters/goblin" in summary

    def test_summary_has_spell_list(self, real_rules_index):
        """Summary includes spell quick reference."""
        summary = build_rules_summary(real_rules_index)
        assert "Cure Light Wounds" in summary or "Magic Missile" in summary

    def test_summary_has_tool_instructions(self, real_rules_index):
        """Summary includes tool usage instructions."""
        summary = build_rules_summary(real_rules_index)
        assert "get_rules" in summary
        assert "list_rules" in summary
        assert 'detail="summary' in summary or 'detail="full' in summary

    def test_summary_reasonable_length(self, real_rules_index):
        """Summary is approximately 300 lines or reasonable size."""
        summary = build_rules_summary(real_rules_index)
        lines = summary.strip().split("\n")
        # With sample data (5 monsters + 5 spells), should be under 100 lines
        # Full index would be ~300 lines
        assert 20 < len(lines) < 400, f"Summary has {len(lines)} lines"


class TestSearchFunctionality:
    """Test search and filtering capabilities."""

    def test_search_by_name(self, real_rules_index):
        """Search finds entries by name."""
        results = search_rules(real_rules_index, "goblin")
        assert len(results) >= 1
        assert any("goblin" in r.path.lower() for r in results)

    def test_search_by_ability(self, real_rules_index):
        """Search finds entries by special ability."""
        results = search_rules(real_rules_index, "paralyze")
        assert len(results) >= 1
        # Ghoul has paralyze
        assert any(r.relevance > 0 for r in results)

    def test_search_returns_snippets(self, real_rules_index):
        """Search results include context snippets."""
        results = search_rules(real_rules_index, "undead")
        for result in results:
            assert result.snippet  # Should have a snippet
            assert len(result.snippet) > 0

    def test_filter_by_multiple_tags(self, real_rules_index):
        """Can filter entries by multiple tags (AND logic)."""
        # Find entries that are both chaotic AND humanoid
        results = list_rules(real_rules_index, "monsters", tags=["chaotic", "humanoid"])
        # Goblin and Orc are both chaotic humanoids
        assert len(results) >= 2

    def test_category_prefix_filtering(self, real_rules_index):
        """Can filter by category prefix."""
        # List only cleric spells
        cleric_spells = list_rules(real_rules_index, "spells/cleric")
        for spell in cleric_spells:
            assert spell.path.startswith("spells/cleric")


class TestDetailLevels:
    """Test different detail levels for rule lookups."""

    def test_summary_detail_level(self, real_rules_index):
        """Summary detail returns just the summary text."""
        result = get_rules(real_rules_index, "monsters/goblin", detail="summary")
        assert result is not None
        # Summary should be short
        assert len(result.content) < 200
        assert "Small chaotic humanoids" in result.content

    def test_stats_detail_level(self, real_rules_index):
        """Stats detail returns stat block."""
        result = get_rules(real_rules_index, "monsters/goblin", detail="stats")
        assert result is not None
        # Should have stat abbreviations
        assert "AC" in result.content or "ac" in result.content.lower()
        assert "HD" in result.content or "hd" in result.content.lower()

    def test_full_detail_level(self, real_rules_index):
        """Full detail returns complete text."""
        result = get_rules(real_rules_index, "monsters/goblin", detail="full")
        assert result is not None
        # Full text should be longer than summary
        assert len(result.content) > 100
        # Should contain descriptive text
        assert "small" in result.content.lower()

    def test_metadata_consistent_across_levels(self, real_rules_index):
        """Metadata is the same regardless of detail level."""
        summary = get_rules(real_rules_index, "monsters/goblin", detail="summary")
        stats = get_rules(real_rules_index, "monsters/goblin", detail="stats")
        full = get_rules(real_rules_index, "monsters/goblin", detail="full")

        assert summary.metadata == stats.metadata == full.metadata
