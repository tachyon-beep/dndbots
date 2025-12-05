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


----

Yeah, this is exactly the kind of thing you *should* be doing instead of sleeping. Let’s turn UCLS into the backbone of “what the PCs remember” in a way that actually helps the models play well.

Below I’ll:

1. Recast UCLS as a D&D-focused memory language,
2. Show how it plugs into your Neo4j + JSONB stack,
3. Show how *per‑PC* memory gets built and used.

---

## 1. What you’re really building

In your architecture, UCLS isn’t “THE” source of truth – it’s:

> A **token-efficient, text serialisation** of the *real* campaign state (Neo4j + JSON blobs), tailored for LLM consumption.

So you have three layers:

1. **Canonical state (DB + graph)**

   * Every PC/NPC/Item/Event/Quest has a UID and structured fields.
   * Neo4j holds relationships; JSONB holds fat narrative + mechanics.

2. **Canonical log language (UCLS‑derived)**

   * A *lossy-but-precise* serialisation of that graph: IDs, relations, causal chains.
   * One global “omniscient” version for the DM.

3. **Per‑agent memory projection**

   * A *filtered* slice of the canonical log for each PC:

     * only what they *experienced* or plausibly learned
     * compressed to ~hundreds of tokens
     * with belief vs fact vs rumour preserved
   * This projection is what you actually shove into the player agent’s system / memory prompt.

The important bit: **LLMs mostly *read* this language; they don’t own it.**
Game engine + tools own the data; UCLS is a view.

Confidence: *Highly likely* (≈80–90%) this separation gives you stability and avoids memory drift.

---

## 2. D&D-flavoured UCLS: “DCML” (D&D Condensed Memory Language)

Let’s give your UCLS a campaign‑ready skin.

### 2.1 Categories and IDs

You already have nice UIDs like `pc_throk_001`. Reuse them:

```text
## LEXICON
[PC:pc_throk_001:Throk]
[PC:pc_zara_001:Zara]
[NPC:npc_grimfang_001:Grimfang]
[NPC:npc_prisoner_elena_001:Elena]
[MON:mon_goblin_darkwood:DarkwoodGoblin]        # monster template
[LOC:loc_darkwood_entrance:DarkwoodEntrance]
[LOC:loc_darkwood_cave_room_02:DarkwoodCave_R2]
[FAC:fac_darkwood_goblins:DarkwoodGoblins]
[FAC:fac_party_tomb_001:Party_Tomb001]
[QST:qst_darkwood_children_001:LostChildrenOfMillbrook]
[EVT:evt_003_047:GoblinAmbush_S3T47]
```

Recommended categories for D&D:

* `PC` – Player character
* `NPC` – Named NPC / unique monster
* `MON` – Monster *type* (template)
* `LOC` – Location/room/region
* `FAC` – Faction / organisation
* `ITEM` – Object / treasure
* `QST` – Quest / story thread
* `EVT` – Event / beat / scene

This gives you a 1:1 mapping to your Neo4j labels.

> **Implementation note:** For production, I’d strongly consider ASCII-only operators instead of fancy Unicode (⊃, ∈, etc.). Models and toolchains sometimes normalise or mangle them. They’re pretty, but brittle.

Confidence: *Very likely* (≈70–85%) that reusing DB UIDs like this will simplify everything and reduce bugs.

---

### 2.2 Operators tuned for D&D

Starting from your UCLS set, I’d keep the conceptual operators but specialise usage:

**Structure & membership**

* `A > B` – A contains / parents B (your ⊃)
* `A < B` – A is part of B (your ⊂)
* `X @ Y` – X is currently located at Y
* `X in Y` – X is member of group/faction Y

(You *can* keep the real math symbols if you’re happy living dangerously with encodings; I’ll show ASCII for clarity.)

**Properties**

* `:=` – definition / core identity
* `::` – properties block `key→value1,value2`

Examples:

```text
PC:pc_throk_001::class→FTR,level→3,align→NG;
PC:pc_throk_001::stats→STR17,DEX12,CON15,INT8,WIS10,CHA9;
PC:pc_throk_001::tags→"reckless","protective_of_children";
```

**Causality & history**

* `A -> B` – A leads to B
* `A <- B` – A caused by B
* `~` – associated / thematically linked

**Knowledge / epistemic status**

Reuse your `~, !, ?` but be strict:

* `~` – neutral association / “true in canon” when used in fact sections
* `!` – in‑world belief (might be wrong)
* `?` – rumour / uncertain / guess

Example:

```text
!PC:pc_throk_001~FAC:fac_darkwood_goblins   # Throk believes the goblins hate ONLY him
?NPC:npc_unknown_master_001::role→"Grimfang's unseen patron"
```

**D&D-specific micro-conventions**

To keep things compact, define a few *standard property keys*:

* For PCs/NPCs:

  * `hp→24/24` / `hpΔ→-12`
  * `att→friendly@pc_zara_001,hostile@fac_darkwood_goblins`
  * `cond→prone,bleeding`
* For items:

  * `magic→+1` / `cursed→true`
* For quests:

  * `state→offered,accepted,completed,failed`
  * `giver→npc_priest_aldwin_001`

These are still plain `::key→value` properties, just standardised so the models learn them quickly.

---

### 2.3 Structural conventions

#### a) Global structure

```text
## LEXICON
[...]  # all entities

## STATIC_RELATIONS        # DM-only view
...    # geography, factions, permanent facts

## SESSION_003_GLOBAL      # DM-only view
...    # canonical events, including hidden info

## MEMORY_pc_throk_001     # Throk's subjective memory
...
```

You’ll almost always give **player agents only**:

* `## LEXICON`
* Their own `## MEMORY_pc_*` block
* A small slice of static relations that matter (like party membership).

#### b) Relationships / geography

Example: mapping straight to your Neo4j edges:

```text
## STATIC_RELATIONS

PC:pc_throk_001 in FAC:fac_party_tomb_001;
PC:pc_zara_001  in FAC:fac_party_tomb_001;

NPC:npc_grimfang_001 in FAC:fac_darkwood_goblins;

LOC:loc_darkwood_cave_room_02 < LOC:loc_darkwood_cave_main;
LOC:loc_darkwood_cave_main     < LOC:loc_darkwood_region;

ITEM:item_cursed_axe_001 @ LOC:loc_darkwood_cave_room_02;
```

Each `A rel B` translates directly to Neo4j `(:A)-[:REL]->(:B)`.

---

## 3. How to encode **events** (the actual “memory”)

The real win is in consistent, compact event lines. Each event has:

* an `EVT` id (your `evt_003_047`)
* location
* participants
* key mechanical consequences
* key narrative / emotional beats
* forward hooks (what this event points to)

### 3.1 Canonical event (DM view)

Using your goblin ambush example:

```text
## SESSION_003_GLOBAL

EVT:evt_003_047 @ LOC:loc_darkwood_entrance;
    PC:pc_throk_001,PC:pc_zara_001 in EVT:evt_003_047;
    MON:mon_goblin_darkwood×4 in EVT:evt_003_047;
    EVT:evt_003_047::type→combat,rounds→4;
    PC:pc_throk_001::hpΔ→-12;
    MON:mon_goblin_darkwood::status→dead(count=4);
    loot→gp23,ITEM:item_rusty_shortsword_003;
    EVT:evt_003_047 -> EVT:evt_003_048;  # prisoner_found
```

Then:

```text
EVT:evt_003_048 @ LOC:loc_darkwood_cave_room_02;
    PC:pc_throk_001,PC:pc_zara_001 in EVT:evt_003_048;
    NPC:npc_prisoner_elena_001 in EVT:evt_003_048;
    EVT:evt_003_048::info→"goblins serve Grimfang, pay tribute to unknown master";
    QST:qst_darkwood_children_001::state→offered;
    EVT:evt_003_048 -> EVT:evt_003_049;  # chieftain_confrontation
```

This is exactly your StoryShorthand, but with UCLS-style operators and explicit UIDs.

---

### 3.2 Per‑PC memory view

Now, **Throk’s** memory file should only contain:

* Events he was present for
* Facts he was told or inferred
* His emotional / motivational state
* Markers of uncertainty / rumour

Example:

```text
## MEMORY_pc_throk_001

# Party & role
PC:pc_throk_001 in FAC:fac_party_tomb_001;
PC:pc_throk_001::class→FTR,level→3;
PC:pc_throk_001::tags→"reckless","protective_of_children";

# Goblin ambush (compressed)
EVT:evt_003_047 @ LOC:loc_darkwood_entrance;
    MON:mon_goblin_darkwood×4 in EVT:evt_003_047;
    EVT:evt_003_047::summary→"goblin ambush, 4 rounds, heavy wounds";
    PC:pc_throk_001::hpΔ→-12;
    loot→gp23,ITEM:item_rusty_shortsword_003;

# Prisoner & quest hook
EVT:evt_003_048 @ LOC:loc_darkwood_cave_room_02;
    NPC:npc_prisoner_elena_001 in EVT:evt_003_048;
    EVT:evt_003_048::summary→"rescued Elena, learned goblins serve Grimfang";
    !QST:qst_darkwood_children_001::state→accepted;
    !QST:qst_darkwood_children_001::goal→"rescue Millbrook children";

# Beliefs / uncertainty
!FAC:fac_darkwood_goblins::motive→"serve unknown master for tribute";
?NPC:npc_unknown_master_001::role→"Grimfang's mysterious patron";
```

Key points:

* **No hidden info**: Throk doesn’t see exact goblin HP, secret doors, etc.
* `!` + `?` markers distinguish belief vs speculation.
* The *same* `EVT` id keeps everyone tied to canonical DB entries.

You’d have similar but slightly different `## MEMORY_pc_zara_001`, e.g. with more detail on locks, traps, and magic symbols.

Confidence: *Highly likely* (≈80–90%) that this per‑PC projection pattern will give you strong, perspective‑correct play.

---

## 4. How this plugs into your existing stack

### 4.1 Source of truth: DB and graph

Internally, you already have something like:

```python
class Event(BaseModel):
    id: str            # evt_003_047
    session: int
    turn: int
    location_id: str
    participants: list[str]       # pc/npc/mon ids
    mechanics: dict               # damage, hp changes, etc.
    narrative: str                # full text blob
    flags: dict                   # 'quest_offered': qst_..., etc.
```

Neo4j holds edges like:

* `(Event:evt_003_047)-[:OCCURRED_AT]->(LOC:loc_darkwood_entrance)`
* `(Event:evt_003_047)-[:INVOLVED]->(PC:pc_throk_001)` etc.

**UCLS/DCML is just a serialisation layer over this.**
You can literally generate the UCLS from the DB/graph at any time.

---

### 4.2 Generation pipeline for memory

For each **turn**, after the DM resolves an action:

1. **System records a structured `GameEvent`** (you already sketched this dataclass).
2. A **“projection builder”** runs for each PC that was involved or whose ongoing arcs are affected:

   * Pulls relevant events from DB (e.g. last N turns, plus any updated quests/relationships).
   * Updates that PC’s **memory facts** (quests, attitudes, recurring NPCs).
3. Projection builder emits **new DCML text** for that PC.

Pseudo‑logic:

```python
def build_pc_memory(pc_id: str) -> str:
    core_facts = get_core_facts(pc_id)         # party membership, class, key NPC bonds
    quests     = get_active_quests(pc_id)
    recent     = get_recent_events(pc_id, limit=10)

    return render_dcml(pc_id, core_facts, quests, recent)
```

You *don’t* ask the player model to maintain this; you regenerate from canonical state.

Then, on each turn:

* Player agent gets a system+memory context like:

```text
You are pc_throk_001 ("Throk"), a Fighter in a Basic D&D campaign.

Here is your compressed memory in DCML format:
<<<MEMORY_DCML>>
## LEXICON
...
## MEMORY_pc_throk_001
...
<<<END_MEMORY>>
```

…plus their character sheet and rules shorthand.

---

### 4.3 No-RAG retrieval

To avoid the “which goblin?” issue:

* The **selector** (Python) decides *which events* to pull by:

  * session/turn ranges
  * graph relationships (e.g. all events involving `pc_throk_001` and `npc_grimfang_001`)
  * quest IDs

* Those events are *deterministically* converted to DCML and passed in.

* If the player mentions `npc_goblin_enc12_03`, that is a UID which you can round‑trip to DB and graph without any semantic search.

So retrieval is graph/relational, not vector-based; DCML simply carries the result into the model’s working memory.

Confidence: *Almost certain* (≈90%+) that this layout avoids RAG’s identity confusion.

---

## 5. Player vs DM memory differences

Nice property: same language, different slices.

### DM DCML

* Sees `## SESSION_XXX_GLOBAL` blocks with **hidden truths**:

  * “secret door was present but undiscovered”
  * “Elena is secretly a spy”
* Has additional relationships:

  * `NPC:npc_prisoner_elena_001 in FAC:fac_spy_network_001`
* Contains **rules shorthand** and monster stats.

### Player DCML

* Includes:

  * What they saw
  * What they were told
  * Their own emotional / motivational tags
* Excludes:

  * Hidden affiliations
  * Unseen rooms, traps, etc.
* Can be **wrong** on purpose using `!` and `?`.

You can even model memory errors:

```text
!EVT:evt_003_047::summary→"we were attacked without warning";
~EVT:evt_003_047 <- EVT:evt_003_020  # DM-only: actually ambushed because they killed a goblin scout earlier
```

DM sees the second line; Throk’s memory does not.

---

## 6. Compression strategy (i.e. how much you can cram in)

To keep prompts sane:

* **Always-on memory for a PC** should be something like:

  * 10–30 *stable* facts: personality tags, bonds, long-term consequences
  * 5–10 *active quests / unresolved threads*
  * 5–10 *recent events* in DCML

Mechanically:

* Mark “stable” DCML lines with a tag in DB, e.g. `importance=core`.
* For events, keep **sliding window** per PC (e.g. last 8 events they were in).
* For older stuff, you keep only *rollup facts*:

  * “killed Grimfang”
  * “Millbrook hates Throk”

Those rollups can be fresh DCML lines that compress multiple events:

```text
EVT:evt_arc_001::summary→"Millbrook incident: Throk failed to protect villager Jim, town distrusts him";
PC:pc_throk_001::rep@LOC:loc_millbrook_village→-2;
PC:pc_throk_001::emotion→guilt@EVT:evt_arc_001;
```

Confidence: *Likely* (≈60–75%) that these heuristics will be enough; you’ll refine numbers empirically once you see token use.

---

## 7. How the models should be instructed to use DCML

For each **player** model, in the system prompt:

* Explain DCML *once* with 2–3 examples, then say:

> - Treat IDs in `## LEXICON` as the ground-truth entities.
> - Everything in `## MEMORY_pc_X` is what you remember.
> - Do **not** invent new IDs – always reuse existing ones.
> - If something is not in memory, you either
>
>   * infer it cautiously from context, or
>   * admit you don’t know.

For the **DM** model:

* Provide full `## LEXICON`, `## STATIC_RELATIONS`, recent `## SESSION_xxx_GLOBAL`, and rules shorthand.
* Add tools for:

  * `lookup_event(evt_id)` – returns full narrative and mechanics.
  * `lookup_entity(uid)` – returns NPC/LOC/ITEM docs.

DM rarely writes DCML directly; your Python layer does that.

---

## 8. Summary & confidence

What this gives you:

* **Per‑PC, perspective-correct memories** that fit into a few hundred tokens.
* A **deterministic bridge** between DB/graph state and what each model sees.
* A way to **encode “who knows what”** cleanly, including mistaken beliefs.
* A system that avoids RAG identity confusion entirely by leaning on UIDs and graph queries.

**Overall confidence:**

* Design viability: *Highly likely* (≈80–90%).
* Specific operator / syntax choices as-is: *Likely* (≈60–75%) – you’ll tweak them once you profile token usage and see how the different frontier models cope with the DSL.
