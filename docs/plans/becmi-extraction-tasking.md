# BECMI Extraction Tasking Statement

## For Extraction Agents

You are extracting BECMI Basic D&D (1983 Red Box) rules from OCR'd text into structured JSON.

### Your Task

1. Read the assigned line range from the source file
2. Extract all entries of the specified category
3. Fix OCR and layout issues as you go
4. Output valid JSON matching the schema

### Source Files

- **DM Rulebook**: `/home/john/dndbots/rules/becmi_dm_rulebook.txt`
- **Players Manual**: `/home/john/dndbots/rules/becmi_players_manual.txt`

### Common OCR Fixes

| OCR Error | Correct |
|-----------|---------|
| `I` in numbers | `1` |
| `O` in numbers | `0` |
| `l` in numbers | `1` |
| `Id6`, `Id8` | `1d6`, `1d8` |
| `'/2` or `1/2` | `1/2` |
| Broken lines mid-word | Join them |
| `John Morrissey (Order #50311027)` | Delete (watermark) |
| Random spacing in stat values | Normalize |

### Layout Issues

The OCR source has multi-column layout. Watch for:
- Stat blocks from different monsters interleaved
- Description text broken across columns
- Headers appearing mid-paragraph

### Output Location

Write JSON to: `/home/john/dndbots/rules/indexed/basic/temp/`

Use the filename specified in your assignment (e.g., `monsters_01.json`).

---

## Monster Schema

```json
{
  "monster_key": {
    "path": "monsters/monster-key",
    "name": "Monster Name",
    "category": "monster",
    "ruleset": "basic",
    "min_level": 1,
    "max_level": 3,
    "source_file": "becmi_dm_rulebook.txt",
    "source_lines": [START, END],
    "tags": ["tag1", "tag2"],
    "related": ["monsters/other-monster"],
    "summary": "One sentence summary from description",
    "stat_block": "AC# HD# Mv#'(#') Atk# Dm# NA#(#) Sv## ML# TT# AL:X XP#",
    "full_text": "Full description paragraph(s)",
    "ac": 6,
    "hd": "1",
    "move": "120' (40')",
    "attacks": "1 weapon",
    "damage": "By weapon",
    "no_appearing": "2-8 (6-60)",
    "save_as": "F1",
    "morale": 8,
    "treasure_type": "C",
    "alignment": "Chaotic",
    "xp": 10,
    "special_abilities": ["ability1", "ability2"]
  }
}
```

**Key formatting rules:**
- `monster_key`: lowercase, hyphens for spaces (e.g., `giant-ant`, `bear-black`)
- `path`: always `monsters/{monster_key}`
- `stat_block`: Compressed one-liner for quick reference
- `tags`: Include creature type (humanoid, undead, beast, etc.), alignment, size, special traits
- `related`: Other monsters mentioned in description or thematically linked
- `special_abilities`: List any non-standard abilities (paralysis, energy drain, etc.)

**For monsters with variants** (e.g., Bear has Black/Grizzly/Polar/Cave):
- Create separate entries for each variant
- Use keys like `bear-black`, `bear-grizzly`, etc.
- Cross-reference each other in `related`

---

## Spell Schema

```json
{
  "spell_key": {
    "path": "spells/spell-key",
    "name": "Spell Name",
    "category": "spell",
    "ruleset": "basic",
    "source_file": "becmi_players_manual.txt",
    "source_lines": [START, END],
    "tags": ["level-1", "magic-user", "offensive"],
    "related": ["spells/similar-spell"],
    "summary": "One sentence effect summary",
    "full_text": "Full spell description",
    "spell_class": "magic-user",
    "spell_level": 1,
    "range": "120'",
    "duration": "6 turns",
    "effect": "One target",
    "reversible": false,
    "reverse_name": null
  }
}
```

**Key formatting rules:**
- `spell_key`: lowercase, hyphens (e.g., `magic-missile`, `cure-light-wounds`)
- `spell_class`: `"cleric"` or `"magic-user"`
- `reversible`: true if spell has a reverse form
- `reverse_name`: Name of reversed spell (e.g., "Cause Light Wounds")
- `tags`: Include level, class, and effect type (offensive, defensive, utility, healing)

---

## Magic Item Schema

```json
{
  "item_key": {
    "path": "items/item-key",
    "name": "Item Name",
    "category": "item",
    "subcategory": "sword|weapon|armor|potion|scroll|ring|wand|misc",
    "ruleset": "basic",
    "source_file": "becmi_dm_rulebook.txt",
    "source_lines": [START, END],
    "tags": ["magic", "weapon", "cursed"],
    "related": ["items/similar-item"],
    "summary": "One sentence effect",
    "full_text": "Full item description",
    "bonus": "+1",
    "charges": null,
    "cursed": false,
    "special_ability": "Description of special power if any"
  }
}
```

---

## Procedure Schema

```json
{
  "procedure_key": {
    "path": "procedures/procedure-key",
    "name": "Procedure Name",
    "category": "procedure",
    "ruleset": "basic",
    "source_file": "becmi_dm_rulebook.txt",
    "source_lines": [START, END],
    "tags": ["combat", "exploration", "social"],
    "related": ["procedures/related-procedure"],
    "summary": "When and how to use this procedure",
    "full_text": "Complete procedure text",
    "tables": []
  }
}
```

---

## Class Schema

```json
{
  "class_key": {
    "path": "classes/class-key",
    "name": "Class Name",
    "category": "class",
    "ruleset": "basic",
    "source_file": "becmi_players_manual.txt",
    "source_lines": [START, END],
    "tags": ["human", "spellcaster"],
    "related": ["classes/similar-class"],
    "summary": "One sentence class description",
    "full_text": "Complete class description",
    "prime_requisite": "Strength",
    "hit_die": "d8",
    "max_level": 14,
    "armor_allowed": "Any",
    "weapons_allowed": "Any",
    "special_abilities": ["ability1"],
    "xp_table": {"1": 0, "2": 2000, "3": 4000}
  }
}
```

---

## For Verification Agents

You are reviewing extracted BECMI rules for accuracy and completeness.

### Your Task

1. Read the extracted JSON file(s)
2. Spot-check entries against the source text
3. Verify all required fields are present
4. Check for OCR errors that were missed
5. Validate JSON is well-formed
6. Report issues found (don't fix them directly)

### Verification Checklist

- [ ] JSON parses without errors
- [ ] All entries have required fields
- [ ] `source_lines` match actual content location
- [ ] Stat values match source (AC, HD, XP, etc.)
- [ ] No obvious OCR errors remain in text
- [ ] `summary` accurately reflects the entry
- [ ] `related` entries reference valid paths
- [ ] No duplicate entries
- [ ] Variant creatures have separate entries

### Output Format

Report issues as:
```
FILE: monsters_01.json
ISSUES:
- giant-ant: XP should be 125, not 12S
- bat-normal: missing special_abilities field
- bandit: source_lines [1998, 2020] should be [2000, 2020]
OK: ape-white, baboon-rock
```

If no issues: `FILE: monsters_01.json - ALL OK`
