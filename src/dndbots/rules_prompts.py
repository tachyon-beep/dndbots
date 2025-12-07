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
