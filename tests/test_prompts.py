"""Tests for agent prompt generation."""

import json
import tempfile
from pathlib import Path

from dndbots.prompts import build_dm_prompt, build_player_prompt
from dndbots.models import Character, Stats
from dndbots.memory import MemoryBuilder
from dndbots.rules_index import RulesIndex


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


class TestDmPromptWithRulesIndex:
    def test_dm_prompt_with_rules_index(self):
        """DM prompt includes rules summary when index provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_dir = Path(tmpdir) / "indexed" / "basic"
            index_dir.mkdir(parents=True)
            monsters = {
                "orc": {
                    "path": "monsters/orc",
                    "name": "Orc",
                    "category": "monster",
                    "ruleset": "basic",
                    "source_file": "dm.txt",
                    "source_lines": [100, 120],
                    "tags": ["humanoid"],
                    "related": [],
                    "summary": "Pig-faced humanoids",
                    "full_text": "...",
                    "stat_block": "AC6 HD1",
                    "ac": 6, "hd": "1", "move": "90'", "attacks": "1",
                    "damage": "1d6", "no_appearing": "2-8", "save_as": "F1",
                    "morale": 8, "treasure_type": "D", "alignment": "C", "xp": 10,
                    "special_abilities": [],
                },
            }
            (index_dir / "monsters.json").write_text(json.dumps(monsters))

            rules_index = RulesIndex(Path(tmpdir))
            prompt = build_dm_prompt("Test scenario", rules_index=rules_index)

            assert "Orc" in prompt
            assert "get_rules" in prompt
            assert "BECMI" in prompt

    def test_dm_prompt_without_rules_index(self):
        """DM prompt uses RULES_SHORTHAND when no index provided."""
        prompt = build_dm_prompt("Test scenario")
        # Should still have basic rules
        assert "THAC0" in prompt or "COMBAT" in prompt


class TestPartyDocumentIntegration:
    def test_dm_prompt_includes_party_document(self):
        """DM prompt includes party document when provided."""
        party_doc = "## Relationships\n- Kira and Marcus share history"
        prompt = build_dm_prompt("Test scenario", party_document=party_doc)
        assert "Relationships" in prompt
        assert "Kira and Marcus" in prompt

    def test_dm_prompt_works_without_party_document(self):
        """DM prompt works when party_document is None."""
        prompt = build_dm_prompt("Test scenario", party_document=None)
        assert "Test scenario" in prompt

    def test_player_prompt_includes_party_document(self):
        """Player prompt includes party document when provided."""
        char = Character(
            name="Test",
            char_class="Fighter",
            level=1,
            hp=8,
            hp_max=8,
            ac=5,
            stats=Stats(str=14, dex=12, con=13, int=10, wis=11, cha=9),
            equipment=[],
            gold=0,
        )
        party_doc = "## Shared Goals\n- Stop the cult"
        prompt = build_player_prompt(char, party_document=party_doc)
        assert "Shared Goals" in prompt
        assert "Stop the cult" in prompt
