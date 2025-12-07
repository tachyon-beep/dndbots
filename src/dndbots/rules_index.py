"""Rules index for BECMI D&D content."""

from dataclasses import dataclass


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
