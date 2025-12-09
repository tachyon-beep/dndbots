# Neo4j Phase D: DM Narrative Tools

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Give DM tools for narrative relationships (NPCs, factions) and graph queries.

**Architecture:** Create dm_tools.py with narrative recording and query tools. Wire into DM agent in game.py.

**Tech Stack:** Neo4jStore, game.py, new dm_tools.py

---

## Task 1: Create DM Tools Module

**Files:**
- Create: `src/dndbots/dm_tools.py`
- Create: `tests/test_dm_tools.py`

**Step 1: Write the failing test**

```python
"""Tests for DM narrative tools."""

import pytest
from unittest.mock import AsyncMock

from dndbots.dm_tools import create_dm_tools


class TestDMTools:
    """Test DM tool creation and basic functionality."""

    def test_create_dm_tools_returns_tools(self):
        """create_dm_tools returns a list of tools."""
        tools = create_dm_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_dm_tools_include_narrative_tools(self):
        """DM tools include narrative management tools."""
        tools = create_dm_tools()
        tool_names = [t.name for t in tools]

        assert "introduce_npc_tool" in tool_names
        assert "set_faction_tool" in tool_names
        assert "enrich_moment_tool" in tool_names

    def test_dm_tools_include_query_tools(self):
        """DM tools include graph query tools."""
        tools = create_dm_tools()
        tool_names = [t.name for t in tools]

        assert "recall_kills_tool" in tool_names
        assert "recall_moments_tool" in tool_names


class TestIntroduceNPCTool:
    """Test NPC introduction tool."""

    @pytest.mark.asyncio
    async def test_introduce_npc_creates_character_node(self):
        """introduce_npc_tool creates character node in Neo4j."""
        mock_neo4j = AsyncMock()
        mock_neo4j.create_character = AsyncMock(return_value="npc_grimfang_001")

        tools = create_dm_tools(
            neo4j=mock_neo4j,
            campaign_id="test_campaign",
        )

        introduce_tool = next(t for t in tools if t.name == "introduce_npc_tool")

        result = await introduce_tool.run_json(
            {
                "name": "Grimfang",
                "description": "A scarred goblin chieftain",
                "char_class": "Goblin",
                "faction": "Darkwood Goblins",
            },
            cancellation_token=None,
        )

        mock_neo4j.create_character.assert_called_once()
        assert "Grimfang" in result
        assert "npc_grimfang" in result.lower()


class TestRecallKillsTool:
    """Test kill recall tool."""

    @pytest.mark.asyncio
    async def test_recall_kills_queries_neo4j(self):
        """recall_kills_tool queries KILLED relationships."""
        mock_neo4j = AsyncMock()
        mock_neo4j.get_relationships = AsyncMock(return_value=[
            {"target_name": "Goblin", "rel_props": {"weapon": "sword", "damage": 8}},
            {"target_name": "Grimfang", "rel_props": {"weapon": "axe", "damage": 12}},
        ])

        tools = create_dm_tools(neo4j=mock_neo4j, campaign_id="test")

        recall_tool = next(t for t in tools if t.name == "recall_kills_tool")

        result = await recall_tool.run_json(
            {"character_id": "pc_throk"},
            cancellation_token=None,
        )

        mock_neo4j.get_relationships.assert_called_with("pc_throk", "KILLED")
        assert "Goblin" in result
        assert "Grimfang" in result


class TestEnrichMomentTool:
    """Test moment enrichment tool."""

    @pytest.mark.asyncio
    async def test_enrich_moment_updates_narrative(self):
        """enrich_moment_tool updates moment narrative."""
        mock_neo4j = AsyncMock()
        mock_neo4j.update_moment_narrative = AsyncMock(return_value=True)

        tools = create_dm_tools(neo4j=mock_neo4j, campaign_id="test")

        enrich_tool = next(t for t in tools if t.name == "enrich_moment_tool")

        result = await enrich_tool.run_json(
            {
                "moment_id": "moment_abc123",
                "narrative": "Throk's blade sang through the air, cleaving the goblin in two",
            },
            cancellation_token=None,
        )

        mock_neo4j.update_moment_narrative.assert_called_once()
        assert "updated" in result.lower() or "enriched" in result.lower()
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_dm_tools.py -v
```

Expected: FAIL - module doesn't exist

**Step 3: Create dm_tools.py**

Create `src/dndbots/dm_tools.py`:

```python
"""DM narrative and query tools for Neo4j graph."""

import uuid
from typing import TYPE_CHECKING

from autogen_core.tools import FunctionTool

if TYPE_CHECKING:
    from dndbots.storage.neo4j_store import Neo4jStore


def create_dm_tools(
    neo4j: "Neo4jStore | None" = None,
    campaign_id: str | None = None,
) -> list[FunctionTool]:
    """Create DM tools for narrative management and graph queries.

    Args:
        neo4j: Optional Neo4jStore for persistence
        campaign_id: Campaign ID for recording

    Returns:
        List of FunctionTool instances
    """

    # === NARRATIVE TOOLS ===

    async def introduce_npc_tool(
        name: str,
        description: str,
        char_class: str = "NPC",
        faction: str | None = None,
        level: int = 1,
    ) -> str:
        """Introduce a new NPC to the campaign.

        Use when an NPC becomes significant enough to track - named enemies,
        quest givers, recurring characters. Generic enemies don't need this.

        Args:
            name: NPC name (e.g., "Grimfang")
            description: Brief description (e.g., "A scarred goblin chieftain")
            char_class: Type/class (e.g., "Goblin", "Merchant", "Guard")
            faction: Optional faction name (e.g., "Darkwood Goblins")
            level: NPC level, default 1

        Returns:
            Confirmation with NPC ID
        """
        npc_id = f"npc_{name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:4]}"

        if neo4j and campaign_id:
            await neo4j.create_character(
                campaign_id=campaign_id,
                char_id=npc_id,
                name=name,
                char_class=char_class,
                level=level,
                description=description,
            )

            # Link to faction if specified
            if faction:
                faction_id = f"fac_{faction.lower().replace(' ', '_')}"
                # Ensure faction exists
                await neo4j.create_faction(campaign_id, faction_id, faction)
                await neo4j.create_relationship(
                    from_id=npc_id,
                    to_id=faction_id,
                    rel_type="MEMBER_OF",
                )

            return f"NPC introduced: {name} ({npc_id}) - {description}"
        else:
            return f"NPC noted (not persisted): {name} - {description}"

    async def set_faction_tool(
        entity_id: str,
        faction_name: str,
        role: str = "member",
    ) -> str:
        """Set an entity's faction membership.

        Args:
            entity_id: Character ID (PC or NPC)
            faction_name: Faction name (e.g., "Darkwood Goblins")
            role: Role in faction (e.g., "chieftain", "member", "ally")

        Returns:
            Confirmation message
        """
        if neo4j and campaign_id:
            faction_id = f"fac_{faction_name.lower().replace(' ', '_')}"
            await neo4j.create_faction(campaign_id, faction_id, faction_name)
            await neo4j.create_relationship(
                from_id=entity_id,
                to_id=faction_id,
                rel_type="MEMBER_OF",
                properties={"role": role},
            )
            return f"Set {entity_id} as {role} of {faction_name}"
        else:
            return f"Faction relation noted (not persisted): {entity_id} -> {faction_name}"

    async def enrich_moment_tool(
        moment_id: str,
        narrative: str,
    ) -> str:
        """Add narrative flavor to a recorded moment.

        Use to enrich mechanical records with dramatic description.
        Example: Turn "pc_throk killed npc_goblin_03" into
        "Throk's blade sang through the air, cleaving the goblin in two"

        Args:
            moment_id: The moment ID to enrich (e.g., "moment_abc123")
            narrative: Dramatic description of what happened

        Returns:
            Confirmation message
        """
        if neo4j:
            await neo4j.update_moment_narrative(moment_id, narrative)
            return f"Moment {moment_id} enriched with narrative"
        else:
            return f"Narrative noted (not persisted): {narrative}"

    # === QUERY TOOLS ===

    async def recall_kills_tool(character_id: str) -> str:
        """Recall who a character has killed.

        Args:
            character_id: Character ID (e.g., "pc_throk")

        Returns:
            Summary of kills
        """
        if neo4j:
            kills = await neo4j.get_relationships(character_id, "KILLED")
            if not kills:
                return f"{character_id} has not killed anyone (recorded)."

            lines = [f"{character_id} has killed:"]
            for kill in kills:
                props = kill.get("rel_props", {})
                weapon = props.get("weapon", "unknown weapon")
                damage = props.get("damage", "?")
                narrative = props.get("narrative", "")

                line = f"- {kill['target_name']} ({weapon}, {damage} damage)"
                if narrative:
                    line += f" - {narrative}"
                lines.append(line)

            return "\n".join(lines)
        else:
            return "Neo4j not configured - cannot recall kills."

    async def recall_moments_tool(
        character_id: str | None = None,
        location_id: str | None = None,
        moment_type: str | None = None,
        limit: int = 5,
    ) -> str:
        """Recall memorable moments from the campaign.

        Args:
            character_id: Filter by character (who performed the moment)
            location_id: Filter by location (where it happened)
            moment_type: Filter by type (kill, crit_hit, creative, etc.)
            limit: Max results (default 5)

        Returns:
            Summary of moments
        """
        if neo4j:
            if character_id:
                moments = await neo4j.get_character_moments(
                    character_id,
                    moment_type=moment_type,
                    limit=limit,
                )
            else:
                moments = await neo4j.get_campaign_moments(
                    campaign_id,
                    moment_type=moment_type,
                    limit=limit,
                )

            if not moments:
                return "No memorable moments recorded yet."

            lines = ["Memorable moments:"]
            for m in moments:
                desc = m.get("description", "")
                narrative = m.get("narrative", "")
                mtype = m.get("moment_type", "moment")

                line = f"- [{mtype}] {desc}"
                if narrative:
                    line += f"\n  \"{narrative}\""
                lines.append(line)

            return "\n".join(lines)
        else:
            return "Neo4j not configured - cannot recall moments."

    # Build tool list
    tools = [
        FunctionTool(introduce_npc_tool, description=introduce_npc_tool.__doc__),
        FunctionTool(set_faction_tool, description=set_faction_tool.__doc__),
        FunctionTool(enrich_moment_tool, description=enrich_moment_tool.__doc__),
        FunctionTool(recall_kills_tool, description=recall_kills_tool.__doc__),
        FunctionTool(recall_moments_tool, description=recall_moments_tool.__doc__),
    ]

    return tools
```

**Step 4: Run tests**

```bash
pytest tests/test_dm_tools.py -v
```

Expected: Some tests may fail due to missing Neo4jStore methods

**Step 5: Commit partial progress**

```bash
git add src/dndbots/dm_tools.py tests/test_dm_tools.py
git commit -m "feat(dm): add DM narrative and query tools (WIP)"
```

---

## Task 2: Add Missing Neo4jStore Methods

**Files:**
- Modify: `src/dndbots/storage/neo4j_store.py`
- Modify: `tests/test_neo4j_store.py`

**Step 1: Add create_faction method**

```python
async def create_faction(
    self,
    campaign_id: str,
    faction_id: str,
    name: str,
    description: str = "",
) -> str:
    """Create or update a faction node.

    Args:
        campaign_id: Campaign identifier
        faction_id: Faction ID
        name: Faction name
        description: Optional description

    Returns:
        faction_id
    """
    async with self._driver.session() as session:
        await session.run(
            """
            MERGE (f:Faction {faction_id: $faction_id})
            SET f.campaign_id = $campaign_id,
                f.name = $name,
                f.description = $description
            """,
            faction_id=faction_id,
            campaign_id=campaign_id,
            name=name,
            description=description,
        )
    return faction_id
```

**Step 2: Add update_moment_narrative method**

```python
async def update_moment_narrative(
    self,
    moment_id: str,
    narrative: str,
) -> bool:
    """Update a moment's narrative description.

    Args:
        moment_id: Moment ID
        narrative: New narrative text

    Returns:
        True if updated, False if moment not found
    """
    async with self._driver.session() as session:
        result = await session.run(
            """
            MATCH (m:Moment {moment_id: $moment_id})
            SET m.narrative = $narrative
            RETURN m
            """,
            moment_id=moment_id,
            narrative=narrative,
        )
        record = await result.single()
    return record is not None
```

**Step 3: Add get_campaign_moments method**

```python
async def get_campaign_moments(
    self,
    campaign_id: str,
    moment_type: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Get moments for a campaign.

    Args:
        campaign_id: Campaign ID
        moment_type: Optional type filter
        limit: Max results

    Returns:
        List of moment dicts
    """
    type_filter = "AND m.moment_type = $moment_type" if moment_type else ""

    query = f"""
        MATCH (m:Moment {{campaign_id: $campaign_id}})
        WHERE true {type_filter}
        RETURN m
        ORDER BY m.timestamp DESC
        LIMIT $limit
    """

    async with self._driver.session() as session:
        result = await session.run(
            query,
            campaign_id=campaign_id,
            moment_type=moment_type,
            limit=limit,
        )
        records = await result.data()

    return [dict(r["m"]) for r in records]
```

**Step 4: Add tests for new methods**

Add to `tests/test_neo4j_store.py`:

```python
@pytest.mark.asyncio
async def test_create_faction(self, graph_store):
    """create_faction creates faction node."""
    faction_id = await graph_store.create_faction(
        campaign_id="test_campaign",
        faction_id="fac_goblins",
        name="Darkwood Goblins",
        description="Forest goblin tribe",
    )
    assert faction_id == "fac_goblins"

@pytest.mark.asyncio
async def test_update_moment_narrative(self, graph_store):
    """update_moment_narrative updates existing moment."""
    # Create a moment first
    await graph_store.create_character(
        campaign_id="test_campaign",
        char_id="pc_test",
        name="Test",
        char_class="Fighter",
        level=1,
    )
    moment_id = await graph_store.record_moment(
        campaign_id="test_campaign",
        actor_id="pc_test",
        moment_type="test",
        description="Test moment",
        session="test",
        turn=1,
    )

    # Update narrative
    updated = await graph_store.update_moment_narrative(
        moment_id,
        "Epic narrative description",
    )
    assert updated is True

    # Verify
    moment = await graph_store.get_moment(moment_id)
    assert moment["narrative"] == "Epic narrative description"
```

**Step 5: Run all tests**

```bash
pytest tests/test_neo4j_store.py tests/test_dm_tools.py -v
```

Expected: All PASS

**Step 6: Commit**

```bash
git add src/dndbots/storage/neo4j_store.py tests/test_neo4j_store.py
git commit -m "feat(neo4j): add faction and moment narrative methods"
```

---

## Task 3: Wire DM Tools into Game

**Files:**
- Modify: `src/dndbots/game.py`

**Step 1: Import dm_tools**

```python
from dndbots.dm_tools import create_dm_tools
```

**Step 2: Add DM tools to DM agent**

In `create_dm_agent` function, modify to accept neo4j:

```python
def create_dm_agent(
    scenario: str,
    model: str = "gpt-4o",
    enable_rules_tools: bool = True,
    party_document: str | None = None,
    neo4j: "Neo4jStore | None" = None,
    campaign_id: str | None = None,
) -> AssistantAgent:
    """Create the Dungeon Master agent.

    Args:
        scenario: The adventure scenario
        model: OpenAI model to use
        enable_rules_tools: Enable rules lookup tools (default: True)
        party_document: Optional party background from Session Zero
        neo4j: Optional Neo4jStore for narrative tools
        campaign_id: Campaign ID for recording

    Returns:
        Configured DM agent with optional rules and narrative tools
    """
    model_client = OpenAIChatCompletionClient(model=model)

    # Create rules tools if enabled
    tools = []
    if enable_rules_tools:
        lookup, list_rules, search = create_rules_tools()
        tools = [lookup, list_rules, search]

    # Add DM narrative/query tools if Neo4j configured
    if neo4j and campaign_id:
        dm_tools = create_dm_tools(neo4j=neo4j, campaign_id=campaign_id)
        tools.extend(dm_tools)

    return AssistantAgent(
        name="dm",
        model_client=model_client,
        system_message=build_dm_prompt(scenario, party_document=party_document),
        tools=tools,
        reflect_on_tool_use=True,
    )
```

**Step 3: Update DnDGame to pass neo4j to DM**

In `DnDGame.__init__`:

```python
# Create agents
neo4j_store = campaign._neo4j if campaign else None
campaign_id = campaign.campaign_id if campaign else None

self.dm = create_dm_agent(
    scenario,
    dm_model,
    party_document=party_document,
    neo4j=neo4j_store,
    campaign_id=campaign_id,
)
```

**Step 4: Run game tests**

```bash
pytest tests/test_game.py -v
```

Expected: All PASS

**Step 5: Commit**

```bash
git add src/dndbots/game.py
git commit -m "feat(game): wire DM tools for Neo4j narrative management"
```

---

## Phase D Complete Checklist

- [ ] dm_tools.py module created
- [ ] introduce_npc_tool creates character nodes
- [ ] set_faction_tool manages faction relationships
- [ ] enrich_moment_tool updates moment narratives
- [ ] recall_kills_tool queries KILLED relationships
- [ ] recall_moments_tool queries campaign moments
- [ ] Neo4jStore has create_faction, update_moment_narrative, get_campaign_moments
- [ ] DM agent has access to all tools
- [ ] All tests pass

**Next Phase:** E - Session Recap
