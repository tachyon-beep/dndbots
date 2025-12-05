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


class DCMLOp(Enum):
    """DCML operators - ASCII-friendly for cross-model compatibility."""
    # Structure & membership
    CONTAINS = ">"      # A contains / parents B
    PART_OF = "<"       # A is part of B
    AT = "@"            # X is located at Y
    IN = "in"           # X is member of group Y

    # Causality
    LEADS_TO = "->"     # A leads to / results in B
    CAUSED_BY = "<-"    # A was caused by / originates from B
    ASSOC = "~"         # Associated with / thematically linked

    # Definition
    DEFINED_AS = ":="   # Core identity
    PROPS = "::"        # Properties block


def render_lexicon_entry(category: DCMLCategory, uid: str, name: str) -> str:
    """Render a lexicon entry in [CATEGORY:UID:Name] format."""
    return f"[{category.value}:{uid}:{name}]"


def render_relation(subject: str, op: DCMLOp, obj: str) -> str:
    """Render a relation in 'subject OP object' format."""
    return f"{subject} {op.value} {obj}"


def render_properties(subject: str, props: dict[str, Any]) -> str:
    """Render properties in subject::key->value,key->value format.

    Lists are formatted with quoted values: tags->"a","b"
    """
    parts = []
    for key, value in props.items():
        if isinstance(value, list):
            # Tags and lists get quoted
            formatted = ",".join(f'"{v}"' for v in value)
        else:
            formatted = str(value)
        parts.append(f"{key}->{formatted}")

    return f"{subject}::{','.join(parts)}"


class Certainty(Enum):
    """Epistemic status markers for DCML facts."""
    FACT = ""       # Canonical, objective truth
    BELIEF = "!"    # In-world belief (may be inaccurate)
    RUMOR = "?"     # Myth, legend, or unconfirmed


def render_fact(statement: str, certainty: Certainty = Certainty.FACT) -> str:
    """Render a statement with epistemic marker prefix."""
    return f"{certainty.value}{statement}"
