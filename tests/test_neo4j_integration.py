"""Integration tests for Neo4j connection via Campaign."""

import os
import pytest
import tempfile

from dndbots.campaign import Campaign
from dndbots.models import Character, Stats


# Skip if Neo4j not configured
pytestmark = pytest.mark.skipif(
    not os.getenv("NEO4J_URI"),
    reason="NEO4J_URI not set"
)


@pytest.fixture
def neo4j_config():
    """Get Neo4j config from environment."""
    return {
        "uri": os.getenv("NEO4J_URI"),
        "username": os.getenv("NEO4J_USER", "neo4j"),
        "password": os.getenv("NEO4J_PASSWORD", ""),
    }


@pytest.fixture
async def campaign_with_neo4j(neo4j_config):
    """Create a campaign with Neo4j enabled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        campaign = Campaign(
            campaign_id="test_neo4j_integration",
            name="Test Campaign",
            db_path=f"{tmpdir}/test.db",
            neo4j_config=neo4j_config,
        )
        await campaign.initialize()

        yield campaign

        # Cleanup
        if campaign._neo4j:
            await campaign._neo4j.clear_campaign("test_neo4j_integration")
        await campaign.close()


class TestNeo4jIntegration:
    """Test Neo4j integration through Campaign."""

    async def test_campaign_initializes_neo4j(self, campaign_with_neo4j):
        """Campaign should initialize Neo4j when config provided."""
        assert campaign_with_neo4j._neo4j is not None

    async def test_add_character_creates_graph_node(self, campaign_with_neo4j):
        """Adding a character should create a node in Neo4j."""
        char = Character(
            name="TestHero",
            char_class="Fighter",
            level=1,
            hp=10,
            hp_max=10,
            ac=5,
            stats=Stats(str=14, dex=12, con=13, int=10, wis=11, cha=9),
            equipment=["sword"],
            gold=50,
        )

        char_id = await campaign_with_neo4j.add_character(char)

        # Verify node exists in Neo4j
        node = await campaign_with_neo4j._neo4j.get_character(char_id)
        assert node is not None
        assert node["name"] == "TestHero"
        assert node["char_class"] == "Fighter"
