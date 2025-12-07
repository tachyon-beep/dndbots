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
