"""Integration tests for DCML memory system."""

import pytest
from dndbots.dcml import DCMLCategory, DCMLOp, Certainty
from dndbots.dcml import render_lexicon_entry, render_relation, render_properties, render_fact
from dndbots.memory import MemoryBuilder
from dndbots.models import Character, Stats
from dndbots.events import GameEvent, EventType
from dndbots.prompts import build_player_prompt


class TestDCMLIntegration:
    """End-to-end tests for the DCML memory system."""

    def test_full_memory_flow(self):
        """Test complete flow: events -> DCML -> prompt."""
        # Create characters
        throk = Character(
            name="Throk",
            char_class="Fighter",
            level=3,
            hp=24, hp_max=24, ac=5,
            stats=Stats(str=17, dex=12, con=15, int=8, wis=10, cha=9),
            equipment=["longsword", "chain mail", "shield"],
            gold=50,
        )
        throk.__dict__['char_id'] = "pc_throk_001"

        zara = Character(
            name="Zara",
            char_class="Thief",
            level=3,
            hp=12, hp_max=12, ac=7,
            stats=Stats(str=10, dex=17, con=12, int=14, wis=11, cha=13),
            equipment=["dagger", "thieves tools"],
            gold=75,
        )
        zara.__dict__['char_id'] = "pc_zara_001"

        # Create events - using actual EventType values from events.py
        events = [
            GameEvent(
                event_id="evt_003_047",
                event_type=EventType.COMBAT_START,
                source="dm",
                content="Four goblins burst from the shadows, ambushing the party!",
                session_id="session_003",
                metadata={
                    "location": "loc_darkwood_entrance",
                    "participants": ["pc_throk_001", "pc_zara_001"],
                    "enemies": ["mon_goblin_darkwood"],
                    "enemy_count": 4,
                }
            ),
            GameEvent(
                event_id="evt_003_048",
                event_type=EventType.PLAYER_ACTION,
                source="pc_throk_001",
                content="I charge at the nearest goblin with my longsword!",
                session_id="session_003",
                metadata={
                    "location": "loc_darkwood_entrance",
                    "participants": ["pc_throk_001"],
                }
            ),
            GameEvent(
                event_id="evt_003_049",
                event_type=EventType.DICE_ROLL,
                source="system",
                content="Throk attacks: d20+2 = 18, hits! Damage: 1d8+2 = 7",
                session_id="session_003",
                metadata={
                    "location": "loc_darkwood_entrance",
                    "participants": ["pc_throk_001"],
                    "killed": ["npc_goblin_enc03_01"],
                }
            ),
        ]

        # Build memory document
        builder = MemoryBuilder(event_window=10)
        memory = builder.build_memory_document(
            pc_id="pc_throk_001",
            character=throk,
            all_characters=[throk, zara],
            events=events,
        )

        # Verify structure
        assert "## LEXICON" in memory
        assert "[PC:pc_throk_001:Throk]" in memory
        assert "[PC:pc_zara_001:Zara]" in memory
        assert "## MEMORY_pc_throk_001" in memory

        # Verify events
        assert "evt_003_047" in memory
        assert "evt_003_048" in memory
        assert "goblin" in memory.lower()

        # Build prompt with memory
        prompt = build_player_prompt(throk, memory=memory)

        # Verify prompt includes everything
        assert "Fighter" in prompt
        assert "## LEXICON" in prompt
        assert "## MEMORY_pc_throk_001" in prompt

        # Token estimate (rough: 4 chars per token)
        estimated_tokens = len(prompt) / 4
        print(f"\nPrompt length: {len(prompt)} chars, ~{estimated_tokens:.0f} tokens")
        assert estimated_tokens < 4000  # Should be reasonable

    def test_zara_sees_different_memory(self):
        """Different PCs get different memory projections."""
        throk = Character(
            name="Throk", char_class="Fighter", level=1,
            hp=8, hp_max=8, ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=[], gold=0,
        )
        throk.__dict__['char_id'] = "pc_throk_001"

        zara = Character(
            name="Zara", char_class="Thief", level=1,
            hp=4, hp_max=4, ac=7,
            stats=Stats(str=10, dex=17, con=12, int=14, wis=11, cha=13),
            equipment=[], gold=0,
        )
        zara.__dict__['char_id'] = "pc_zara_001"

        # Event only Throk was in
        throk_only_event = GameEvent(
            event_id="evt_solo_001",
            event_type=EventType.PLAYER_ACTION,
            source="pc_throk_001",
            content="Throk explores the northern corridor alone",
            session_id="s1",
            metadata={"participants": ["pc_throk_001"]}
        )

        # Event only Zara was in
        zara_only_event = GameEvent(
            event_id="evt_solo_002",
            event_type=EventType.PLAYER_ACTION,
            source="pc_zara_001",
            content="Zara picks the lock on the treasure chest",
            session_id="s1",
            metadata={"participants": ["pc_zara_001"]}
        )

        builder = MemoryBuilder()

        throk_memory = builder.build_memory_document(
            pc_id="pc_throk_001",
            character=throk,
            all_characters=[throk, zara],
            events=[throk_only_event, zara_only_event],
        )

        zara_memory = builder.build_memory_document(
            pc_id="pc_zara_001",
            character=zara,
            all_characters=[throk, zara],
            events=[throk_only_event, zara_only_event],
        )

        # Throk sees his event, not Zara's
        assert "evt_solo_001" in throk_memory
        assert "evt_solo_002" not in throk_memory

        # Zara sees her event, not Throk's
        assert "evt_solo_002" in zara_memory
        assert "evt_solo_001" not in zara_memory
