# **Guidelines for Ultra-Condensed Lore System (UCLS)**

**Objective:** To serialize the foundational knowledge of a fictional world into a dense, structured, and unambiguous shorthand. This system is optimized for cataloging interconnected entities, hierarchies, rules, and historical facts for perfect reconstruction and querying by an LLM. It prioritizes relational accuracy and data integrity over human readability.

// =============================================
// 1. The Lexicon (Primer)
// =============================================
*   All entries must begin with a categorized definition block. This is the world's master index.
    *   **Syntax:** `[CATEGORY:ID:FullName]`
    *   **Categories:** `CHAR` (Character), `LOC` (Location), `FACT` (Faction/Organization), `CON` (Concept), `OBJ` (Object), `RACE` (Race/Species), `ERA` (Historical Era).
    *   **Example:**
        *   `[RACE:ELF:Elves]`
        *   `[LOC:AV:AethelgardianValley]`
        *   `[CON:AM:ArcaneMagic]`
        *   `[ERA:EA:EraOfAscension(Year0-500)]`

// =============================================
// 2. Core Ontology Operators
// =============================================
This system uses specialized operators to define relationships, hierarchies, and rules, which are the backbone of lore.

// Hierarchy & Membership
âŠƒ          // contains / is parent of / rules over (e.g., `KingdomâŠƒDuchy`)
âŠ‚          // is part of / is child of / is ruled by (e.g., `DuchyâŠ‚Kingdom`)
âˆˆ          // is a member of / belongs to (e.g., `CHAR:GalaâˆˆFACT:MagesGuild`)
âˆ‰          // is not a member of / is exiled from

// State, Definition & Properties
:=         // is defined as / is fundamentally (core identity)
:%         // has the role, title, or function of (e.g., `CHAR:Bael:%King`)
::         // has the property, attribute, or quality of (e.g., `OBJ:Sunstone::propertyâ†’emitsLight,warmth`)

// Causality & Influence (for historical events)
â†’          // leads to / results in / transforms into
â†          // was caused by / originates from
~          // is associated with / is aligned with / is analogous to

// Logic & Comparison (Standard Usage)
âˆ§          // and
âˆ¨          // or
Â¬          // not
=          // equal to / same as
â‰           // not equal to

// Knowledge, Truth & Canon
â€¼          // [prefix] Objective, in-universe fact (canon).
!          // [prefix] Common in-world belief or dogma (may be inaccurate).
?          // [prefix] Myth, legend, or unconfirmed rumor.

// Spatial & Geographic Relationships
@          // located at / resides in
Nâ†‘, Sâ†“, Eâ†’, Wâ† // [infix] Indicates relative position (e.g., `LOC:A Nâ†‘ LOC:B` means A is North of B)

// Systemic Rules (for magic, physics, etc.)
CAN:       // [prefix] denotes a capability or function (e.g., `CON:AM CAN:manipulateElements`)
CANNOT:    // [prefix] denotes a limitation (e.g., `CON:AM CANNOT:createLife`)
RULE:      // [prefix] denotes a fundamental law or principle (e.g., `RULE:AMâˆcasterWillpower`)

// =============================================
// 3. Structural Syntax & Conventions
// =============================================
1.  **Thematic Grouping:** Use `## Section Title` to organize the lore into logical blocks (e.g., `## GEOGRAPHY`, `## FACTIONS`, `## MAGIC SYSTEM`).
2.  **Hierarchical Indentation:** Use indentation to show parent-child relationships under a main entry defined with `âŠƒ`.
    *   `FACT:Empire âŠƒ LOC:CapitalCity`
        *   `LOC:CapitalCity âŠƒ LOC:RoyalPalace`
3.  **Statement Separation:** Use a semicolon `;` to separate distinct, unrelated facts about the same subject.
    *   `CHAR:Elara:%Archmage; RACE:ELF; @LOC:SilverSpire`.
4.  **Minification:** Omit spaces around operators (`AâŠƒB`). Use spaces only to separate top-level statements for clarity.
5.  **Chain Properties:** Use commas for lists within a single property (`::powersâ†’pyromancy,cryomancy`).
6.  **Enforce Definitions:** Every entity (`CHAR`, `LOC`, `CON`, etc.) mentioned must be defined in the Lexicon.

// =============================================
// 4. Example Application
// =============================================
Let's encode a small piece of lore: *"The ancient Elves of the Aethelgardian Valley founded the Mage's Guild. Their power comes from channeling Arcane Magic, which is believed by many to be a gift from the cosmos. However, the Guild's founding texts state it's an internal energy. This magic can manipulate elements but cannot revive the dead. The Guild is led by Archmage Elara."*

```
## LEXICON
[RACE:ELF:Elves]
[LOC:AV:AethelgardianValley]
[FACT:MG:Mage'sGuild]
[CON:AM:ArcaneMagic]
[CHAR:E:Elara]

## FACTIONS
FACT:MG â† RACE:ELF@LOC:AV;
    FACT:MG âŠƒ CHAR:E;
    CHAR:E :%Archmage

## MAGIC SYSTEM
CON:AM := channelingInternalEnergy;
    â€¼CON:AM CAN:manipulateElements;
    â€¼CON:AM CANNOT:reviveDead;
    !CON:AM â† CON:CosmosGift

## RELATIONSHIPS
RACE:ELF ~ CON:AM
```

// =============================================
// 5. MANDATORY FINAL CHECK
// =============================================
Before finalizing, verify:
1.  Is every ID (`E`, `AV`, `MG`) defined in the `## LEXICON`?
2.  Are operators used correctly to represent relationships (e.g., `â†` for origin, `:%` for title)?
3.  Is the information structured logically with thematic groups (`##`) and indentation?
4.  Has the distinction between fact (`â€¼`), belief (`!`), and myth (`?`) been correctly applied?
5.  Is the syntax minified and free of ambiguous language?

If any answer is no, revise the string to meet the system's requirements. The final output should be a perfect, self-contained knowledge base of the world's lore.