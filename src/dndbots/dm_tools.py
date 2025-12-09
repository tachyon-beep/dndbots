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
