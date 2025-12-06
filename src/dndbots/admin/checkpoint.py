"""Checkpoint models for graceful shutdown and resume."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class NarrativeCheckpoint:
    """Minimal checkpoint for narrative pause.

    Stores enough context for the DM to resume the story naturally
    after a clean shutdown.
    """

    campaign_id: str
    session_id: str
    party_location: str
    current_beat: str | None = None
    recent_events: list[str] = field(default_factory=list)
    dm_notes: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "campaign_id": self.campaign_id,
            "session_id": self.session_id,
            "party_location": self.party_location,
            "current_beat": self.current_beat,
            "recent_events": self.recent_events,
            "dm_notes": self.dm_notes,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NarrativeCheckpoint":
        """Create from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.now(timezone.utc)

        return cls(
            campaign_id=data["campaign_id"],
            session_id=data["session_id"],
            party_location=data["party_location"],
            current_beat=data.get("current_beat"),
            recent_events=data.get("recent_events", []),
            dm_notes=data.get("dm_notes", ""),
            timestamp=timestamp,
        )


@dataclass
class CombatCheckpoint:
    """Full checkpoint for mid-combat shutdown.

    Stores complete combat state for resumption at exact point,
    including initiative order, HP, conditions, and action log.
    """

    narrative: NarrativeCheckpoint
    initiative_order: list[str]
    current_turn: int
    round_number: int
    combatants: dict[str, dict[str, Any]]
    rounds: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "narrative": self.narrative.to_dict(),
            "initiative_order": self.initiative_order,
            "current_turn": self.current_turn,
            "round_number": self.round_number,
            "combatants": self.combatants,
            "rounds": self.rounds,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CombatCheckpoint":
        """Create from dictionary."""
        return cls(
            narrative=NarrativeCheckpoint.from_dict(data["narrative"]),
            initiative_order=data["initiative_order"],
            current_turn=data["current_turn"],
            round_number=data["round_number"],
            combatants=data["combatants"],
            rounds=data["rounds"],
        )
