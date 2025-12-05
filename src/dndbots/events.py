"""Game event schemas for persistence."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class EventType(Enum):
    """Types of game events."""
    DM_NARRATION = "dm_narration"
    PLAYER_ACTION = "player_action"
    DICE_ROLL = "dice_roll"
    COMBAT_START = "combat_start"
    COMBAT_END = "combat_end"
    DAMAGE = "damage"
    DEATH = "death"
    LOOT = "loot"
    QUEST_UPDATE = "quest_update"
    SESSION_START = "session_start"
    SESSION_END = "session_end"


@dataclass
class GameEvent:
    """A single game event for persistence and replay."""

    event_type: EventType
    source: str  # "dm", "system", or character UID like "pc_throk_001"
    content: str
    session_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)
    event_id: str | None = None  # Set by storage layer

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "source": self.source,
            "content": self.content,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GameEvent":
        """Create from dictionary."""
        return cls(
            event_id=data.get("event_id"),
            event_type=EventType(data["event_type"]),
            source=data["source"],
            content=data["content"],
            session_id=data["session_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )
