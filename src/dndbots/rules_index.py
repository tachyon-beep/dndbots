"""Rules index for BECMI D&D content."""

import json
from dataclasses import dataclass, field
from pathlib import Path


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


@dataclass
class SpellEntry(RulesEntry):
    """Extended metadata for spell entries."""

    spell_class: str = "magic-user"  # "cleric", "magic-user", "elf"
    spell_level: int = 1  # 1-5 for Basic
    range: str = "0"  # "Touch", "120'", "0 (caster only)"
    duration: str = "Instantaneous"  # "Permanent", "2 turns", "1 round/level"
    reversible: bool = False  # Can be reversed
    reverse_name: str | None = None  # "Cause Light Wounds"


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
