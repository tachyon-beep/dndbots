"""Tests for DCML memory projection."""

import pytest
from dndbots.memory import MemoryBuilder
from dndbots.models import Character, Stats
from dndbots.events import GameEvent, EventType


class TestLexiconBuilder:
    def test_build_lexicon_from_characters(self):
        """Build lexicon entries from Character objects."""
        chars = [
            Character(
                name="Throk",
                char_class="Fighter",
                level=1,
                hp=8, hp_max=8, ac=5,
                stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
                equipment=[], gold=0,
            ),
            Character(
                name="Zara",
                char_class="Thief",
                level=1,
                hp=4, hp_max=4, ac=7,
                stats=Stats(str=10, dex=17, con=12, int=14, wis=11, cha=13),
                equipment=[], gold=0,
            ),
        ]

        # Note: Character objects have optional char_id attribute
        # Task spec says to use getattr(char, 'char_id', None)
        chars[0].__dict__['char_id'] = "pc_throk_001"
        chars[1].__dict__['char_id'] = "pc_zara_001"

        builder = MemoryBuilder()
        lexicon = builder.build_lexicon(characters=chars)

        assert "[PC:pc_throk_001:Throk]" in lexicon
        assert "[PC:pc_zara_001:Zara]" in lexicon

    def test_build_lexicon_includes_header(self):
        """Lexicon block has ## LEXICON header."""
        builder = MemoryBuilder()
        lexicon = builder.build_lexicon(characters=[])

        assert lexicon.startswith("## LEXICON\n")


class TestEventRenderer:
    def test_render_combat_event(self):
        """Combat events render with participants and outcomes."""
        event = GameEvent(
            event_id="evt_003_047",
            event_type=EventType.COMBAT_START,
            source="dm",
            content="Goblin ambush at cave entrance",
            session_id="session_001",
            metadata={
                "location": "loc_darkwood_entrance",
                "participants": ["pc_throk_001", "pc_zara_001"],
                "enemies": ["mon_goblin_darkwood"],
                "enemy_count": 4,
            }
        )

        builder = MemoryBuilder()
        dcml = builder.render_event(event)

        assert "EVT:evt_003_047 @ loc_darkwood_entrance" in dcml
        assert "pc_throk_001" in dcml
        assert "mon_goblin_darkwood" in dcml

    def test_render_player_action_event(self):
        """Player actions render with summary."""
        event = GameEvent(
            event_id="evt_003_048",
            event_type=EventType.PLAYER_ACTION,
            source="pc_throk_001",
            content="I search the goblin bodies for loot",
            session_id="session_001",
            metadata={"location": "loc_darkwood_entrance"}
        )

        builder = MemoryBuilder()
        dcml = builder.render_event(event)

        assert "EVT:evt_003_048" in dcml
        assert "search" in dcml.lower() or "loot" in dcml.lower()


class TestMemoryProjection:
    def test_build_pc_memory_includes_header(self):
        """PC memory has ## MEMORY_<id> header."""
        builder = MemoryBuilder()
        memory = builder.build_pc_memory(
            pc_id="pc_throk_001",
            character=Character(
                name="Throk",
                char_class="Fighter",
                level=3,
                hp=24, hp_max=24, ac=5,
                stats=Stats(str=17, dex=12, con=15, int=8, wis=10, cha=9),
                equipment=["longsword", "chain mail"],
                gold=50,
            ),
            events=[],
        )

        assert "## MEMORY_pc_throk_001" in memory

    def test_build_pc_memory_includes_core_facts(self):
        """PC memory includes class, level, key traits."""
        builder = MemoryBuilder()
        memory = builder.build_pc_memory(
            pc_id="pc_throk_001",
            character=Character(
                name="Throk",
                char_class="Fighter",
                level=3,
                hp=24, hp_max=24, ac=5,
                stats=Stats(str=17, dex=12, con=15, int=8, wis=10, cha=9),
                equipment=["longsword"],
                gold=50,
            ),
            events=[],
        )

        assert "class->FTR" in memory or "class->Fighter" in memory
        assert "level->3" in memory

    def test_build_pc_memory_filters_events_by_participation(self):
        """PC only sees events they participated in."""
        throk_event = GameEvent(
            event_id="evt_001",
            event_type=EventType.PLAYER_ACTION,
            source="pc_throk_001",
            content="Throk attacks",
            session_id="s1",
            metadata={"participants": ["pc_throk_001"]}
        )
        zara_event = GameEvent(
            event_id="evt_002",
            event_type=EventType.PLAYER_ACTION,
            source="pc_zara_001",
            content="Zara sneaks",
            session_id="s1",
            metadata={"participants": ["pc_zara_001"]}  # Throk not present
        )

        builder = MemoryBuilder()
        memory = builder.build_pc_memory(
            pc_id="pc_throk_001",
            character=Character(
                name="Throk", char_class="Fighter", level=1,
                hp=8, hp_max=8, ac=5,
                stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
                equipment=[], gold=0,
            ),
            events=[throk_event, zara_event],
        )

        assert "evt_001" in memory
        assert "evt_002" not in memory  # Throk wasn't there


class TestMemoryDocument:
    def test_build_full_memory_document(self):
        """Full memory doc has lexicon + PC memory."""
        char = Character(
            name="Throk",
            char_class="Fighter",
            level=1,
            hp=8, hp_max=8, ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=["longsword"],
            gold=25,
        )
        char.__dict__['char_id'] = "pc_throk_001"

        builder = MemoryBuilder()
        doc = builder.build_memory_document(
            pc_id="pc_throk_001",
            character=char,
            all_characters=[char],
            events=[],
        )

        assert "## LEXICON" in doc
        assert "[PC:pc_throk_001:Throk]" in doc
        assert "## MEMORY_pc_throk_001" in doc

    def test_memory_document_token_estimate(self):
        """Memory documents should stay under token budget."""
        char = Character(
            name="Throk",
            char_class="Fighter",
            level=1,
            hp=8, hp_max=8, ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=["longsword"],
            gold=25,
        )

        # Simulate 10 events
        events = [
            GameEvent(
                event_id=f"evt_{i:03d}",
                event_type=EventType.PLAYER_ACTION,
                source="pc_throk_001",
                content=f"Action {i} " * 20,  # ~80 chars each
                session_id="s1",
                metadata={"participants": ["pc_throk_001"]}
            )
            for i in range(10)
        ]

        builder = MemoryBuilder()
        doc = builder.build_memory_document(
            pc_id="pc_throk_001",
            character=char,
            all_characters=[char],
            events=events,
        )

        # Rough estimate: 4 chars per token
        estimated_tokens = len(doc) / 4
        assert estimated_tokens < 2000  # Should fit easily
