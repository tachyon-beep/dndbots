"""Tests for rules reference."""

from dndbots.rules import RULES_SHORTHAND, get_thac0, check_hit


class TestThac0:
    def test_fighter_level_1_thac0(self):
        assert get_thac0("Fighter", 1) == 19

    def test_fighter_level_3_thac0(self):
        assert get_thac0("Fighter", 3) == 19  # Improves at 4

    def test_thief_level_1_thac0(self):
        assert get_thac0("Thief", 1) == 19

    def test_cleric_level_1_thac0(self):
        assert get_thac0("Cleric", 1) == 19

    def test_wizard_level_1_thac0(self):
        assert get_thac0("Magic-User", 1) == 19


class TestCheckHit:
    def test_hit_succeeds_when_roll_meets_target(self):
        # THAC0 19, AC 5 -> need 14 to hit
        assert check_hit(roll=14, thac0=19, target_ac=5) is True

    def test_hit_fails_when_roll_too_low(self):
        assert check_hit(roll=13, thac0=19, target_ac=5) is False

    def test_natural_20_always_hits(self):
        assert check_hit(roll=20, thac0=19, target_ac=-5) is True

    def test_natural_1_always_misses(self):
        assert check_hit(roll=1, thac0=10, target_ac=9) is False


class TestRulesShorthand:
    def test_rules_shorthand_exists(self):
        assert len(RULES_SHORTHAND) > 100  # Should be substantial
        assert "COMBAT" in RULES_SHORTHAND
        assert "THAC0" in RULES_SHORTHAND
