"""Tests for DCML (D&D Condensed Memory Language)."""

import pytest
from dndbots.dcml import DCMLCategory, render_lexicon_entry


class TestDCMLEntity:
    def test_render_lexicon_entry_pc(self):
        """Lexicon entries use [CATEGORY:ID:Name] format."""
        entry = render_lexicon_entry(
            category=DCMLCategory.PC,
            uid="pc_throk_001",
            name="Throk"
        )
        assert entry == "[PC:pc_throk_001:Throk]"

    def test_render_lexicon_entry_npc(self):
        entry = render_lexicon_entry(
            category=DCMLCategory.NPC,
            uid="npc_grimfang_001",
            name="Grimfang"
        )
        assert entry == "[NPC:npc_grimfang_001:Grimfang]"

    def test_render_lexicon_entry_location(self):
        entry = render_lexicon_entry(
            category=DCMLCategory.LOC,
            uid="loc_darkwood_cave",
            name="DarkwoodCave"
        )
        assert entry == "[LOC:loc_darkwood_cave:DarkwoodCave]"
