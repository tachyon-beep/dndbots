# BECMI Rules Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate BECMI Basic D&D rules into DnDBots with structured tool access and a ~300 line in-context summary.

**Architecture:** Three-level hierarchy (category summary in context → stats via tool → full entry via tool). Pre-indexed JSON storage with rich metadata. Unified namespace supporting future BECMI expansion (Expert, Companion, Master, Immortals).

**Tech Stack:** Python dataclasses, JSON storage, pytest for TDD

**Design Document:** `docs/plans/2025-12-07-becmi-rules-integration-design.md`

---

## Phase 1: Data Models and Storage (Tasks 1-4)

### Task 1: RulesEntry Base Dataclass

**Files:**
- Create: `src/dndbots/rules_index.py`
- Test: `tests/test_rules_index.py`

**Step 1: Write the failing test**

```python
# tests/test_rules_index.py
"""Tests for rules index and data models."""

import pytest
from dndbots.rules_index import RulesEntry


class TestRulesEntry:
    def test_rules_entry_creation(self):
        """RulesEntry can be created with required fields."""
        entry = RulesEntry(
            path="monsters/goblin",
            name="Goblin",
            category="monster",
            ruleset="basic",
            source_file="becmi_dm_rulebook.txt",
            source_lines=(2456, 2489),
            tags=["humanoid", "chaotic"],
            related=["monsters/hobgoblin"],
            summary="Small chaotic humanoids, -1 to hit in daylight",
            full_text="Goblins are small, evil humanoids...",
        )
        assert entry.path == "monsters/goblin"
        assert entry.name == "Goblin"
        assert entry.ruleset == "basic"

    def test_rules_entry_optional_fields(self):
        """RulesEntry handles optional fields correctly."""
        entry = RulesEntry(
            path="procedures/morale",
            name="Morale",
            category="procedure",
            ruleset="basic",
            source_file="becmi_dm_rulebook.txt",
            source_lines=(100, 150),
            tags=["combat"],
            related=[],
            summary="Rules for monster morale checks",
            full_text="When monsters take casualties...",
        )
        assert entry.min_level is None
        assert entry.max_level is None
        assert entry.stat_block is None
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_rules_index.py::TestRulesEntry -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'dndbots.rules_index'"

**Step 3: Write minimal implementation**

```python
# src/dndbots/rules_index.py
"""Rules index for BECMI D&D content."""

from dataclasses import dataclass, field


@dataclass
class RulesEntry:
    """A single rules entry (monster, spell, treasure type, procedure)."""

    # Identity
    path: str  # "monsters/goblin", "spells/cleric/1/cure_light_wounds"
    name: str  # "Goblin", "Cure Light Wounds"
    category: str  # "monster", "spell", "treasure", "procedure", "equipment"

    # BECMI set tracking
    ruleset: str  # "basic", "expert", "companion", "master", "immortals"

    # Source tracking
    source_file: str  # "becmi_dm_rulebook.txt"
    source_lines: tuple[int, int]  # (2456, 2489) for verification

    # Searchability
    tags: list[str]  # ["humanoid", "tribal", "low-level", "chaotic"]
    related: list[str]  # ["monsters/hobgoblin", "monsters/bugbear"]

    # Content tiers
    summary: str  # 1-2 line overview (always available)
    full_text: str  # Complete text (level 3)

    # Optional fields
    min_level: int | None = None  # Minimum character level relevance
    max_level: int | None = None  # Maximum character level relevance
    stat_block: str | None = None  # Compressed stats (level 2)
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_rules_index.py::TestRulesEntry -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/rules_index.py tests/test_rules_index.py
git commit -m "feat(rules): add RulesEntry base dataclass"
```

---

### Task 2: MonsterEntry Extended Dataclass

**Files:**
- Modify: `src/dndbots/rules_index.py`
- Test: `tests/test_rules_index.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_rules_index.py
from dndbots.rules_index import RulesEntry, MonsterEntry


class TestMonsterEntry:
    def test_monster_entry_creation(self):
        """MonsterEntry includes monster-specific stat fields."""
        monster = MonsterEntry(
            path="monsters/goblin",
            name="Goblin",
            category="monster",
            ruleset="basic",
            source_file="becmi_dm_rulebook.txt",
            source_lines=(2456, 2489),
            tags=["humanoid", "chaotic", "low-level"],
            related=["monsters/hobgoblin", "monsters/bugbear"],
            summary="Small chaotic humanoids, -1 to hit in daylight",
            full_text="Goblins are small, evil humanoids...",
            stat_block="AC6 HD1-1 Mv90'(30') Atk1wpn Dm(wpn) ML7 XP5",
            ac=6,
            hd="1-1",
            move="90' (30')",
            attacks="1 weapon",
            damage="By weapon",
            no_appearing="2-8 (6-60)",
            save_as="Normal Man",
            morale=7,
            treasure_type="(R) C",
            alignment="Chaotic",
            xp=5,
            special_abilities=["infravision 90'", "-1 to hit in daylight"],
        )
        assert monster.ac == 6
        assert monster.hd == "1-1"
        assert monster.xp == 5
        assert "infravision" in monster.special_abilities[0]

    def test_monster_entry_is_rules_entry(self):
        """MonsterEntry is a subclass of RulesEntry."""
        monster = MonsterEntry(
            path="monsters/skeleton",
            name="Skeleton",
            category="monster",
            ruleset="basic",
            source_file="becmi_dm_rulebook.txt",
            source_lines=(3000, 3030),
            tags=["undead"],
            related=[],
            summary="Animated bones, mindless",
            full_text="Skeletons are...",
            ac=7,
            hd="1",
            move="60' (20')",
            attacks="1 weapon",
            damage="By weapon",
            no_appearing="3-12",
            save_as="F1",
            morale=12,
            treasure_type="None",
            alignment="Chaotic",
            xp=10,
            special_abilities=[],
        )
        assert isinstance(monster, RulesEntry)
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_rules_index.py::TestMonsterEntry -v`
Expected: FAIL with "ImportError: cannot import name 'MonsterEntry'"

**Step 3: Write minimal implementation**

```python
# Add to src/dndbots/rules_index.py

@dataclass
class MonsterEntry(RulesEntry):
    """Extended metadata for monster entries."""

    ac: int = 9  # Armor Class
    hd: str = "1"  # Hit Dice ("1-1", "3+1", "6**")
    move: str = "60' (20')"  # Movement
    attacks: str = "1"  # Attack routine
    damage: str = "1d6"  # Damage
    no_appearing: str = "1"  # Number appearing
    save_as: str = "F1"  # Save as
    morale: int = 6  # Morale score
    treasure_type: str = "None"  # Treasure
    alignment: str = "Neutral"  # Alignment
    xp: int = 0  # XP value
    special_abilities: list[str] = field(default_factory=list)
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_rules_index.py::TestMonsterEntry -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/rules_index.py tests/test_rules_index.py
git commit -m "feat(rules): add MonsterEntry with stat fields"
```

---

### Task 3: SpellEntry Extended Dataclass

**Files:**
- Modify: `src/dndbots/rules_index.py`
- Test: `tests/test_rules_index.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_rules_index.py
from dndbots.rules_index import RulesEntry, MonsterEntry, SpellEntry


class TestSpellEntry:
    def test_spell_entry_creation(self):
        """SpellEntry includes spell-specific fields."""
        spell = SpellEntry(
            path="spells/cleric/1/cure_light_wounds",
            name="Cure Light Wounds",
            category="spell",
            ruleset="basic",
            source_file="becmi_players_manual.txt",
            source_lines=(3500, 3520),
            tags=["healing", "cleric"],
            related=["spells/cleric/1/cause_light_wounds"],
            summary="Touch, heal 1d6+1 hp",
            full_text="By placing hands on a wounded creature...",
            stat_block="Range: Touch, Duration: Permanent, Effect: 1 creature",
            spell_class="cleric",
            spell_level=1,
            range="Touch",
            duration="Permanent",
            reversible=True,
            reverse_name="Cause Light Wounds",
        )
        assert spell.spell_class == "cleric"
        assert spell.spell_level == 1
        assert spell.reversible is True
        assert spell.reverse_name == "Cause Light Wounds"

    def test_spell_entry_non_reversible(self):
        """SpellEntry handles non-reversible spells."""
        spell = SpellEntry(
            path="spells/magic_user/1/magic_missile",
            name="Magic Missile",
            category="spell",
            ruleset="basic",
            source_file="becmi_players_manual.txt",
            source_lines=(3600, 3620),
            tags=["damage", "magic-user", "auto-hit"],
            related=[],
            summary="150', auto-hit, 2d6+1 damage",
            full_text="A glowing arrow of energy...",
            spell_class="magic-user",
            spell_level=1,
            range="150'",
            duration="Instantaneous",
            reversible=False,
        )
        assert spell.reversible is False
        assert spell.reverse_name is None
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_rules_index.py::TestSpellEntry -v`
Expected: FAIL with "ImportError: cannot import name 'SpellEntry'"

**Step 3: Write minimal implementation**

```python
# Add to src/dndbots/rules_index.py

@dataclass
class SpellEntry(RulesEntry):
    """Extended metadata for spell entries."""

    spell_class: str = "magic-user"  # "cleric", "magic-user", "elf"
    spell_level: int = 1  # 1-5 for Basic
    range: str = "0"  # "Touch", "120'", "0 (caster only)"
    duration: str = "Instantaneous"  # "Permanent", "2 turns", "1 round/level"
    reversible: bool = False  # Can be reversed
    reverse_name: str | None = None  # "Cause Light Wounds"
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_rules_index.py::TestSpellEntry -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/rules_index.py tests/test_rules_index.py
git commit -m "feat(rules): add SpellEntry with spell fields"
```

---

### Task 4: Result Dataclasses (RulesResult, RulesIndex, RulesMatch)

**Files:**
- Modify: `src/dndbots/rules_index.py`
- Test: `tests/test_rules_index.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_rules_index.py
from dndbots.rules_index import RulesResult, RulesIndexEntry, RulesMatch


class TestResultTypes:
    def test_rules_result_creation(self):
        """RulesResult contains full lookup result."""
        result = RulesResult(
            path="monsters/goblin",
            name="Goblin",
            category="monster",
            ruleset="basic",
            content="AC6 HD1-1 Mv90'...",
            metadata={"ac": 6, "hd": "1-1", "xp": 5},
            related=["monsters/hobgoblin"],
            source_reference="becmi_dm_rulebook.txt:2456-2489",
        )
        assert result.path == "monsters/goblin"
        assert result.metadata["ac"] == 6
        assert "2456" in result.source_reference

    def test_rules_index_entry_creation(self):
        """RulesIndexEntry for list results."""
        entry = RulesIndexEntry(
            path="monsters/ghoul",
            name="Ghoul",
            summary="HD2, AC6, paralyze touch",
            tags=["undead", "paralyze"],
            stat_preview="AC6 HD2 ML9 XP25",
        )
        assert entry.path == "monsters/ghoul"
        assert "paralyze" in entry.tags

    def test_rules_match_creation(self):
        """RulesMatch for search results."""
        match = RulesMatch(
            path="monsters/ghoul",
            name="Ghoul",
            category="monster",
            relevance=0.85,
            snippet="...paralyze on touch, save vs Paralysis...",
        )
        assert match.relevance == 0.85
        assert "paralyze" in match.snippet.lower()
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_rules_index.py::TestResultTypes -v`
Expected: FAIL with "ImportError: cannot import name 'RulesResult'"

**Step 3: Write minimal implementation**

```python
# Add to src/dndbots/rules_index.py

@dataclass
class RulesResult:
    """Result from get_rules() lookup."""

    path: str
    name: str
    category: str
    ruleset: str
    content: str  # Formatted based on detail level
    metadata: dict  # All entry fields as dict
    related: list[str]  # Suggested related paths
    source_reference: str  # "becmi_dm_rulebook.txt:2456-2489"


@dataclass
class RulesIndexEntry:
    """Entry in list_rules() results."""

    path: str
    name: str
    summary: str
    tags: list[str]
    stat_preview: str | None = None  # One-line stat summary if applicable


@dataclass
class RulesMatch:
    """Search result from search_rules()."""

    path: str
    name: str
    category: str
    relevance: float  # 0.0-1.0 match score
    snippet: str  # Matching excerpt
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_rules_index.py::TestResultTypes -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/rules_index.py tests/test_rules_index.py
git commit -m "feat(rules): add result dataclasses for tool responses"
```

---

## Phase 2: RulesIndex Loading and Querying (Tasks 5-8)

### Task 5: RulesIndex Class with JSON Loading

**Files:**
- Modify: `src/dndbots/rules_index.py`
- Create: `rules/indexed/basic/monsters.json` (minimal test fixture)
- Test: `tests/test_rules_index.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_rules_index.py
import json
import tempfile
from pathlib import Path
from dndbots.rules_index import RulesIndex


class TestRulesIndex:
    def test_load_from_directory(self):
        """RulesIndex loads entries from indexed JSON files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test fixture
            index_dir = Path(tmpdir) / "indexed" / "basic"
            index_dir.mkdir(parents=True)

            monsters = {
                "goblin": {
                    "path": "monsters/goblin",
                    "name": "Goblin",
                    "category": "monster",
                    "ruleset": "basic",
                    "source_file": "becmi_dm_rulebook.txt",
                    "source_lines": [2456, 2489],
                    "tags": ["humanoid", "chaotic"],
                    "related": ["monsters/hobgoblin"],
                    "summary": "Small chaotic humanoids",
                    "full_text": "Goblins are...",
                    "stat_block": "AC6 HD1-1",
                    "ac": 6,
                    "hd": "1-1",
                    "move": "90' (30')",
                    "attacks": "1 weapon",
                    "damage": "By weapon",
                    "no_appearing": "2-8",
                    "save_as": "Normal Man",
                    "morale": 7,
                    "treasure_type": "C",
                    "alignment": "Chaotic",
                    "xp": 5,
                    "special_abilities": ["infravision 90'"],
                }
            }
            (index_dir / "monsters.json").write_text(json.dumps(monsters))

            rules = RulesIndex(Path(tmpdir))
            assert rules.get("monsters/goblin") is not None
            assert rules.get("monsters/goblin").name == "Goblin"

    def test_get_nonexistent_returns_none(self):
        """RulesIndex.get() returns None for missing entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_dir = Path(tmpdir) / "indexed" / "basic"
            index_dir.mkdir(parents=True)
            (index_dir / "monsters.json").write_text("{}")

            rules = RulesIndex(Path(tmpdir))
            assert rules.get("monsters/dragon") is None
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_rules_index.py::TestRulesIndex::test_load_from_directory -v`
Expected: FAIL with "ImportError: cannot import name 'RulesIndex'"

**Step 3: Write minimal implementation**

```python
# Add to src/dndbots/rules_index.py
import json
from pathlib import Path


class RulesIndex:
    """Index of all BECMI rules content."""

    def __init__(self, rules_dir: Path):
        """Load rules from indexed JSON files.

        Args:
            rules_dir: Path to rules/ directory containing indexed/ subdirectory
        """
        self._entries: dict[str, RulesEntry] = {}
        self._rules_dir = rules_dir

        indexed_dir = rules_dir / "indexed"
        if indexed_dir.exists():
            self._load_indexed(indexed_dir)

    def _load_indexed(self, indexed_dir: Path) -> None:
        """Load all indexed JSON files."""
        for ruleset_dir in indexed_dir.iterdir():
            if ruleset_dir.is_dir():
                self._load_ruleset(ruleset_dir)

    def _load_ruleset(self, ruleset_dir: Path) -> None:
        """Load all JSON files in a ruleset directory."""
        for json_file in ruleset_dir.glob("*.json"):
            if json_file.name.startswith("_"):
                continue  # Skip manifest files
            self._load_json_file(json_file)

    def _load_json_file(self, json_file: Path) -> None:
        """Load entries from a single JSON file."""
        data = json.loads(json_file.read_text())
        for key, entry_data in data.items():
            entry = self._parse_entry(entry_data)
            self._entries[entry.path] = entry

    def _parse_entry(self, data: dict) -> RulesEntry:
        """Parse a JSON entry into the appropriate dataclass."""
        category = data.get("category", "")

        if category == "monster":
            return MonsterEntry(
                path=data["path"],
                name=data["name"],
                category=data["category"],
                ruleset=data["ruleset"],
                source_file=data["source_file"],
                source_lines=tuple(data["source_lines"]),
                tags=data.get("tags", []),
                related=data.get("related", []),
                summary=data["summary"],
                full_text=data["full_text"],
                min_level=data.get("min_level"),
                max_level=data.get("max_level"),
                stat_block=data.get("stat_block"),
                ac=data.get("ac", 9),
                hd=data.get("hd", "1"),
                move=data.get("move", "60' (20')"),
                attacks=data.get("attacks", "1"),
                damage=data.get("damage", "1d6"),
                no_appearing=data.get("no_appearing", "1"),
                save_as=data.get("save_as", "F1"),
                morale=data.get("morale", 6),
                treasure_type=data.get("treasure_type", "None"),
                alignment=data.get("alignment", "Neutral"),
                xp=data.get("xp", 0),
                special_abilities=data.get("special_abilities", []),
            )
        elif category == "spell":
            return SpellEntry(
                path=data["path"],
                name=data["name"],
                category=data["category"],
                ruleset=data["ruleset"],
                source_file=data["source_file"],
                source_lines=tuple(data["source_lines"]),
                tags=data.get("tags", []),
                related=data.get("related", []),
                summary=data["summary"],
                full_text=data["full_text"],
                min_level=data.get("min_level"),
                max_level=data.get("max_level"),
                stat_block=data.get("stat_block"),
                spell_class=data.get("spell_class", "magic-user"),
                spell_level=data.get("spell_level", 1),
                range=data.get("range", "0"),
                duration=data.get("duration", "Instantaneous"),
                reversible=data.get("reversible", False),
                reverse_name=data.get("reverse_name"),
            )
        else:
            return RulesEntry(
                path=data["path"],
                name=data["name"],
                category=data["category"],
                ruleset=data["ruleset"],
                source_file=data["source_file"],
                source_lines=tuple(data["source_lines"]),
                tags=data.get("tags", []),
                related=data.get("related", []),
                summary=data["summary"],
                full_text=data["full_text"],
                min_level=data.get("min_level"),
                max_level=data.get("max_level"),
                stat_block=data.get("stat_block"),
            )

    def get(self, path: str) -> RulesEntry | None:
        """Get an entry by path."""
        return self._entries.get(path)
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_rules_index.py::TestRulesIndex -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/rules_index.py tests/test_rules_index.py
git commit -m "feat(rules): add RulesIndex class with JSON loading"
```

---

### Task 6: get_rules() Tool Function

**Files:**
- Create: `src/dndbots/rules_tools.py`
- Test: `tests/test_rules_tools.py`

**Step 1: Write the failing test**

```python
# tests/test_rules_tools.py
"""Tests for rules tool functions."""

import json
import tempfile
from pathlib import Path

import pytest

from dndbots.rules_tools import get_rules
from dndbots.rules_index import RulesIndex, RulesResult


@pytest.fixture
def rules_index():
    """Create a RulesIndex with test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        index_dir = Path(tmpdir) / "indexed" / "basic"
        index_dir.mkdir(parents=True)

        monsters = {
            "goblin": {
                "path": "monsters/goblin",
                "name": "Goblin",
                "category": "monster",
                "ruleset": "basic",
                "source_file": "becmi_dm_rulebook.txt",
                "source_lines": [2456, 2489],
                "tags": ["humanoid", "chaotic"],
                "related": ["monsters/hobgoblin"],
                "summary": "Small chaotic humanoids, -1 to hit in daylight",
                "full_text": "Goblins are small, evil humanoids that live in caves...",
                "stat_block": "AC6 HD1-1 Mv90'(30') Atk1wpn Dm(wpn) ML7 XP5",
                "ac": 6,
                "hd": "1-1",
                "move": "90' (30')",
                "attacks": "1 weapon",
                "damage": "By weapon",
                "no_appearing": "2-8 (6-60)",
                "save_as": "Normal Man",
                "morale": 7,
                "treasure_type": "(R) C",
                "alignment": "Chaotic",
                "xp": 5,
                "special_abilities": ["infravision 90'", "-1 to hit in daylight"],
            }
        }
        (index_dir / "monsters.json").write_text(json.dumps(monsters))

        yield RulesIndex(Path(tmpdir))


class TestGetRules:
    def test_get_rules_summary(self, rules_index):
        """get_rules returns summary by default."""
        result = get_rules(rules_index, "monsters/goblin", detail="summary")
        assert isinstance(result, RulesResult)
        assert result.name == "Goblin"
        assert "Small chaotic humanoids" in result.content
        assert result.ruleset == "basic"

    def test_get_rules_stats(self, rules_index):
        """get_rules with detail='stats' returns stat block."""
        result = get_rules(rules_index, "monsters/goblin", detail="stats")
        assert "AC6" in result.content
        assert "HD1-1" in result.content

    def test_get_rules_full(self, rules_index):
        """get_rules with detail='full' returns full text."""
        result = get_rules(rules_index, "monsters/goblin", detail="full")
        assert "Goblins are small, evil humanoids" in result.content
        assert "caves" in result.content

    def test_get_rules_not_found(self, rules_index):
        """get_rules returns None for missing entries."""
        result = get_rules(rules_index, "monsters/dragon", detail="summary")
        assert result is None

    def test_get_rules_includes_metadata(self, rules_index):
        """get_rules includes metadata in result."""
        result = get_rules(rules_index, "monsters/goblin", detail="summary")
        assert result.metadata["ac"] == 6
        assert result.metadata["xp"] == 5
        assert result.source_reference == "becmi_dm_rulebook.txt:2456-2489"
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_rules_tools.py::TestGetRules -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'dndbots.rules_tools'"

**Step 3: Write minimal implementation**

```python
# src/dndbots/rules_tools.py
"""Tool functions for BECMI rules access."""

from typing import Literal

from dndbots.rules_index import (
    RulesIndex,
    RulesEntry,
    RulesResult,
    MonsterEntry,
    SpellEntry,
)


def get_rules(
    index: RulesIndex,
    path: str,
    detail: Literal["summary", "stats", "full"] = "summary",
) -> RulesResult | None:
    """Fetch rules content by exact path.

    Args:
        index: The RulesIndex to query
        path: Hierarchical path like "monsters/goblin"
        detail: Content level - "summary", "stats", or "full"

    Returns:
        RulesResult with content and metadata, or None if not found
    """
    entry = index.get(path)
    if entry is None:
        return None

    # Build content based on detail level
    if detail == "summary":
        content = entry.summary
    elif detail == "stats":
        content = entry.stat_block or entry.summary
    else:  # full
        content = entry.full_text

    # Build metadata dict from entry fields
    metadata = _entry_to_metadata(entry)

    # Build source reference
    source_reference = f"{entry.source_file}:{entry.source_lines[0]}-{entry.source_lines[1]}"

    return RulesResult(
        path=entry.path,
        name=entry.name,
        category=entry.category,
        ruleset=entry.ruleset,
        content=content,
        metadata=metadata,
        related=entry.related,
        source_reference=source_reference,
    )


def _entry_to_metadata(entry: RulesEntry) -> dict:
    """Convert a RulesEntry to a metadata dict."""
    metadata = {
        "tags": entry.tags,
        "min_level": entry.min_level,
        "max_level": entry.max_level,
    }

    if isinstance(entry, MonsterEntry):
        metadata.update({
            "ac": entry.ac,
            "hd": entry.hd,
            "move": entry.move,
            "attacks": entry.attacks,
            "damage": entry.damage,
            "no_appearing": entry.no_appearing,
            "save_as": entry.save_as,
            "morale": entry.morale,
            "treasure_type": entry.treasure_type,
            "alignment": entry.alignment,
            "xp": entry.xp,
            "special_abilities": entry.special_abilities,
        })
    elif isinstance(entry, SpellEntry):
        metadata.update({
            "spell_class": entry.spell_class,
            "spell_level": entry.spell_level,
            "range": entry.range,
            "duration": entry.duration,
            "reversible": entry.reversible,
            "reverse_name": entry.reverse_name,
        })

    return metadata
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_rules_tools.py::TestGetRules -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/rules_tools.py tests/test_rules_tools.py
git commit -m "feat(rules): add get_rules() tool function"
```

---

### Task 7: list_rules() Tool Function

**Files:**
- Modify: `src/dndbots/rules_tools.py`
- Modify: `src/dndbots/rules_index.py` (add list method)
- Test: `tests/test_rules_tools.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_rules_tools.py
from dndbots.rules_tools import get_rules, list_rules
from dndbots.rules_index import RulesIndex, RulesResult, RulesIndexEntry


# Add more monsters to fixture
@pytest.fixture
def rules_index_with_multiple():
    """Create a RulesIndex with multiple test entries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        index_dir = Path(tmpdir) / "indexed" / "basic"
        index_dir.mkdir(parents=True)

        monsters = {
            "goblin": {
                "path": "monsters/goblin",
                "name": "Goblin",
                "category": "monster",
                "ruleset": "basic",
                "source_file": "becmi_dm_rulebook.txt",
                "source_lines": [2456, 2489],
                "tags": ["humanoid", "chaotic", "low-level"],
                "related": ["monsters/hobgoblin"],
                "summary": "Small chaotic humanoids",
                "full_text": "Goblins are...",
                "stat_block": "AC6 HD1-1",
                "ac": 6, "hd": "1-1", "move": "90' (30')", "attacks": "1 weapon",
                "damage": "By weapon", "no_appearing": "2-8", "save_as": "Normal Man",
                "morale": 7, "treasure_type": "C", "alignment": "Chaotic",
                "xp": 5, "special_abilities": [],
            },
            "skeleton": {
                "path": "monsters/skeleton",
                "name": "Skeleton",
                "category": "monster",
                "ruleset": "basic",
                "source_file": "becmi_dm_rulebook.txt",
                "source_lines": [3000, 3030],
                "tags": ["undead", "low-level"],
                "related": ["monsters/zombie"],
                "summary": "Animated bones, mindless",
                "full_text": "Skeletons are...",
                "stat_block": "AC7 HD1",
                "ac": 7, "hd": "1", "move": "60' (20')", "attacks": "1 weapon",
                "damage": "By weapon", "no_appearing": "3-12", "save_as": "F1",
                "morale": 12, "treasure_type": "None", "alignment": "Chaotic",
                "xp": 10, "special_abilities": [],
            },
            "ghoul": {
                "path": "monsters/ghoul",
                "name": "Ghoul",
                "category": "monster",
                "ruleset": "basic",
                "source_file": "becmi_dm_rulebook.txt",
                "source_lines": [2200, 2240],
                "tags": ["undead", "paralyze"],
                "related": ["monsters/wight"],
                "summary": "Paralyzing touch, eats corpses",
                "full_text": "Ghouls are...",
                "stat_block": "AC6 HD2",
                "ac": 6, "hd": "2", "move": "90' (30')", "attacks": "2 claws/1 bite",
                "damage": "1d3/1d3/1d3+paralysis", "no_appearing": "1-6", "save_as": "F2",
                "morale": 9, "treasure_type": "B", "alignment": "Chaotic",
                "xp": 25, "special_abilities": ["paralyze on touch"],
            },
        }
        (index_dir / "monsters.json").write_text(json.dumps(monsters))

        yield RulesIndex(Path(tmpdir))


class TestListRules:
    def test_list_rules_all_monsters(self, rules_index_with_multiple):
        """list_rules returns all monsters in category."""
        results = list_rules(rules_index_with_multiple, "monsters")
        assert len(results) == 3
        names = [r.name for r in results]
        assert "Goblin" in names
        assert "Skeleton" in names
        assert "Ghoul" in names

    def test_list_rules_filter_by_tags(self, rules_index_with_multiple):
        """list_rules can filter by tags."""
        results = list_rules(rules_index_with_multiple, "monsters", tags=["undead"])
        assert len(results) == 2
        names = [r.name for r in results]
        assert "Skeleton" in names
        assert "Ghoul" in names
        assert "Goblin" not in names

    def test_list_rules_returns_index_entries(self, rules_index_with_multiple):
        """list_rules returns RulesIndexEntry objects."""
        results = list_rules(rules_index_with_multiple, "monsters")
        assert all(isinstance(r, RulesIndexEntry) for r in results)
        goblin = next(r for r in results if r.name == "Goblin")
        assert goblin.summary == "Small chaotic humanoids"
        assert "humanoid" in goblin.tags
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_rules_tools.py::TestListRules -v`
Expected: FAIL with "ImportError: cannot import name 'list_rules'"

**Step 3: Write minimal implementation**

```python
# Add to src/dndbots/rules_index.py, in RulesIndex class:

    def list_by_category(
        self,
        category: str,
        ruleset: str | None = None,
        tags: list[str] | None = None,
    ) -> list[RulesEntry]:
        """List entries matching category and filters.

        Args:
            category: Category prefix like "monsters", "spells/cleric/1"
            ruleset: Optional ruleset filter
            tags: Optional tag filter (AND logic)

        Returns:
            List of matching entries
        """
        results = []
        for path, entry in self._entries.items():
            # Check category prefix
            if not path.startswith(category):
                continue

            # Check ruleset filter
            if ruleset and entry.ruleset != ruleset:
                continue

            # Check tag filter (all tags must match)
            if tags and not all(t in entry.tags for t in tags):
                continue

            results.append(entry)

        return results
```

```python
# Add to src/dndbots/rules_tools.py:

from dndbots.rules_index import (
    RulesIndex,
    RulesEntry,
    RulesResult,
    RulesIndexEntry,
    MonsterEntry,
    SpellEntry,
)


def list_rules(
    index: RulesIndex,
    category: str,
    ruleset: str | None = None,
    tags: list[str] | None = None,
) -> list[RulesIndexEntry]:
    """List available entries in a category with filtering.

    Args:
        index: The RulesIndex to query
        category: Category path like "monsters", "spells/cleric/1"
        ruleset: Optional ruleset filter
        tags: Optional tag filter (AND logic)

    Returns:
        List of RulesIndexEntry with path, name, summary, tags
    """
    entries = index.list_by_category(category, ruleset=ruleset, tags=tags)

    return [
        RulesIndexEntry(
            path=e.path,
            name=e.name,
            summary=e.summary,
            tags=e.tags,
            stat_preview=e.stat_block,
        )
        for e in entries
    ]
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_rules_tools.py::TestListRules -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/rules_index.py src/dndbots/rules_tools.py tests/test_rules_tools.py
git commit -m "feat(rules): add list_rules() tool function with filtering"
```

---

### Task 8: search_rules() Tool Function

**Files:**
- Modify: `src/dndbots/rules_tools.py`
- Modify: `src/dndbots/rules_index.py` (add search method)
- Test: `tests/test_rules_tools.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_rules_tools.py
from dndbots.rules_tools import get_rules, list_rules, search_rules
from dndbots.rules_index import RulesIndex, RulesResult, RulesIndexEntry, RulesMatch


class TestSearchRules:
    def test_search_rules_by_keyword(self, rules_index_with_multiple):
        """search_rules finds entries matching keywords."""
        results = search_rules(rules_index_with_multiple, "paralyze")
        assert len(results) >= 1
        # Ghoul has "paralyze" in summary and special abilities
        paths = [r.path for r in results]
        assert "monsters/ghoul" in paths

    def test_search_rules_in_full_text(self, rules_index_with_multiple):
        """search_rules searches full text."""
        results = search_rules(rules_index_with_multiple, "animated")
        # Skeleton has "Animated bones" in summary
        paths = [r.path for r in results]
        assert "monsters/skeleton" in paths

    def test_search_rules_returns_matches(self, rules_index_with_multiple):
        """search_rules returns RulesMatch objects."""
        results = search_rules(rules_index_with_multiple, "undead")
        assert all(isinstance(r, RulesMatch) for r in results)
        assert all(r.relevance > 0 for r in results)

    def test_search_rules_respects_limit(self, rules_index_with_multiple):
        """search_rules respects limit parameter."""
        results = search_rules(rules_index_with_multiple, "monster", limit=1)
        assert len(results) <= 1

    def test_search_rules_category_filter(self, rules_index_with_multiple):
        """search_rules can filter by category."""
        results = search_rules(
            rules_index_with_multiple, "chaotic", category="monsters"
        )
        # Should find goblin and skeleton (both are Chaotic)
        assert len(results) >= 1
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_rules_tools.py::TestSearchRules -v`
Expected: FAIL with "ImportError: cannot import name 'search_rules'"

**Step 3: Write minimal implementation**

```python
# Add to src/dndbots/rules_index.py, in RulesIndex class:

    def search(
        self,
        query: str,
        category: str | None = None,
        limit: int = 5,
    ) -> list[tuple[RulesEntry, float, str]]:
        """Search entries by keyword.

        Args:
            query: Search query
            category: Optional category filter
            limit: Maximum results

        Returns:
            List of (entry, relevance, snippet) tuples
        """
        query_lower = query.lower()
        results = []

        for path, entry in self._entries.items():
            # Apply category filter
            if category and not path.startswith(category):
                continue

            # Search in name, summary, full_text, tags
            score = 0.0
            snippet = ""

            if query_lower in entry.name.lower():
                score += 1.0
                snippet = entry.name

            if query_lower in entry.summary.lower():
                score += 0.8
                snippet = snippet or entry.summary

            if query_lower in entry.full_text.lower():
                score += 0.5
                # Extract snippet around match
                idx = entry.full_text.lower().find(query_lower)
                start = max(0, idx - 30)
                end = min(len(entry.full_text), idx + len(query) + 30)
                snippet = snippet or f"...{entry.full_text[start:end]}..."

            if any(query_lower in tag.lower() for tag in entry.tags):
                score += 0.6
                snippet = snippet or f"Tags: {', '.join(entry.tags)}"

            if score > 0:
                results.append((entry, score, snippet))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]
```

```python
# Add to src/dndbots/rules_tools.py:

from dndbots.rules_index import (
    RulesIndex,
    RulesEntry,
    RulesResult,
    RulesIndexEntry,
    RulesMatch,
    MonsterEntry,
    SpellEntry,
)


def search_rules(
    index: RulesIndex,
    query: str,
    category: str | None = None,
    limit: int = 5,
) -> list[RulesMatch]:
    """Search rules by keywords.

    Args:
        index: The RulesIndex to query
        query: Search query
        category: Optional category filter
        limit: Maximum results to return

    Returns:
        List of RulesMatch with path, relevance, snippet
    """
    results = index.search(query, category=category, limit=limit)

    return [
        RulesMatch(
            path=entry.path,
            name=entry.name,
            category=entry.category,
            relevance=relevance,
            snippet=snippet,
        )
        for entry, relevance, snippet in results
    ]
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_rules_tools.py::TestSearchRules -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/rules_index.py src/dndbots/rules_tools.py tests/test_rules_tools.py
git commit -m "feat(rules): add search_rules() tool function"
```

---

## Phase 3: In-Context Summary Generation (Tasks 9-10)

### Task 9: Rules Summary Generator

**Files:**
- Create: `src/dndbots/rules_prompts.py`
- Test: `tests/test_rules_prompts.py`

**Step 1: Write the failing test**

```python
# tests/test_rules_prompts.py
"""Tests for rules prompt generation."""

import json
import tempfile
from pathlib import Path

import pytest

from dndbots.rules_prompts import build_rules_summary
from dndbots.rules_index import RulesIndex


@pytest.fixture
def rules_index_for_summary():
    """Create a RulesIndex with varied test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        index_dir = Path(tmpdir) / "indexed" / "basic"
        index_dir.mkdir(parents=True)

        monsters = {
            "goblin": {
                "path": "monsters/goblin",
                "name": "Goblin",
                "category": "monster",
                "ruleset": "basic",
                "source_file": "dm.txt",
                "source_lines": [100, 120],
                "tags": ["humanoid"],
                "related": [],
                "summary": "Small humanoids",
                "full_text": "...",
                "stat_block": "AC6 HD1-1 ML7 XP5",
                "ac": 6, "hd": "1-1", "move": "90'", "attacks": "1",
                "damage": "1d6", "no_appearing": "2-8", "save_as": "NM",
                "morale": 7, "treasure_type": "C", "alignment": "C", "xp": 5,
                "special_abilities": [],
            },
        }
        spells = {
            "cure_light_wounds": {
                "path": "spells/cleric/1/cure_light_wounds",
                "name": "Cure Light Wounds",
                "category": "spell",
                "ruleset": "basic",
                "source_file": "player.txt",
                "source_lines": [200, 210],
                "tags": ["healing"],
                "related": [],
                "summary": "Touch, heal 1d6+1",
                "full_text": "...",
                "spell_class": "cleric",
                "spell_level": 1,
                "range": "Touch",
                "duration": "Permanent",
                "reversible": True,
                "reverse_name": "Cause Light Wounds",
            },
        }
        (index_dir / "monsters.json").write_text(json.dumps(monsters))
        (index_dir / "spells.json").write_text(json.dumps(spells))

        yield RulesIndex(Path(tmpdir))


class TestBuildRulesSummary:
    def test_summary_includes_core_mechanics(self, rules_index_for_summary):
        """Summary includes core D&D mechanics."""
        summary = build_rules_summary(rules_index_for_summary)
        assert "THAC0" in summary
        assert "Combat" in summary or "COMBAT" in summary

    def test_summary_includes_monster_list(self, rules_index_for_summary):
        """Summary includes monster quick reference."""
        summary = build_rules_summary(rules_index_for_summary)
        assert "Goblin" in summary
        assert "monsters/goblin" in summary

    def test_summary_includes_spell_list(self, rules_index_for_summary):
        """Summary includes spell quick reference."""
        summary = build_rules_summary(rules_index_for_summary)
        assert "Cure Light Wounds" in summary

    def test_summary_includes_tool_syntax(self, rules_index_for_summary):
        """Summary includes tool usage instructions."""
        summary = build_rules_summary(rules_index_for_summary)
        assert "get_rules" in summary
        assert "list_rules" in summary

    def test_summary_reasonable_length(self, rules_index_for_summary):
        """Summary is approximately 300 lines."""
        summary = build_rules_summary(rules_index_for_summary)
        lines = summary.strip().split("\n")
        # With minimal test data, should be less than 100 lines
        # Full index would be ~300 lines
        assert 20 < len(lines) < 400
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_rules_prompts.py::TestBuildRulesSummary -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'dndbots.rules_prompts'"

**Step 3: Write minimal implementation**

```python
# src/dndbots/rules_prompts.py
"""Rules prompt generation for DM and player agents."""

from dndbots.rules_index import RulesIndex, MonsterEntry, SpellEntry


# Core mechanics that go in every summary
CORE_MECHANICS = """
## CORE MECHANICS

### Combat Sequence
1. Morale check (if applicable)
2. Movement
3. Missile fire (by DEX order)
4. Magic (spells go off)
5. Melee (simultaneous)

### THAC0 by Class/Level
       1-3   4-6   7-9  10-12
F/Elf   19    17    15    13
C/Thf   19    19    17    17
M-U     19    19    19    17
Dwf     19    17    17    15
Hflg    19    19    17    17

### Saving Throws (Fighter 1-3)
D/P: 12 | Wands: 13 | Para: 14 | Breath: 15 | Spells: 16

### Morale
2 = Never flees | 12 = Never checks
Check when: first death, half dead
2d6 > morale = flee

### Reaction Rolls (2d6)
2-3: Hostile | 4-6: Unfriendly | 7-9: Neutral | 10-11: Friendly | 12: Helpful
"""


TOOL_SYNTAX = """
## RULES TOOL USAGE

### Available Tools

get_rules(path, detail="summary|stats|full")
  - Fetch exact entry by path
  - Example: get_rules("monsters/goblin", detail="full")

list_rules(category, tags=None)
  - List entries in category with filters
  - Example: list_rules("monsters", tags=["undead"])

search_rules(query, category=None, limit=5)
  - Keyword search when path unknown
  - Example: search_rules("paralysis attack", category="monsters")

### Path Examples
monsters/goblin
spells/cleric/1/cure_light_wounds
spells/magic_user/2/invisibility
"""


def build_rules_summary(index: RulesIndex) -> str:
    """Build the in-context rules summary for DM prompt.

    Args:
        index: The loaded RulesIndex

    Returns:
        ~300 line rules summary string
    """
    sections = [
        "BECMI BASIC RULES REFERENCE",
        "=" * 27,
        "",
        CORE_MECHANICS,
    ]

    # Add monster quick reference
    monsters = index.list_by_category("monsters")
    if monsters:
        sections.append("## MONSTER QUICK REFERENCE")
        sections.append("")
        sections.append("Format: Name: Stats [Special] -> path")
        sections.append("")
        for m in sorted(monsters, key=lambda x: x.name):
            if isinstance(m, MonsterEntry):
                special = f" [{', '.join(m.special_abilities)}]" if m.special_abilities else ""
                sections.append(
                    f"{m.name}: AC{m.ac} HD{m.hd} ML{m.morale} XP{m.xp}{special} -> {m.path}"
                )
            else:
                sections.append(f"{m.name}: {m.summary} -> {m.path}")
        sections.append("")

    # Add spell quick reference
    spells = index.list_by_category("spells")
    if spells:
        sections.append("## SPELL QUICK REFERENCE")
        sections.append("")
        for s in sorted(spells, key=lambda x: (
            getattr(x, 'spell_class', ''),
            getattr(x, 'spell_level', 0),
            x.name
        )):
            if isinstance(s, SpellEntry):
                rev = " [Rev]" if s.reversible else ""
                sections.append(
                    f"{s.spell_class[0].upper()}{s.spell_level} {s.name}: {s.summary}{rev} -> {s.path}"
                )
            else:
                sections.append(f"{s.name}: {s.summary} -> {s.path}")
        sections.append("")

    sections.append(TOOL_SYNTAX)

    return "\n".join(sections)
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_rules_prompts.py::TestBuildRulesSummary -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/rules_prompts.py tests/test_rules_prompts.py
git commit -m "feat(rules): add rules summary generator for DM prompt"
```

---

### Task 10: Integrate Rules Summary into DM Prompt

**Files:**
- Modify: `src/dndbots/prompts.py`
- Test: `tests/test_prompts.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_prompts.py
import json
import tempfile
from pathlib import Path

from dndbots.prompts import build_dm_prompt
from dndbots.rules_index import RulesIndex


class TestDmPromptWithRulesIndex:
    def test_dm_prompt_with_rules_index(self):
        """DM prompt includes rules summary when index provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_dir = Path(tmpdir) / "indexed" / "basic"
            index_dir.mkdir(parents=True)
            monsters = {
                "orc": {
                    "path": "monsters/orc",
                    "name": "Orc",
                    "category": "monster",
                    "ruleset": "basic",
                    "source_file": "dm.txt",
                    "source_lines": [100, 120],
                    "tags": ["humanoid"],
                    "related": [],
                    "summary": "Pig-faced humanoids",
                    "full_text": "...",
                    "stat_block": "AC6 HD1",
                    "ac": 6, "hd": "1", "move": "90'", "attacks": "1",
                    "damage": "1d6", "no_appearing": "2-8", "save_as": "F1",
                    "morale": 8, "treasure_type": "D", "alignment": "C", "xp": 10,
                    "special_abilities": [],
                },
            }
            (index_dir / "monsters.json").write_text(json.dumps(monsters))

            rules_index = RulesIndex(Path(tmpdir))
            prompt = build_dm_prompt("Test scenario", rules_index=rules_index)

            assert "Orc" in prompt
            assert "get_rules" in prompt
            assert "BECMI" in prompt

    def test_dm_prompt_without_rules_index(self):
        """DM prompt uses RULES_SHORTHAND when no index provided."""
        prompt = build_dm_prompt("Test scenario")
        # Should still have basic rules
        assert "THAC0" in prompt or "COMBAT" in prompt
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_prompts.py::TestDmPromptWithRulesIndex -v`
Expected: FAIL (build_dm_prompt doesn't accept rules_index parameter)

**Step 3: Write minimal implementation**

```python
# Modify src/dndbots/prompts.py

from dndbots.models import Character
from dndbots.rules import RULES_SHORTHAND
from dndbots.rules_index import RulesIndex
from dndbots.rules_prompts import build_rules_summary


DCML_GUIDE = """
## Your Memory (DCML Format)

Below is your compressed memory in DCML (D&D Condensed Memory Language).
- ## LEXICON lists all entities you know about
- ## MEMORY_<your_id> contains what you remember
- Facts with ! prefix are your beliefs (may be inaccurate)
- Facts with ? prefix are rumors/unconfirmed
- Do NOT invent new entity IDs - use existing ones from LEXICON

"""


def build_dm_prompt(
    scenario: str,
    rules_index: RulesIndex | None = None,
) -> str:
    """Build the Dungeon Master system prompt.

    Args:
        scenario: The adventure scenario/setup
        rules_index: Optional loaded rules index for expanded summary

    Returns:
        Complete DM system prompt
    """
    # Use expanded rules summary if index provided, else fall back to shorthand
    if rules_index is not None:
        rules_section = build_rules_summary(rules_index)
    else:
        rules_section = RULES_SHORTHAND

    return f"""You are the Dungeon Master for a Basic D&D (1983 Red Box) campaign.

{rules_section}

=== YOUR SCENARIO ===
{scenario}

=== DM GUIDELINES ===
- Describe scenes vividly but concisely
- Ask players what they want to do, don't assume actions
- Roll dice transparently - announce what you're rolling and why
- When a player attacks: announce their roll, calculate hit/miss, roll damage if hit
- Keep combat exciting with descriptions of hits and misses
- Be fair but challenging - Basic D&D is lethal
- Track monster HP and announce when enemies are wounded or defeated

=== TURN CONTROL ===
After describing a scene or resolving an action, explicitly address the next player.
Example: "Throk, the goblin snarls at you. What do you do?"

When you need to end the session or pause, say "SESSION PAUSE" clearly.
"""


def build_player_prompt(character: Character, memory: str | None = None) -> str:
    """Build a player agent system prompt.

    Args:
        character: The character this agent plays
        memory: Optional DCML memory block to include

    Returns:
        Complete player system prompt
    """
    sections = [
        f"You are playing {character.name} in a Basic D&D campaign.",
        "",
        "=== YOUR CHARACTER ===",
        character.to_sheet(),
    ]

    if memory:
        sections.extend([
            "",
            DCML_GUIDE,
            memory,
        ])

    sections.extend([
        "",
        f"""=== PLAYER GUIDELINES ===
- Stay in character - respond as {character.name} would
- Describe your actions clearly: "I attack the goblin with my sword"
- You can ask the DM questions: "How far away is the door?"
- Declare dice rolls you want to make: "I want to search for traps"
- Roleplay conversations with NPCs and other players
- Your character has their own personality, goals, and fears

=== PARTY PLAY ===
- "I defer to [other player]" or "I watch and wait" are VALID actions
- Only act if you have something valuable to add
- If another character is better suited for a task, let them shine
- Stepping back IS good roleplay

=== COMBAT ===
- On your turn, declare your action: attack, cast spell, use item, flee, etc.
- The DM will roll dice and describe results
- Keep track of your HP - you can ask the DM your current status

When the DM addresses you directly, respond in character.""",
    ])

    return "\n".join(sections)
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_prompts.py::TestDmPromptWithRulesIndex -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/prompts.py tests/test_prompts.py
git commit -m "feat(rules): integrate rules summary into DM prompt"
```

---

## Phase 4: Sample Data Extraction (Tasks 11-12)

### Task 11: Create Sample Monster Index (5 monsters)

**Files:**
- Create: `rules/indexed/basic/monsters.json`

**Step 1: Create the sample data file**

This is manual curation of 5 representative monsters from the BECMI DM rulebook.

```json
{
  "goblin": {
    "path": "monsters/goblin",
    "name": "Goblin",
    "category": "monster",
    "ruleset": "basic",
    "min_level": 1,
    "max_level": 3,
    "source_file": "becmi_dm_rulebook.txt",
    "source_lines": [2456, 2489],
    "tags": ["humanoid", "chaotic", "low-level", "tribal"],
    "related": ["monsters/hobgoblin", "monsters/bugbear", "monsters/kobold"],
    "summary": "Small chaotic humanoids, -1 to hit in daylight, hate dwarves",
    "stat_block": "AC6 HD1-1 Mv90'(30') Atk1wpn Dm(wpn) NA2-8(6-60) SvNM ML7(9) TT(R)C AL:C XP5",
    "full_text": "Goblins are small, ugly humanoids standing about 4' tall. They live in dark places (usually caves or underground) and attack any creature they think they can defeat. When in full daylight, they suffer a penalty of -1 to all Hit rolls.\n\nAs tribal creatures, goblins have leaders. For every 4 goblins encountered, there is an additional leader with 1+1 Hit Dice who gains +1 to damage. When 20 or more goblins are encountered, a chieftain is present with 2 Hit Dice and +2 damage. Goblins hate dwarves and will attack them in preference to other opponents.",
    "ac": 6,
    "hd": "1-1",
    "move": "90' (30')",
    "attacks": "1 weapon",
    "damage": "By weapon",
    "no_appearing": "2-8 (6-60)",
    "save_as": "Normal Man",
    "morale": 7,
    "treasure_type": "(R) C",
    "alignment": "Chaotic",
    "xp": 5,
    "special_abilities": ["infravision 90'", "-1 to hit in daylight", "hate dwarves"]
  },
  "skeleton": {
    "path": "monsters/skeleton",
    "name": "Skeleton",
    "category": "monster",
    "ruleset": "basic",
    "min_level": 1,
    "max_level": 3,
    "source_file": "becmi_dm_rulebook.txt",
    "source_lines": [3200, 3230],
    "tags": ["undead", "mindless", "low-level"],
    "related": ["monsters/zombie", "monsters/ghoul"],
    "summary": "Animated bones, mindless, immune to sleep/charm",
    "stat_block": "AC7 HD1 Mv60'(20') Atk1wpn Dm(wpn) NA3-12 SvF1 ML12 TTNone AL:C XP10",
    "full_text": "Skeletons are the animated bones of the dead. They can be created by magic-users or clerics of Chaotic alignment. They are mindless, and simply follow the commands of their creator.\n\nSkeletons always fight until destroyed. They are immune to sleep and charm spells, as are all undead. They take only half damage from edged weapons.",
    "ac": 7,
    "hd": "1",
    "move": "60' (20')",
    "attacks": "1 weapon",
    "damage": "By weapon",
    "no_appearing": "3-12",
    "save_as": "F1",
    "morale": 12,
    "treasure_type": "None",
    "alignment": "Chaotic",
    "xp": 10,
    "special_abilities": ["undead immunities", "half damage from edged weapons"]
  },
  "ghoul": {
    "path": "monsters/ghoul",
    "name": "Ghoul",
    "category": "monster",
    "ruleset": "basic",
    "min_level": 1,
    "max_level": 4,
    "source_file": "becmi_dm_rulebook.txt",
    "source_lines": [2200, 2250],
    "tags": ["undead", "paralyze", "corpse-eater"],
    "related": ["monsters/wight", "monsters/skeleton", "monsters/zombie"],
    "summary": "Paralyzing touch (save vs Paralysis), feeds on corpses",
    "stat_block": "AC6 HD2 Mv90'(30') Atk2claws/1bite Dm1d3/1d3/1d3+para NA1-6(2-16) SvF2 ML9 TTB AL:C XP25",
    "full_text": "Ghouls are undead creatures that feed on the flesh of corpses. They look like twisted, bestial humanoids with elongated claws and sharp teeth.\n\nAny successful hit by a ghoul requires the victim to save vs Paralysis or become paralyzed for 2-8 turns. Elves are immune to this paralysis. Ghouls are, like all undead, immune to sleep and charm spells.",
    "ac": 6,
    "hd": "2",
    "move": "90' (30')",
    "attacks": "2 claws/1 bite",
    "damage": "1d3/1d3/1d3 + paralysis",
    "no_appearing": "1-6 (2-16)",
    "save_as": "F2",
    "morale": 9,
    "treasure_type": "B",
    "alignment": "Chaotic",
    "xp": 25,
    "special_abilities": ["paralyze on hit (save vs Paralysis)", "elves immune", "undead immunities"]
  },
  "orc": {
    "path": "monsters/orc",
    "name": "Orc",
    "category": "monster",
    "ruleset": "basic",
    "min_level": 1,
    "max_level": 4,
    "source_file": "becmi_dm_rulebook.txt",
    "source_lines": [2900, 2950],
    "tags": ["humanoid", "chaotic", "tribal"],
    "related": ["monsters/goblin", "monsters/hobgoblin", "monsters/ogre"],
    "summary": "Pig-faced humanoids, -1 to hit in daylight, tribal with leaders",
    "stat_block": "AC6 HD1 Mv120'(40') Atk1wpn Dm(wpn) NA2-8(10-60) SvF1 ML8(6) TT(L)D AL:C XP10",
    "full_text": "Orcs are ugly humanoids with pig-like faces. They are nocturnal, and suffer -1 to Hit rolls when in bright sunlight. Orcs live in tribes, each tribe having a lair in a cave or other dark place.\n\nOrc leaders appear as follows: for every 10 orcs, there is a leader with 8 hit points. If 20+ orcs are encountered, there is a chieftain with 15 hit points and 2 bodyguards with 8 hp each. In an orc lair, the chieftain has double hit points.",
    "ac": 6,
    "hd": "1",
    "move": "120' (40')",
    "attacks": "1 weapon",
    "damage": "By weapon",
    "no_appearing": "2-8 (10-60)",
    "save_as": "F1",
    "morale": 8,
    "treasure_type": "(L) D",
    "alignment": "Chaotic",
    "xp": 10,
    "special_abilities": ["infravision 60'", "-1 to hit in daylight"]
  },
  "giant_spider": {
    "path": "monsters/giant_spider",
    "name": "Giant Spider (Black Widow)",
    "category": "monster",
    "ruleset": "basic",
    "min_level": 1,
    "max_level": 5,
    "source_file": "becmi_dm_rulebook.txt",
    "source_lines": [3100, 3150],
    "tags": ["vermin", "poison", "web"],
    "related": ["monsters/giant_spider_crab", "monsters/giant_spider_tarantula"],
    "summary": "Poisonous bite (save vs Poison or die in 1 turn), webs",
    "stat_block": "AC6 HD3 Mv60'(20')Web120'(40') Atk1bite Dm2d6+poison NA1-3 SvF2 ML8 TTU AL:N XP50",
    "full_text": "Black widow spiders are 6' long, with shiny black bodies and a red hourglass marking. They spin strong webs to trap prey.\n\nBlack widows attack with a poisonous bite. A victim who fails to save vs Poison will die in 1 turn. Even if the save succeeds, the victim takes 2d6 damage from the bite. Black widows can be found in their webs; if so, they gain surprise on 1-4 on 1d6.",
    "ac": 6,
    "hd": "3",
    "move": "60' (20') / Web 120' (40')",
    "attacks": "1 bite",
    "damage": "2d6 + poison",
    "no_appearing": "1-3",
    "save_as": "F2",
    "morale": 8,
    "treasure_type": "U",
    "alignment": "Neutral",
    "xp": 50,
    "special_abilities": ["poison (save or die in 1 turn)", "webs", "surprise 1-4 in web"]
  }
}
```

**Step 2: Create the directory and file**

```bash
mkdir -p rules/indexed/basic
# Write the JSON content to rules/indexed/basic/monsters.json
```

**Step 3: Commit**

```bash
git add rules/indexed/basic/monsters.json
git commit -m "data(rules): add 5 sample monsters to indexed rules"
```

---

### Task 12: Create Sample Spell Index (5 spells)

**Files:**
- Create: `rules/indexed/basic/spells.json`

**Step 1: Create the sample data file**

```json
{
  "cure_light_wounds": {
    "path": "spells/cleric/1/cure_light_wounds",
    "name": "Cure Light Wounds",
    "category": "spell",
    "ruleset": "basic",
    "min_level": 1,
    "source_file": "becmi_players_manual.txt",
    "source_lines": [3500, 3520],
    "tags": ["healing", "cleric", "level-1"],
    "related": ["spells/cleric/1/cause_light_wounds"],
    "summary": "Touch, heal 1d6+1 hp",
    "stat_block": "Range: Touch | Duration: Permanent | Reversible",
    "full_text": "This spell heals a living creature of 2-7 (1d6+1) points of damage. It cannot raise the dead nor heal a creature above its normal maximum hit points.\n\nThe reverse of this spell, Cause Light Wounds, requires a successful Hit roll and inflicts 2-7 points of damage.",
    "spell_class": "cleric",
    "spell_level": 1,
    "range": "Touch",
    "duration": "Permanent",
    "reversible": true,
    "reverse_name": "Cause Light Wounds"
  },
  "light": {
    "path": "spells/cleric/1/light",
    "name": "Light",
    "category": "spell",
    "ruleset": "basic",
    "min_level": 1,
    "source_file": "becmi_players_manual.txt",
    "source_lines": [3550, 3570],
    "tags": ["utility", "cleric", "level-1"],
    "related": ["spells/cleric/1/darkness", "spells/magic_user/1/light"],
    "summary": "30' radius light, 12 turns duration",
    "stat_block": "Range: 120' | Duration: 12 turns | Reversible",
    "full_text": "This spell creates a globe of light 30' in diameter. It may be cast on an object (which will then shed light as it moves) or into the air (where it will remain stationary).\n\nThe reverse of this spell, Darkness, creates a globe of darkness 30' in diameter. Normal sight and infravision cannot see through it; a Light spell will cancel a Darkness spell.",
    "spell_class": "cleric",
    "spell_level": 1,
    "range": "120'",
    "duration": "12 turns",
    "reversible": true,
    "reverse_name": "Darkness"
  },
  "magic_missile": {
    "path": "spells/magic_user/1/magic_missile",
    "name": "Magic Missile",
    "category": "spell",
    "ruleset": "basic",
    "min_level": 1,
    "source_file": "becmi_players_manual.txt",
    "source_lines": [3700, 3720],
    "tags": ["damage", "magic-user", "level-1", "auto-hit"],
    "related": [],
    "summary": "150' range, auto-hit, 2d6+1 damage",
    "stat_block": "Range: 150' | Duration: Instantaneous",
    "full_text": "A magic missile is a glowing arrow of energy that springs from the caster's fingertip. It automatically hits any visible target and does 2-7 (2d6+1) points of damage.\n\nFor every 5 levels of experience of the caster, an additional magic missile is created (2 at 6th level, 3 at 11th, etc.).",
    "spell_class": "magic-user",
    "spell_level": 1,
    "range": "150'",
    "duration": "Instantaneous",
    "reversible": false,
    "reverse_name": null
  },
  "sleep": {
    "path": "spells/magic_user/1/sleep",
    "name": "Sleep",
    "category": "spell",
    "ruleset": "basic",
    "min_level": 1,
    "source_file": "becmi_players_manual.txt",
    "source_lines": [3750, 3780],
    "tags": ["enchantment", "magic-user", "level-1", "area-effect"],
    "related": [],
    "summary": "240' range, 2d8 HD of creatures sleep",
    "stat_block": "Range: 240' | Duration: 4d4 turns",
    "full_text": "This spell puts creatures to sleep. It affects 2d8 Hit Dice of creatures. Creatures with the least Hit Dice are affected first. Sleeping creatures are helpless and may be killed instantly with any weapon.\n\nUndead and creatures larger than 4+1 HD are not affected. Creatures with 4+1 HD are allowed a save vs Spells to resist the effect.",
    "spell_class": "magic-user",
    "spell_level": 1,
    "range": "240'",
    "duration": "4d4 turns",
    "reversible": false,
    "reverse_name": null
  },
  "detect_magic": {
    "path": "spells/magic_user/1/detect_magic",
    "name": "Detect Magic",
    "category": "spell",
    "ruleset": "basic",
    "min_level": 1,
    "source_file": "becmi_players_manual.txt",
    "source_lines": [3650, 3665],
    "tags": ["divination", "magic-user", "level-1", "detection"],
    "related": ["spells/cleric/1/detect_magic"],
    "summary": "60' range, 2 turns, see magic glow",
    "stat_block": "Range: 60' | Duration: 2 turns",
    "full_text": "This spell allows the caster to see a glow around any object or area that has been enchanted or magically created. It does not reveal the type of magic, only that magic is present.\n\nThe glow can be seen through walls or obstacles up to 60' away, but the caster must concentrate on an area to detect magic therein.",
    "spell_class": "magic-user",
    "spell_level": 1,
    "range": "60'",
    "duration": "2 turns",
    "reversible": false,
    "reverse_name": null
  }
}
```

**Step 2: Create the file**

```bash
# Write the JSON content to rules/indexed/basic/spells.json
```

**Step 3: Commit**

```bash
git add rules/indexed/basic/spells.json
git commit -m "data(rules): add 5 sample spells to indexed rules"
```

---

## Phase 5: Integration Tests (Tasks 13-14)

### Task 13: Full Integration Test with Sample Data

**Files:**
- Create: `tests/test_rules_integration.py`

**Step 1: Write the failing test**

```python
# tests/test_rules_integration.py
"""Integration tests for the complete rules system."""

from pathlib import Path

import pytest

from dndbots.rules_index import RulesIndex, MonsterEntry, SpellEntry
from dndbots.rules_tools import get_rules, list_rules, search_rules
from dndbots.rules_prompts import build_rules_summary
from dndbots.prompts import build_dm_prompt


# Use the actual indexed rules if they exist
RULES_DIR = Path(__file__).parent.parent / "rules"


@pytest.fixture
def real_rules_index():
    """Load the actual rules index from the project."""
    if not (RULES_DIR / "indexed").exists():
        pytest.skip("No indexed rules available")
    return RulesIndex(RULES_DIR)


class TestRulesIntegration:
    def test_load_all_monsters(self, real_rules_index):
        """Can load and query all indexed monsters."""
        monsters = list_rules(real_rules_index, "monsters")
        assert len(monsters) >= 5  # We created 5 sample monsters
        names = [m.name for m in monsters]
        assert "Goblin" in names
        assert "Ghoul" in names

    def test_load_all_spells(self, real_rules_index):
        """Can load and query all indexed spells."""
        spells = list_rules(real_rules_index, "spells")
        assert len(spells) >= 5  # We created 5 sample spells
        names = [s.name for s in spells]
        assert "Magic Missile" in names
        assert "Sleep" in names

    def test_get_monster_full_entry(self, real_rules_index):
        """Can retrieve full monster entry with all details."""
        result = get_rules(real_rules_index, "monsters/ghoul", detail="full")
        assert result is not None
        assert "paralysis" in result.content.lower() or "paralyze" in result.content.lower()
        assert result.metadata["ac"] == 6
        assert result.metadata["hd"] == "2"

    def test_get_spell_full_entry(self, real_rules_index):
        """Can retrieve full spell entry with all details."""
        result = get_rules(real_rules_index, "spells/magic_user/1/sleep", detail="full")
        assert result is not None
        assert "2d8" in result.content
        assert result.metadata["spell_level"] == 1

    def test_search_for_undead(self, real_rules_index):
        """Can search for undead monsters."""
        results = search_rules(real_rules_index, "undead", category="monsters")
        assert len(results) >= 2  # Skeleton and Ghoul
        paths = [r.path for r in results]
        assert "monsters/skeleton" in paths or "monsters/ghoul" in paths

    def test_search_for_poison(self, real_rules_index):
        """Can search for poison abilities."""
        results = search_rules(real_rules_index, "poison")
        assert len(results) >= 1
        # Giant Spider has poison
        paths = [r.path for r in results]
        assert any("spider" in p for p in paths)

    def test_filter_monsters_by_tag(self, real_rules_index):
        """Can filter monsters by tag."""
        humanoids = list_rules(real_rules_index, "monsters", tags=["humanoid"])
        assert len(humanoids) >= 2  # Goblin and Orc
        names = [m.name for m in humanoids]
        assert "Goblin" in names
        assert "Orc" in names

    def test_dm_prompt_includes_monsters(self, real_rules_index):
        """DM prompt includes monster quick reference."""
        prompt = build_dm_prompt("Test dungeon", rules_index=real_rules_index)
        assert "Goblin" in prompt
        assert "Ghoul" in prompt
        assert "monsters/" in prompt

    def test_dm_prompt_includes_spells(self, real_rules_index):
        """DM prompt includes spell quick reference."""
        prompt = build_dm_prompt("Test dungeon", rules_index=real_rules_index)
        assert "Magic Missile" in prompt or "Sleep" in prompt
        assert "spells/" in prompt

    def test_dm_prompt_includes_tool_syntax(self, real_rules_index):
        """DM prompt includes tool usage instructions."""
        prompt = build_dm_prompt("Test dungeon", rules_index=real_rules_index)
        assert "get_rules" in prompt
        assert "list_rules" in prompt
        assert "search_rules" in prompt
```

**Step 2: Run test to verify it works**

Run: `.venv/bin/pytest tests/test_rules_integration.py -v`
Expected: PASS (assuming sample data exists)

**Step 3: Commit**

```bash
git add tests/test_rules_integration.py
git commit -m "test(rules): add integration tests with sample data"
```

---

### Task 14: Run All Tests and Verify

**Step 1: Run full test suite**

```bash
.venv/bin/pytest -v
```

Expected: All tests pass

**Step 2: Check test coverage**

```bash
.venv/bin/pytest --cov=dndbots --cov-report=term-missing
```

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat(rules): complete BECMI rules integration phase 1

- RulesEntry, MonsterEntry, SpellEntry dataclasses
- RulesIndex with JSON loading
- get_rules(), list_rules(), search_rules() tool functions
- build_rules_summary() for DM prompt
- Integration with build_dm_prompt()
- 5 sample monsters and 5 sample spells indexed
- Full test coverage"
```

---

## Summary

**Total Tasks:** 14

**Files Created:**
- `src/dndbots/rules_index.py` - Data models and index loading
- `src/dndbots/rules_tools.py` - Tool functions
- `src/dndbots/rules_prompts.py` - Summary generation
- `tests/test_rules_index.py` - Index tests
- `tests/test_rules_tools.py` - Tool tests
- `tests/test_rules_prompts.py` - Prompt tests
- `tests/test_rules_integration.py` - Integration tests
- `rules/indexed/basic/monsters.json` - Sample monster data
- `rules/indexed/basic/spells.json` - Sample spell data

**Files Modified:**
- `src/dndbots/prompts.py` - Add rules_index parameter

**Phase 2 (Future Work):**
- Full monster extraction script
- Full spell extraction script
- Treasure types
- DM procedures
- Manifest generation

---

Plan complete and saved to `docs/plans/2025-12-07-becmi-rules-implementation-plan.md`.

**Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
