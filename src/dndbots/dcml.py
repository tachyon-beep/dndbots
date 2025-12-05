"""DCML (D&D Condensed Memory Language) - Token-efficient campaign state serialization.

DCML is a lossy-but-precise serialization of campaign state from Neo4j + SQLite,
designed for LLM consumption. Models READ this; the engine OWNS it.

Based on UCLS (Ultra-Condensed Lore System) with D&D-specific adaptations.
See docs/example_compression.md for full specification.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DCMLCategory(Enum):
    """Entity categories for DCML lexicon."""
    PC = "PC"           # Player character
    NPC = "NPC"         # Named NPC / unique monster
    MON = "MON"         # Monster type (template)
    LOC = "LOC"         # Location / room / region
    FAC = "FAC"         # Faction / organization
    ITEM = "ITEM"       # Object / treasure
    QST = "QST"         # Quest / story thread
    EVT = "EVT"         # Event / beat / scene


def render_lexicon_entry(category: DCMLCategory, uid: str, name: str) -> str:
    """Render a lexicon entry in [CATEGORY:UID:Name] format."""
    return f"[{category.value}:{uid}:{name}]"
