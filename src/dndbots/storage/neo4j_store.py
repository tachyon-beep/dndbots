"""Neo4j graph store for entity relationships."""

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
