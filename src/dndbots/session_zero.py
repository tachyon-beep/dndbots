"""Session Zero: Collaborative campaign and character creation."""

from dataclasses import dataclass
from typing import Any

from dndbots.models import Character


@dataclass
class SessionZeroResult:
    """Output from a completed Session Zero."""

    scenario: str
    characters: list[Character]
    party_document: str
    transcript: list[Any]  # Message objects from AutoGen
