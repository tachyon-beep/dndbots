"""Neo4j graph store for entity relationships."""

import uuid
from datetime import datetime, timezone
from typing import Any

from neo4j import AsyncGraphDatabase


class Neo4jStore:
    """Async Neo4j store for game entity relationships."""

    def __init__(self, uri: str, username: str, password: str):
        """Initialize Neo4j connection.

        Args:
            uri: Neo4j bolt URI (e.g., bolt://localhost:7687)
            username: Neo4j username
            password: Neo4j password
        """
        self._driver = AsyncGraphDatabase.driver(
            uri, auth=(username, password)
        )

    async def initialize(self) -> None:
        """Verify connection and create indexes."""
        async with self._driver.session() as session:
            # Create indexes for common lookups
            await session.run("""
                CREATE INDEX char_id IF NOT EXISTS
                FOR (c:Character) ON (c.char_id)
            """)
            await session.run("""
                CREATE INDEX loc_id IF NOT EXISTS
                FOR (l:Location) ON (l.location_id)
            """)

    async def close(self) -> None:
        """Close the driver connection."""
        await self._driver.close()

    async def clear_campaign(self, campaign_id: str) -> None:
        """Delete all nodes and relationships for a campaign (for testing)."""
        async with self._driver.session() as session:
            await session.run(
                "MATCH (n {campaign_id: $campaign_id}) DETACH DELETE n",
                campaign_id=campaign_id,
            )

    # Character nodes

    async def create_character(
        self,
        campaign_id: str,
        char_id: str,
        name: str,
        char_class: str,
        level: int,
        **properties,
    ) -> str:
        """Create a character node."""
        async with self._driver.session() as session:
            await session.run(
                """
                MERGE (c:Character {char_id: $char_id})
                SET c.campaign_id = $campaign_id,
                    c.name = $name,
                    c.char_class = $char_class,
                    c.level = $level,
                    c += $properties
                """,
                char_id=char_id,
                campaign_id=campaign_id,
                name=name,
                char_class=char_class,
                level=level,
                properties=properties,
            )
        return char_id

    async def get_character(self, char_id: str) -> dict[str, Any] | None:
        """Get character node by ID."""
        async with self._driver.session() as session:
            result = await session.run(
                "MATCH (c:Character {char_id: $char_id}) RETURN c",
                char_id=char_id,
            )
            record = await result.single()

        if not record:
            return None
        return dict(record["c"])

    # Location nodes

    async def create_location(
        self,
        campaign_id: str,
        location_id: str,
        name: str,
        description: str = "",
        **properties,
    ) -> str:
        """Create a location node."""
        async with self._driver.session() as session:
            await session.run(
                """
                MERGE (l:Location {location_id: $location_id})
                SET l.campaign_id = $campaign_id,
                    l.name = $name,
                    l.description = $description,
                    l += $properties
                """,
                location_id=location_id,
                campaign_id=campaign_id,
                name=name,
                description=description,
                properties=properties,
            )
        return location_id

    # Faction nodes

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

    # Relationships

    async def create_relationship(
        self,
        from_id: str,
        to_id: str,
        rel_type: str,
        properties: dict[str, Any] | None = None,
    ) -> None:
        """Create a relationship between two nodes.

        Args:
            from_id: Source node ID (char_id or location_id)
            to_id: Target node ID
            rel_type: Relationship type (e.g., KILLED, ALLIED_WITH, LOCATED_AT)
            properties: Optional relationship properties
        """
        props = properties or {}
        async with self._driver.session() as session:
            # Find nodes by any ID type
            await session.run(
                f"""
                MATCH (a), (b)
                WHERE (a.char_id = $from_id OR a.location_id = $from_id)
                  AND (b.char_id = $to_id OR b.location_id = $to_id)
                MERGE (a)-[r:{rel_type}]->(b)
                SET r += $properties
                """,
                from_id=from_id,
                to_id=to_id,
                properties=props,
            )

    async def get_relationships(
        self,
        char_id: str,
        rel_type: str | None = None,
        direction: str = "outgoing",
    ) -> list[dict[str, Any]]:
        """Get relationships for a character.

        Args:
            char_id: Character ID
            rel_type: Optional relationship type filter
            direction: "outgoing", "incoming", or "both"
        """
        type_filter = f":{rel_type}" if rel_type else ""

        if direction == "outgoing":
            pattern = f"-[r{type_filter}]->(target)"
        elif direction == "incoming":
            pattern = f"<-[r{type_filter}]-(target)"
        else:
            pattern = f"-[r{type_filter}]-(target)"

        query = f"""
            MATCH (c:Character {{char_id: $char_id}}){pattern}
            RETURN type(r) as rel_type, properties(r) as rel_props,
                   target.name as target_name,
                   coalesce(target.char_id, target.location_id) as target_id
        """

        async with self._driver.session() as session:
            result = await session.run(query, char_id=char_id)
            records = await result.data()

        return records

    async def set_character_location(
        self, char_id: str, location_id: str
    ) -> None:
        """Set a character's current location (replaces existing)."""
        async with self._driver.session() as session:
            # Remove existing LOCATED_AT relationship
            await session.run(
                """
                MATCH (c:Character {char_id: $char_id})-[r:LOCATED_AT]->()
                DELETE r
                """,
                char_id=char_id,
            )
            # Create new relationship
            await session.run(
                """
                MATCH (c:Character {char_id: $char_id})
                MATCH (l:Location {location_id: $location_id})
                MERGE (c)-[:LOCATED_AT]->(l)
                """,
                char_id=char_id,
                location_id=location_id,
            )

    async def get_character_location(
        self, char_id: str
    ) -> dict[str, Any] | None:
        """Get a character's current location."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (c:Character {char_id: $char_id})-[:LOCATED_AT]->(l:Location)
                RETURN l
                """,
                char_id=char_id,
            )
            record = await result.single()

        if not record:
            return None
        return dict(record["l"])

    # Moment recording

    async def record_kill(
        self,
        campaign_id: str,
        attacker_id: str,
        target_id: str,
        weapon: str,
        damage: int,
        session: str,
        turn: int,
        narrative: str = "",
    ) -> str:
        """Record a kill with KILLED relationship and Moment node.

        Args:
            campaign_id: Campaign identifier
            attacker_id: Character ID of attacker
            target_id: Character ID of target (victim)
            weapon: Weapon used
            damage: Damage dealt
            session: Session ID
            turn: Turn number
            narrative: Optional narrative description

        Returns:
            moment_id of the created Moment node
        """
        moment_id = f"moment_{uuid.uuid4().hex[:12]}"
        timestamp = datetime.now(timezone.utc).isoformat()

        async with self._driver.session() as db_session:
            # Create Moment node
            await db_session.run(
                """
                CREATE (m:Moment {
                    moment_id: $moment_id,
                    campaign_id: $campaign_id,
                    moment_type: 'kill',
                    session: $session,
                    turn: $turn,
                    description: $description,
                    timestamp: $timestamp,
                    narrative: $narrative
                })
                """,
                moment_id=moment_id,
                campaign_id=campaign_id,
                session=session,
                turn=turn,
                description=f"{attacker_id} killed {target_id} with {weapon} for {damage} damage",
                timestamp=timestamp,
                narrative=narrative,
            )

            # Create KILLED relationship with properties
            await db_session.run(
                """
                MATCH (a:Character {char_id: $attacker_id})
                MATCH (t:Character {char_id: $target_id})
                MERGE (a)-[r:KILLED]->(t)
                SET r.moment_id = $moment_id,
                    r.weapon = $weapon,
                    r.damage = $damage,
                    r.session = $session,
                    r.turn = $turn,
                    r.timestamp = $timestamp,
                    r.narrative = $narrative
                """,
                attacker_id=attacker_id,
                target_id=target_id,
                moment_id=moment_id,
                weapon=weapon,
                damage=damage,
                session=session,
                turn=turn,
                timestamp=timestamp,
                narrative=narrative,
            )

            # Link attacker to moment (PERFORMED)
            await db_session.run(
                """
                MATCH (a:Character {char_id: $attacker_id})
                MATCH (m:Moment {moment_id: $moment_id})
                MERGE (a)-[:PERFORMED]->(m)
                """,
                attacker_id=attacker_id,
                moment_id=moment_id,
            )

        return moment_id

    async def record_moment(
        self,
        campaign_id: str,
        actor_id: str,
        moment_type: str,
        description: str,
        session: str,
        turn: int,
        narrative: str = "",
        target_id: str | None = None,
    ) -> str:
        """Record a generic noteworthy moment.

        Args:
            campaign_id: Campaign identifier
            actor_id: Character ID of the actor
            moment_type: Type (crit_hit, crit_fail, clutch_save, creative, etc.)
            description: Mechanical description
            session: Session ID
            turn: Turn number
            narrative: Optional narrative description
            target_id: Optional target character ID

        Returns:
            moment_id of the created Moment node
        """
        moment_id = f"moment_{uuid.uuid4().hex[:12]}"
        timestamp = datetime.now(timezone.utc).isoformat()

        async with self._driver.session() as db_session:
            # Create Moment node
            await db_session.run(
                """
                CREATE (m:Moment {
                    moment_id: $moment_id,
                    campaign_id: $campaign_id,
                    moment_type: $moment_type,
                    session: $session,
                    turn: $turn,
                    description: $description,
                    timestamp: $timestamp,
                    narrative: $narrative
                })
                """,
                moment_id=moment_id,
                campaign_id=campaign_id,
                moment_type=moment_type,
                session=session,
                turn=turn,
                description=description,
                timestamp=timestamp,
                narrative=narrative,
            )

            # Link actor to moment (PERFORMED)
            await db_session.run(
                """
                MATCH (a:Character {char_id: $actor_id})
                MATCH (m:Moment {moment_id: $moment_id})
                MERGE (a)-[:PERFORMED]->(m)
                """,
                actor_id=actor_id,
                moment_id=moment_id,
            )

            # If target specified, create appropriate relationship
            if target_id and moment_type == "crit_hit":
                await db_session.run(
                    """
                    MATCH (a:Character {char_id: $actor_id})
                    MATCH (t:Character {char_id: $target_id})
                    MATCH (m:Moment {moment_id: $moment_id})
                    MERGE (a)-[r:CRITTED {moment_id: $moment_id}]->(t)
                    MERGE (t)-[:WITNESSED]->(m)
                    """,
                    actor_id=actor_id,
                    target_id=target_id,
                    moment_id=moment_id,
                )

        return moment_id

    async def get_moment(self, moment_id: str) -> dict | None:
        """Get a Moment node by ID."""
        async with self._driver.session() as session:
            result = await session.run(
                "MATCH (m:Moment {moment_id: $moment_id}) RETURN m",
                moment_id=moment_id,
            )
            record = await result.single()

        if not record:
            return None
        return dict(record["m"])

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

    async def get_character_moments(
        self,
        char_id: str,
        moment_type: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Get moments performed by a character.

        Args:
            char_id: Character ID
            moment_type: Optional filter by type
            limit: Max results

        Returns:
            List of moment dicts
        """
        type_filter = "AND m.moment_type = $moment_type" if moment_type else ""

        query = f"""
            MATCH (c:Character {{char_id: $char_id}})-[:PERFORMED]->(m:Moment)
            WHERE true {type_filter}
            RETURN m
            ORDER BY m.timestamp DESC
            LIMIT $limit
        """

        async with self._driver.session() as session:
            result = await session.run(
                query,
                char_id=char_id,
                moment_type=moment_type,
                limit=limit,
            )
            records = await result.data()

        return [dict(r["m"]) for r in records]

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

    # Session recap methods

    async def get_session_moments(
        self,
        campaign_id: str,
        session_id: str,
    ) -> list[dict]:
        """Get all moments from a specific session.

        Args:
            campaign_id: Campaign ID
            session_id: Session ID

        Returns:
            List of moment dicts, ordered by turn
        """
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (m:Moment {campaign_id: $campaign_id, session: $session_id})
                RETURN m
                ORDER BY m.turn ASC
                """,
                campaign_id=campaign_id,
                session_id=session_id,
            )
            records = await result.data()

        return [dict(r["m"]) for r in records]

    async def get_last_session_id(self, campaign_id: str) -> str | None:
        """Get the most recent session ID for a campaign.

        Args:
            campaign_id: Campaign ID

        Returns:
            Session ID or None if no sessions
        """
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (m:Moment {campaign_id: $campaign_id})
                RETURN DISTINCT m.session as session
                ORDER BY m.session DESC
                LIMIT 1
                """,
                campaign_id=campaign_id,
            )
            record = await result.single()

        return record["session"] if record else None

    async def mark_npc_encountered(
        self,
        npc_id: str,
        session_id: str,
        status: str = "neutral",
    ) -> None:
        """Mark an NPC as encountered in a session.

        Args:
            npc_id: NPC character ID
            session_id: Session ID
            status: Relationship status (friendly, hostile, neutral)
        """
        async with self._driver.session() as session:
            await session.run(
                """
                MATCH (c:Character {char_id: $npc_id})
                SET c.last_encountered = $session_id,
                    c.encounter_status = $status
                """,
                npc_id=npc_id,
                session_id=session_id,
                status=status,
            )

    async def get_active_npcs(
        self,
        campaign_id: str,
        session_id: str,
    ) -> list[dict]:
        """Get NPCs encountered in a session.

        Args:
            campaign_id: Campaign ID
            session_id: Session ID

        Returns:
            List of NPC dicts with name, class, status
        """
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (c:Character {campaign_id: $campaign_id})
                WHERE c.last_encountered = $session_id
                  AND c.char_id STARTS WITH 'npc_'
                RETURN c.char_id as char_id, c.name as name,
                       c.char_class as char_class, c.encounter_status as status
                """,
                campaign_id=campaign_id,
                session_id=session_id,
            )
            records = await result.data()

        return records
