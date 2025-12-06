"""Tests for checkpoint models."""

import pytest
from datetime import datetime, timezone

from dndbots.admin.checkpoint import NarrativeCheckpoint, CombatCheckpoint


class TestNarrativeCheckpoint:
    """Tests for NarrativeCheckpoint."""

    def test_create_minimal(self):
        """Create checkpoint with required fields only."""
        checkpoint = NarrativeCheckpoint(
            campaign_id="campaign_001",
            session_id="session_001",
            party_location="loc_caves_entrance",
        )
        assert checkpoint.campaign_id == "campaign_001"
        assert checkpoint.session_id == "session_001"
        assert checkpoint.party_location == "loc_caves_entrance"
        assert checkpoint.current_beat is None
        assert checkpoint.recent_events == []
        assert checkpoint.dm_notes == ""

    def test_create_full(self):
        """Create checkpoint with all fields."""
        checkpoint = NarrativeCheckpoint(
            campaign_id="campaign_001",
            session_id="session_001",
            party_location="loc_caves_room_02",
            current_beat="exploring",
            recent_events=["evt_001", "evt_002"],
            dm_notes="Party just defeated goblins",
        )
        assert checkpoint.current_beat == "exploring"
        assert len(checkpoint.recent_events) == 2

    def test_to_dict(self):
        """Convert checkpoint to dictionary."""
        checkpoint = NarrativeCheckpoint(
            campaign_id="campaign_001",
            session_id="session_001",
            party_location="loc_caves_entrance",
        )
        data = checkpoint.to_dict()
        assert data["campaign_id"] == "campaign_001"
        assert "timestamp" in data

    def test_from_dict(self):
        """Create checkpoint from dictionary."""
        data = {
            "campaign_id": "campaign_001",
            "session_id": "session_001",
            "party_location": "loc_caves_entrance",
            "current_beat": None,
            "recent_events": [],
            "dm_notes": "",
            "timestamp": "2025-12-06T12:00:00+00:00",
        }
        checkpoint = NarrativeCheckpoint.from_dict(data)
        assert checkpoint.campaign_id == "campaign_001"


class TestCombatCheckpoint:
    """Tests for CombatCheckpoint."""

    def test_create_combat_checkpoint(self):
        """Create combat checkpoint with initiative."""
        narrative = NarrativeCheckpoint(
            campaign_id="campaign_001",
            session_id="session_001",
            party_location="loc_caves_room_02",
            current_beat="combat",
        )
        checkpoint = CombatCheckpoint(
            narrative=narrative,
            initiative_order=["pc_throk_001", "npc_goblin_001", "pc_zara_001"],
            current_turn=1,
            round_number=2,
            combatants={
                "pc_throk_001": {"hp": 12, "conditions": [], "position": "front"},
                "npc_goblin_001": {"hp": 3, "conditions": ["wounded"], "position": "center"},
                "pc_zara_001": {"hp": 8, "conditions": [], "position": "back"},
            },
            rounds=[],
        )
        assert checkpoint.current_turn == 1
        assert checkpoint.round_number == 2
        assert len(checkpoint.initiative_order) == 3
        assert checkpoint.combatants["npc_goblin_001"]["hp"] == 3

    def test_to_dict(self):
        """Convert combat checkpoint to dictionary."""
        narrative = NarrativeCheckpoint(
            campaign_id="campaign_001",
            session_id="session_001",
            party_location="loc_caves_room_02",
        )
        checkpoint = CombatCheckpoint(
            narrative=narrative,
            initiative_order=["pc_throk_001"],
            current_turn=0,
            round_number=1,
            combatants={},
            rounds=[],
        )
        data = checkpoint.to_dict()
        assert data["round_number"] == 1
        assert "narrative" in data

    def test_from_dict(self):
        """Create combat checkpoint from dictionary."""
        data = {
            "narrative": {
                "campaign_id": "campaign_001",
                "session_id": "session_001",
                "party_location": "loc_caves_room_02",
                "current_beat": None,
                "recent_events": [],
                "dm_notes": "",
                "timestamp": "2025-12-06T12:00:00+00:00",
            },
            "initiative_order": ["pc_throk_001"],
            "current_turn": 0,
            "round_number": 1,
            "combatants": {},
            "rounds": [],
        }
        checkpoint = CombatCheckpoint.from_dict(data)
        assert checkpoint.round_number == 1
        assert checkpoint.narrative.campaign_id == "campaign_001"
