"""Tests for game data models."""

import pytest

from dndbots.models import Character, Stats


class TestStats:
    def test_modifier_for_high_stat(self):
        stats = Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11)
        assert stats.modifier("str") == 2  # 16 = +2 in Basic D&D

    def test_modifier_for_average_stat(self):
        stats = Stats(str=10, dex=10, con=10, int=10, wis=10, cha=10)
        assert stats.modifier("str") == 0

    def test_modifier_for_low_stat(self):
        stats = Stats(str=6, dex=10, con=10, int=10, wis=10, cha=10)
        assert stats.modifier("str") == -1


class TestCharacter:
    def test_character_creation(self):
        char = Character(
            name="Throk",
            char_class="Fighter",
            level=1,
            hp=8,
            hp_max=8,
            ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=["longsword", "chain mail"],
            gold=25,
        )
        assert char.name == "Throk"
        assert char.is_alive

    def test_character_take_damage(self):
        char = Character(
            name="Throk",
            char_class="Fighter",
            level=1,
            hp=8,
            hp_max=8,
            ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=[],
            gold=0,
        )
        char.take_damage(5)
        assert char.hp == 3
        assert char.is_alive

    def test_character_dies_at_zero_hp(self):
        char = Character(
            name="Throk",
            char_class="Fighter",
            level=1,
            hp=8,
            hp_max=8,
            ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=[],
            gold=0,
        )
        char.take_damage(10)
        assert char.hp == 0
        assert not char.is_alive

    def test_character_sheet_string(self):
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
        sheet = char.to_sheet()
        assert "Throk" in sheet
        assert "Fighter" in sheet
        assert "HP: 8/8" in sheet
