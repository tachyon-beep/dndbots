"""Tests for dice rolling utilities."""

import pytest

from dndbots.dice import roll, parse_roll


class TestRoll:
    def test_roll_d20_returns_int_in_range(self):
        for _ in range(100):
            result = roll(1, 20)
            assert 1 <= result <= 20

    def test_roll_2d6_returns_sum_in_range(self):
        for _ in range(100):
            result = roll(2, 6)
            assert 2 <= result <= 12

    def test_roll_with_modifier(self):
        for _ in range(100):
            result = roll(1, 20, modifier=5)
            assert 6 <= result <= 25

    def test_roll_raises_on_invalid_dice(self):
        with pytest.raises(ValueError, match="Invalid dice parameters: dice=0"):
            roll(0, 6)

    def test_roll_raises_on_invalid_sides(self):
        with pytest.raises(ValueError, match="Invalid dice parameters: .* sides=0"):
            roll(2, 0)

    def test_roll_raises_on_negative_dice(self):
        with pytest.raises(ValueError, match="Invalid dice parameters: dice=-1"):
            roll(-1, 6)


class TestParseRoll:
    def test_parse_d20(self):
        result = parse_roll("d20")
        assert result["dice"] == 1
        assert result["sides"] == 20
        assert result["modifier"] == 0

    def test_parse_2d6(self):
        result = parse_roll("2d6")
        assert result["dice"] == 2
        assert result["sides"] == 6
        assert result["modifier"] == 0

    def test_parse_d20_plus_5(self):
        result = parse_roll("d20+5")
        assert result["dice"] == 1
        assert result["sides"] == 20
        assert result["modifier"] == 5

    def test_parse_3d6_minus_2(self):
        result = parse_roll("3d6-2")
        assert result["dice"] == 3
        assert result["sides"] == 6
        assert result["modifier"] == -2
