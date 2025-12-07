"""Tests for rules index and data models."""

import pytest
from dndbots.rules_index import RulesEntry, MonsterEntry, SpellEntry


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


class TestMonsterEntry:
    def test_monster_entry_creation(self):
        """MonsterEntry includes monster-specific stat fields."""
        monster = MonsterEntry(
            path="monsters/goblin",
            name="Goblin",
            category="monster",
            ruleset="basic",
            source_file="becmi_dm_rulebook.txt",
            source_lines=(2456, 2489),
            tags=["humanoid", "chaotic", "low-level"],
            related=["monsters/hobgoblin", "monsters/bugbear"],
            summary="Small chaotic humanoids, -1 to hit in daylight",
            full_text="Goblins are small, evil humanoids...",
            stat_block="AC6 HD1-1 Mv90'(30') Atk1wpn Dm(wpn) ML7 XP5",
            ac=6,
            hd="1-1",
            move="90' (30')",
            attacks="1 weapon",
            damage="By weapon",
            no_appearing="2-8 (6-60)",
            save_as="Normal Man",
            morale=7,
            treasure_type="(R) C",
            alignment="Chaotic",
            xp=5,
            special_abilities=["infravision 90'", "-1 to hit in daylight"],
        )
        assert monster.ac == 6
        assert monster.hd == "1-1"
        assert monster.xp == 5
        assert "infravision" in monster.special_abilities[0]

    def test_monster_entry_is_rules_entry(self):
        """MonsterEntry is a subclass of RulesEntry."""
        monster = MonsterEntry(
            path="monsters/skeleton",
            name="Skeleton",
            category="monster",
            ruleset="basic",
            source_file="becmi_dm_rulebook.txt",
            source_lines=(3000, 3030),
            tags=["undead"],
            related=[],
            summary="Animated bones, mindless",
            full_text="Skeletons are...",
            ac=7,
            hd="1",
            move="60' (20')",
            attacks="1 weapon",
            damage="By weapon",
            no_appearing="3-12",
            save_as="F1",
            morale=12,
            treasure_type="None",
            alignment="Chaotic",
            xp=10,
            special_abilities=[],
        )
        assert isinstance(monster, RulesEntry)


class TestSpellEntry:
    def test_spell_entry_creation(self):
        """SpellEntry includes spell-specific fields."""
        spell = SpellEntry(
            path="spells/cleric/1/cure_light_wounds",
            name="Cure Light Wounds",
            category="spell",
            ruleset="basic",
            source_file="becmi_players_manual.txt",
            source_lines=(3500, 3520),
            tags=["healing", "cleric"],
            related=["spells/cleric/1/cause_light_wounds"],
            summary="Touch, heal 1d6+1 hp",
            full_text="By placing hands on a wounded creature...",
            stat_block="Range: Touch, Duration: Permanent, Effect: 1 creature",
            spell_class="cleric",
            spell_level=1,
            range="Touch",
            duration="Permanent",
            reversible=True,
            reverse_name="Cause Light Wounds",
        )
        assert spell.spell_class == "cleric"
        assert spell.spell_level == 1
        assert spell.reversible is True
        assert spell.reverse_name == "Cause Light Wounds"

    def test_spell_entry_non_reversible(self):
        """SpellEntry handles non-reversible spells."""
        spell = SpellEntry(
            path="spells/magic_user/1/magic_missile",
            name="Magic Missile",
            category="spell",
            ruleset="basic",
            source_file="becmi_players_manual.txt",
            source_lines=(3600, 3620),
            tags=["damage", "magic-user", "auto-hit"],
            related=[],
            summary="150', auto-hit, 2d6+1 damage",
            full_text="A glowing arrow of energy...",
            spell_class="magic-user",
            spell_level=1,
            range="150'",
            duration="Instantaneous",
            reversible=False,
        )
        assert spell.reversible is False
        assert spell.reverse_name is None
