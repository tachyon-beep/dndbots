"""Tests for DCML memory projection."""

import pytest
from dndbots.memory import MemoryBuilder
from dndbots.models import Character, Stats


class TestLexiconBuilder:
    def test_build_lexicon_from_characters(self):
        """Build lexicon entries from Character objects."""
        chars = [
            Character(
                name="Throk",
                char_class="Fighter",
                level=1,
                hp=8, hp_max=8, ac=5,
                stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
                equipment=[], gold=0,
            ),
            Character(
                name="Zara",
                char_class="Thief",
                level=1,
                hp=4, hp_max=4, ac=7,
                stats=Stats(str=10, dex=17, con=12, int=14, wis=11, cha=13),
                equipment=[], gold=0,
            ),
        ]

        # Note: Character objects have optional char_id attribute
        # Task spec says to use getattr(char, 'char_id', None)
        chars[0].__dict__['char_id'] = "pc_throk_001"
        chars[1].__dict__['char_id'] = "pc_zara_001"

        builder = MemoryBuilder()
        lexicon = builder.build_lexicon(characters=chars)

        assert "[PC:pc_throk_001:Throk]" in lexicon
        assert "[PC:pc_zara_001:Zara]" in lexicon

    def test_build_lexicon_includes_header(self):
        """Lexicon block has ## LEXICON header."""
        builder = MemoryBuilder()
        lexicon = builder.build_lexicon(characters=[])

        assert lexicon.startswith("## LEXICON\n")
