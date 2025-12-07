"""Tool functions for BECMI rules access."""

from pathlib import Path
from typing import Callable, Literal

from dndbots.rules_index import (
    RulesIndex,
    RulesEntry,
    RulesResult,
    RulesIndexEntry,
    RulesMatch,
    MonsterEntry,
    SpellEntry,
)


# Default rules directory (can be overridden)
# Path: rules_tools.py -> dndbots/ -> src/ -> dndbots/ -> rules/
DEFAULT_RULES_DIR = Path(__file__).parent.parent.parent / "rules"


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


def create_rules_tools(
    rules_dir: Path | None = None,
) -> tuple[Callable, Callable, Callable]:
    """Create tool functions bound to a rules index.

    Returns tools suitable for AutoGen AssistantAgent(tools=[...]).

    Args:
        rules_dir: Path to rules directory. Defaults to project rules/

    Returns:
        Tuple of (lookup_rules, list_rules_tool, search_rules_tool) functions

    Example:
        lookup, list_rules, search = create_rules_tools()
        agent = AssistantAgent(name="dm", tools=[lookup, list_rules, search])
    """
    if rules_dir is None:
        rules_dir = DEFAULT_RULES_DIR

    index = RulesIndex(rules_dir)

    def lookup_rules(
        path: str,
        detail: Literal["summary", "stats", "full"] = "summary",
    ) -> str:
        """Look up D&D rules by exact path.

        Use this to get details about specific monsters, spells, items, or procedures.

        Args:
            path: Hierarchical path like "monsters/goblin", "spells/magic-user/1/sleep"
            detail: Level of detail - "summary" (quick), "stats" (combat), "full" (everything)

        Returns:
            Rules content as formatted text, or "Not found" message
        """
        result = get_rules(index, path, detail)
        if result is None:
            return f"No rules entry found for path: {path}"

        # Format output as readable text
        lines = [f"# {result.name}", f"Category: {result.category}", ""]
        lines.append(result.content)

        if detail != "summary" and result.related:
            lines.extend(["", "Related:", *[f"  - {r}" for r in result.related[:3]]])

        return "\n".join(lines)

    def list_rules_tool(
        category: str,
        tags: str | None = None,
    ) -> str:
        """List available rules entries in a category.

        Use this to discover what monsters, spells, or items are available.

        Args:
            category: Category path like "monsters", "spells/cleric/1", "items"
            tags: Comma-separated tags to filter by (e.g., "undead,dangerous")

        Returns:
            List of available entries with brief summaries
        """
        tag_list = [t.strip() for t in tags.split(",")] if tags else None
        entries = list_rules(index, category, tags=tag_list)

        if not entries:
            return f"No entries found in category: {category}"

        lines = [f"# {category.title()} ({len(entries)} entries)", ""]
        for e in entries[:20]:  # Limit output
            preview = f" [{e.stat_preview}]" if e.stat_preview else ""
            lines.append(f"- **{e.path}**: {e.name}{preview}")
            lines.append(f"  {e.summary[:100]}...")

        if len(entries) > 20:
            lines.append(f"\n... and {len(entries) - 20} more")

        return "\n".join(lines)

    def search_rules_tool(
        query: str,
        category: str | None = None,
    ) -> str:
        """Search rules by keyword.

        Use this when you don't know the exact path but need to find something.

        Args:
            query: Search term like "poison", "fire", "undead"
            category: Optional category filter like "monsters" or "spells"

        Returns:
            List of matching entries with relevance scores
        """
        matches = search_rules(index, query, category=category, limit=8)

        if not matches:
            return f"No matches found for: {query}"

        lines = [f"# Search results for '{query}'", ""]
        for m in matches:
            lines.append(f"- **{m.path}** ({m.name}) - {m.relevance:.0%} match")
            lines.append(f"  {m.snippet[:80]}...")

        return "\n".join(lines)

    return lookup_rules, list_rules_tool, search_rules_tool
