# Neo4j Phase A: Wire Up Connection

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Connect Neo4j to the game by passing environment config to Campaign.

**Architecture:** Read NEO4J_* env vars in cli.py, pass as config dict to Campaign constructor. Campaign already handles initialization.

**Tech Stack:** python-dotenv (already loaded), Neo4j driver (already installed)

---

## Task 1: Add Neo4j Config to CLI

**Files:**
- Modify: `src/dndbots/cli.py:51-66`
- Test: Manual verification

**Step 1: Read the current cli.py run_game function**

Review lines 51-66 to understand current Campaign initialization.

**Step 2: Modify run_game to pass neo4j_config**

```python
async def run_game(session_zero: bool = False) -> None:
    """Run the game with persistence.

    Args:
        session_zero: If True, run Session Zero for collaborative creation
    """
    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Build Neo4j config if environment variables are set
    neo4j_config = None
    if os.getenv("NEO4J_URI"):
        neo4j_config = {
            "uri": os.getenv("NEO4J_URI"),
            "username": os.getenv("NEO4J_USER", "neo4j"),
            "password": os.getenv("NEO4J_PASSWORD", ""),
        }

    # Initialize campaign
    campaign = Campaign(
        campaign_id="default_campaign",
        name="Caves of Chaos",
        db_path=str(DEFAULT_DB),
        neo4j_config=neo4j_config,
    )
    await campaign.initialize()
```

**Step 3: Run existing tests to ensure no regression**

```bash
pytest tests/test_cli.py -v
```

Expected: All tests PASS

**Step 4: Commit**

```bash
git add src/dndbots/cli.py
git commit -m "feat(cli): wire Neo4j config from environment variables"
```

---

## Task 2: Add Integration Test for Neo4j Connection

**Files:**
- Create: `tests/test_neo4j_integration.py`

**Step 1: Write integration test**

```python
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
```

**Step 2: Run test to verify it passes (Neo4j already creates characters)**

```bash
pytest tests/test_neo4j_integration.py -v
```

Expected: All tests PASS (Campaign.add_character already calls neo4j.create_character)

**Step 3: Commit**

```bash
git add tests/test_neo4j_integration.py
git commit -m "test: add Neo4j integration tests for Campaign"
```

---

## Task 3: Verify End-to-End with Manual Test

**Files:**
- None (manual verification)

**Step 1: Start a quick game session**

```bash
source .env && timeout 30 dndbots || true
```

Let it run for ~30 seconds to create characters and start.

**Step 2: Query Neo4j to verify character nodes exist**

```bash
# Using cypher-shell or Neo4j browser
# Query: MATCH (c:Character) RETURN c.name, c.char_class, c.campaign_id
```

Or via Python:

```python
import os
from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)

with driver.session() as session:
    result = session.run("MATCH (c:Character) RETURN c.name, c.char_class, c.campaign_id")
    for record in result:
        print(record)
```

Expected: Character nodes from the game session appear in Neo4j.

**Step 3: Clean up test data (optional)**

```cypher
MATCH (n {campaign_id: 'default_campaign'}) DETACH DELETE n
```

---

## Phase A Complete Checklist

- [ ] Neo4j config read from environment in cli.py
- [ ] Config passed to Campaign constructor
- [ ] Integration test verifies character nodes created
- [ ] Manual verification shows nodes in Neo4j

**Next Phase:** B - Referee Records Kills
