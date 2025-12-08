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


# Saving throw tables for Basic D&D (by class and level)
# Format: {class: {level: {save_type: target_number}}}
SAVING_THROWS: dict[str, dict[int, dict[str, int]]] = {
    "Fighter": {
        1: {"death_ray": 12, "wands": 13, "paralysis": 14, "breath": 15, "spells": 16},
        2: {"death_ray": 12, "wands": 13, "paralysis": 14, "breath": 15, "spells": 16},
        3: {"death_ray": 12, "wands": 13, "paralysis": 14, "breath": 15, "spells": 16},
        4: {"death_ray": 10, "wands": 11, "paralysis": 12, "breath": 13, "spells": 14},
        5: {"death_ray": 10, "wands": 11, "paralysis": 12, "breath": 13, "spells": 14},
        6: {"death_ray": 10, "wands": 11, "paralysis": 12, "breath": 13, "spells": 14},
    },
    "Cleric": {
        1: {"death_ray": 11, "wands": 12, "paralysis": 14, "breath": 16, "spells": 15},
        2: {"death_ray": 11, "wands": 12, "paralysis": 14, "breath": 16, "spells": 15},
        3: {"death_ray": 11, "wands": 12, "paralysis": 14, "breath": 16, "spells": 15},
        4: {"death_ray": 9, "wands": 10, "paralysis": 12, "breath": 14, "spells": 13},
        5: {"death_ray": 9, "wands": 10, "paralysis": 12, "breath": 14, "spells": 13},
        6: {"death_ray": 9, "wands": 10, "paralysis": 12, "breath": 14, "spells": 13},
    },
    "Thief": {
        1: {"death_ray": 13, "wands": 14, "paralysis": 13, "breath": 16, "spells": 15},
        2: {"death_ray": 13, "wands": 14, "paralysis": 13, "breath": 16, "spells": 15},
        3: {"death_ray": 13, "wands": 14, "paralysis": 13, "breath": 16, "spells": 15},
        4: {"death_ray": 11, "wands": 12, "paralysis": 11, "breath": 14, "spells": 13},
        5: {"death_ray": 11, "wands": 12, "paralysis": 11, "breath": 14, "spells": 13},
        6: {"death_ray": 11, "wands": 12, "paralysis": 11, "breath": 14, "spells": 13},
    },
    "Magic-User": {
        1: {"death_ray": 13, "wands": 14, "paralysis": 13, "breath": 16, "spells": 15},
        2: {"death_ray": 13, "wands": 14, "paralysis": 13, "breath": 16, "spells": 15},
        3: {"death_ray": 13, "wands": 14, "paralysis": 13, "breath": 16, "spells": 15},
        4: {"death_ray": 11, "wands": 12, "paralysis": 11, "breath": 14, "spells": 13},
        5: {"death_ray": 11, "wands": 12, "paralysis": 11, "breath": 14, "spells": 13},
        6: {"death_ray": 11, "wands": 12, "paralysis": 11, "breath": 14, "spells": 13},
    },
}


def get_saving_throw(char_class: str, level: int, save_type: str) -> int:
    """Get saving throw target number for a character class and level.

    Args:
        char_class: Character class (e.g., "Fighter", "Cleric", "Thief", "Magic-User")
        level: Character level (1-6 for now)
        save_type: Type of save ("death_ray", "wands", "paralysis", "breath", "spells")

    Returns:
        Target number needed on d20 to make the save

    Raises:
        ValueError: If save_type is invalid
    """
    # Normalize class name (capitalize first letter)
    normalized_class = char_class.capitalize()

    # Default to Fighter if class not found
    class_table = SAVING_THROWS.get(normalized_class, SAVING_THROWS["Fighter"])

    # Clamp level to available range
    clamped_level = min(level, max(class_table.keys()))
    clamped_level = max(clamped_level, 1)

    # Get saves for this level
    level_saves = class_table[clamped_level]

    # Validate save_type
    if save_type not in level_saves:
        valid_types = ", ".join(level_saves.keys())
        raise ValueError(
            f"Invalid save_type: {save_type}. Must be one of: {valid_types}"
        )

    return level_saves[save_type]


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
