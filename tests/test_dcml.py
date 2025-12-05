"""Tests for DCML (D&D Condensed Memory Language)."""

import pytest
from dndbots.dcml import DCMLCategory, render_lexicon_entry, render_relation, DCMLOp, render_properties


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


class TestDCMLRelations:
    def test_render_located_at(self):
        """@ operator for location."""
        rel = render_relation("pc_throk_001", DCMLOp.AT, "loc_darkwood_cave")
        assert rel == "pc_throk_001 @ loc_darkwood_cave"

    def test_render_member_of(self):
        """'in' operator for membership."""
        rel = render_relation("pc_throk_001", DCMLOp.IN, "fac_party_001")
        assert rel == "pc_throk_001 in fac_party_001"

    def test_render_contains(self):
        """> operator for containment."""
        rel = render_relation("loc_cave_main", DCMLOp.CONTAINS, "loc_cave_room_02")
        assert rel == "loc_cave_main > loc_cave_room_02"

    def test_render_leads_to(self):
        """-> operator for causality."""
        rel = render_relation("evt_003_047", DCMLOp.LEADS_TO, "evt_003_048")
        assert rel == "evt_003_047 -> evt_003_048"

    def test_render_caused_by(self):
        """<- operator for origin."""
        rel = render_relation("fac_mages_guild", DCMLOp.CAUSED_BY, "race_elves")
        assert rel == "fac_mages_guild <- race_elves"


class TestDCMLProperties:
    def test_render_simple_properties(self):
        """Properties use ::key->value format."""
        props = render_properties("pc_throk_001", {"class": "FTR", "level": 3})
        assert props == "pc_throk_001::class->FTR,level->3"

    def test_render_stats_properties(self):
        """Stats can be rendered compactly."""
        props = render_properties("pc_throk_001", {
            "stats": "STR17,DEX12,CON15,INT8,WIS10,CHA9"
        })
        assert props == "pc_throk_001::stats->STR17,DEX12,CON15,INT8,WIS10,CHA9"

    def test_render_hp_delta(self):
        """HP changes use hpD notation."""
        props = render_properties("pc_throk_001", {"hpD": -12})
        assert props == "pc_throk_001::hpD->-12"

    def test_render_tags(self):
        """Tags are comma-separated."""
        props = render_properties("pc_throk_001", {
            "tags": ["reckless", "protective"]
        })
        assert props == 'pc_throk_001::tags->"reckless","protective"'
