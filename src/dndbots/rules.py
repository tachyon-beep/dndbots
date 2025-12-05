"""Basic D&D rules reference and utilities."""

# THAC0 tables for Basic D&D (levels 1-3 for now)
THAC0_TABLE: dict[str, dict[int, int]] = {
    "Fighter": {1: 19, 2: 19, 3: 19, 4: 17, 5: 17, 6: 17},
    "Cleric": {1: 19, 2: 19, 3: 19, 4: 19, 5: 17, 6: 17},
    "Thief": {1: 19, 2: 19, 3: 19, 4: 19, 5: 17, 6: 17},
    "Magic-User": {1: 19, 2: 19, 3: 19, 4: 19, 5: 19, 6: 17},
}


def get_thac0(char_class: str, level: int) -> int:
    """Get THAC0 for a character class and level.

    THAC0 = 'To Hit Armor Class 0'. Lower is better.
    Roll d20 >= (THAC0 - target_AC) to hit.
    """
    class_table = THAC0_TABLE.get(char_class, THAC0_TABLE["Fighter"])
    # Clamp level to table range
    clamped_level = min(level, max(class_table.keys()))
    return class_table.get(clamped_level, 19)


def check_hit(roll: int, thac0: int, target_ac: int) -> bool:
    """Check if an attack roll hits.

    Args:
        roll: The d20 roll result (before modifiers)
        thac0: Attacker's THAC0
        target_ac: Defender's Armor Class

    Returns:
        True if the attack hits
    """
    # Natural 1 always misses, natural 20 always hits
    if roll == 1:
        return False
    if roll == 20:
        return True

    # Need to roll >= (THAC0 - AC) to hit
    target_number = thac0 - target_ac
    return roll >= target_number


# Compressed rules for system prompts
RULES_SHORTHAND = """
=== BASIC D&D RULES (Red Box) ===

COMBAT:
• Initiative: d6 per side, high acts first
• Attack: d20 >= (THAC0 - target_AC) = hit
• THAC0: Starts at 19 for all classes (lower is better)
• Natural 20: Always hits | Natural 1: Always misses
• Damage: Weapon die + STR modifier

ARMOR CLASS (lower is better):
• Unarmored: AC 9
• Leather: AC 7
• Chain: AC 5
• Plate: AC 3
• Shield: -1 AC

SAVING THROWS (d20 >= target):
• Death/Poison, Wands, Paralysis/Stone, Dragon Breath, Spells
• Fighter L1: 12/13/14/15/16
• Cleric L1: 11/12/14/16/15
• Thief L1: 13/14/13/16/15
• Magic-User L1: 13/14/13/16/15

ABILITY MODIFIERS:
• 3: -3 | 4-5: -2 | 6-8: -1 | 9-12: 0 | 13-15: +1 | 16-17: +2 | 18: +3

HEALING:
• Rest: 1d3 HP per full day of rest
• Clerical healing: Cure Light Wounds = 1d6+1 HP

DEATH:
• 0 HP = dead (Basic D&D has no death saves)
"""
