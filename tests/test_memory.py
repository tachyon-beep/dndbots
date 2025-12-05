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
