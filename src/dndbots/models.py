"""Game data models for D&D characters and state."""

from dataclasses import dataclass, field


@dataclass
class Stats:
    """Character ability scores (Basic D&D)."""

    str: int
    dex: int
    con: int
    int: int
    wis: int
    cha: int

    def modifier(self, stat: str) -> int:
        """Get modifier for a stat (Basic D&D table).

        Basic D&D modifiers:
        3: -3, 4-5: -2, 6-8: -1, 9-12: 0, 13-15: +1, 16-17: +2, 18: +3
        """
        value = getattr(self, stat)
        if value <= 3:
            return -3
        elif value <= 5:
            return -2
        elif value <= 8:
            return -1
        elif value <= 12:
            return 0
        elif value <= 15:
            return 1
        elif value <= 17:
            return 2
        else:
            return 3


@dataclass
class Character:
    """A player character or NPC."""

    name: str
    char_class: str
    level: int
    hp: int
    hp_max: int
    ac: int
    stats: Stats
    equipment: list[str] = field(default_factory=list)
    gold: int = 0

    @property
    def is_alive(self) -> bool:
        """Character is alive if HP > 0."""
        return self.hp > 0

    def take_damage(self, amount: int) -> None:
        """Apply damage to character. HP cannot go below 0."""
        self.hp = max(0, self.hp - amount)

    def heal(self, amount: int) -> None:
        """Heal character. HP cannot exceed max."""
        self.hp = min(self.hp_max, self.hp + amount)

    def to_sheet(self) -> str:
        """Generate a compact character sheet string for context."""
        equipment_str = ", ".join(self.equipment) if self.equipment else "none"
        return f"""=== {self.name} ===
Class: {self.char_class} | Level: {self.level}
HP: {self.hp}/{self.hp_max} | AC: {self.ac}
STR: {self.stats.str} ({self.stats.modifier('str'):+d}) | DEX: {self.stats.dex} ({self.stats.modifier('dex'):+d}) | CON: {self.stats.con} ({self.stats.modifier('con'):+d})
INT: {self.stats.int} ({self.stats.modifier('int'):+d}) | WIS: {self.stats.wis} ({self.stats.modifier('wis'):+d}) | CHA: {self.stats.cha} ({self.stats.modifier('cha'):+d})
Equipment: {equipment_str}
Gold: {self.gold}gp"""
