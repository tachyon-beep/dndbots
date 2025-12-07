"""Rules index for BECMI D&D content."""

from dataclasses import dataclass, field


@dataclass
class RulesEntry:
    """A single rules entry (monster, spell, treasure type, procedure)."""

    # Identity
    path: str  # "monsters/goblin", "spells/cleric/1/cure_light_wounds"
    name: str  # "Goblin", "Cure Light Wounds"
    category: str  # "monster", "spell", "treasure", "procedure", "equipment"

    # BECMI set tracking
    ruleset: str  # "basic", "expert", "companion", "master", "immortals"

    # Source tracking
    source_file: str  # "becmi_dm_rulebook.txt"
    source_lines: tuple[int, int]  # (2456, 2489) for verification

    # Searchability
    tags: list[str]  # ["humanoid", "tribal", "low-level", "chaotic"]
    related: list[str]  # ["monsters/hobgoblin", "monsters/bugbear"]

    # Content tiers
    summary: str  # 1-2 line overview (always available)
    full_text: str  # Complete text (level 3)

    # Optional fields
    min_level: int | None = None  # Minimum character level relevance
    max_level: int | None = None  # Maximum character level relevance
    stat_block: str | None = None  # Compressed stats (level 2)


@dataclass
class MonsterEntry(RulesEntry):
    """Extended metadata for monster entries."""

    ac: int = 9  # Armor Class
    hd: str = "1"  # Hit Dice ("1-1", "3+1", "6**")
    move: str = "60' (20')"  # Movement
    attacks: str = "1"  # Attack routine
    damage: str = "1d6"  # Damage
    no_appearing: str = "1"  # Number appearing
    save_as: str = "F1"  # Save as
    morale: int = 6  # Morale score
    treasure_type: str = "None"  # Treasure
    alignment: str = "Neutral"  # Alignment
    xp: int = 0  # XP value
    special_abilities: list[str] = field(default_factory=list)


@dataclass
class SpellEntry(RulesEntry):
    """Extended metadata for spell entries."""

    spell_class: str = "magic-user"  # "cleric", "magic-user", "elf"
    spell_level: int = 1  # 1-5 for Basic
    range: str = "0"  # "Touch", "120'", "0 (caster only)"
    duration: str = "Instantaneous"  # "Permanent", "2 turns", "1 round/level"
    reversible: bool = False  # Can be reversed
    reverse_name: str | None = None  # "Cause Light Wounds"
