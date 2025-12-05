"""Tests for agent prompt generation."""

from dndbots.prompts import build_dm_prompt, build_player_prompt
from dndbots.models import Character, Stats
from dndbots.memory import MemoryBuilder


class TestDMPrompt:
    def test_dm_prompt_contains_rules(self):
        prompt = build_dm_prompt(scenario="A goblin cave adventure")
        assert "THAC0" in prompt
        assert "COMBAT" in prompt

    def test_dm_prompt_contains_scenario(self):
        prompt = build_dm_prompt(scenario="A goblin cave adventure")
        assert "goblin cave" in prompt

    def test_dm_prompt_contains_dm_guidance(self):
        prompt = build_dm_prompt(scenario="test")
        assert "Dungeon Master" in prompt


class TestPlayerPrompt:
    def test_player_prompt_contains_character_sheet(self):
        char = Character(
            name="Throk",
            char_class="Fighter",
            level=1,
            hp=8,
            hp_max=8,
            ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=["longsword"],
            gold=25,
        )
        prompt = build_player_prompt(char)
        assert "Throk" in prompt
        assert "Fighter" in prompt
        assert "HP: 8/8" in prompt

    def test_player_prompt_contains_player_guidance(self):
        char = Character(
            name="Test",
            char_class="Fighter",
            level=1,
            hp=8,
            hp_max=8,
            ac=5,
            stats=Stats(str=10, dex=10, con=10, int=10, wis=10, cha=10),
            equipment=[],
            gold=0,
        )
        prompt = build_player_prompt(char)
        assert "roleplay" in prompt.lower() or "character" in prompt.lower()


class TestMemoryIntegration:
    def test_player_prompt_includes_memory_block(self):
        """Player prompts can include DCML memory."""
        char = Character(
            name="Throk",
            char_class="Fighter",
            level=1,
            hp=8, hp_max=8, ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=["longsword"],
            gold=25,
        )

        builder = MemoryBuilder()
        memory = builder.build_memory_document(
            pc_id="pc_throk_001",
            character=char,
            all_characters=[char],
            events=[],
        )

        prompt = build_player_prompt(char, memory=memory)

        assert "## LEXICON" in prompt
        assert "## MEMORY_pc_throk_001" in prompt

    def test_player_prompt_explains_dcml(self):
        """Player prompts include brief DCML usage guide."""
        char = Character(
            name="Throk",
            char_class="Fighter",
            level=1,
            hp=8, hp_max=8, ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=["longsword"],
            gold=25,
        )

        prompt = build_player_prompt(char, memory="## LEXICON\n## MEMORY_test")

        assert "LEXICON" in prompt
        # Should explain what memory block means
        assert "remember" in prompt.lower() or "memory" in prompt.lower()
