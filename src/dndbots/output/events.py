"""Output event types for the event bus."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class OutputEventType(Enum):
    """Types of events that flow through the output system."""

    # Game content
    NARRATION = "narration"         # DM narrative text
    PLAYER_ACTION = "player_action" # Player character actions
    DIALOGUE = "dialogue"           # Character speech

    # Mechanics
    DICE_ROLL = "dice_roll"         # Dice roll results
    COMBAT = "combat"               # Combat updates (damage, status)
    REFEREE = "referee"             # Referee rulings and mechanics

    # System
    SYSTEM = "system"               # System messages
    SESSION_START = "session_start" # Session began
    SESSION_END = "session_end"     # Session ended
    ERROR = "error"                 # Error messages


@dataclass
class OutputEvent:
    """An event to be sent to output plugins.

    This is the unit of communication between the game loop
    and output destinations (console, logs, Discord, etc.).
    """

    event_type: OutputEventType
    source: str  # Who generated this: "dm", "pc_throk_001", "system"
    content: str  # The text content to display
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
