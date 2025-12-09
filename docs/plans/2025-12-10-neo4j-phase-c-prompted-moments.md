# Neo4j Phase C: Referee Prompted Moments

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Give Referee a tool to record creative/dramatic moments at its discretion.

**Architecture:** Add `record_moment_tool` to referee tools. Update Referee prompt with guidance on when to use it.

**Tech Stack:** referee_tools.py, prompts.py

---

## Task 1: Add record_moment_tool to Referee

**Files:**
- Modify: `src/dndbots/referee_tools.py`
- Create: `tests/test_referee_moment_tool.py`

**Step 1: Write the failing test**

```python
"""Tests for Referee moment recording tool."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from dndbots.mechanics import MechanicsEngine
from dndbots.referee_tools import create_referee_tools


class TestRecordMomentTool:
    """Test the record_moment_tool."""

    def test_record_moment_tool_exists(self):
        """record_moment_tool should be in referee tools."""
        engine = MechanicsEngine()
        tools = create_referee_tools(engine)

        tool_names = [t.name for t in tools]
        assert "record_moment_tool" in tool_names

    @pytest.mark.asyncio
    async def test_record_moment_tool_calls_neo4j(self):
        """record_moment_tool should call neo4j.record_moment."""
        engine = MechanicsEngine()
        mock_neo4j = AsyncMock()
        mock_neo4j.record_moment = AsyncMock(return_value="moment_abc123")

        tools = create_referee_tools(
            engine,
            neo4j=mock_neo4j,
            campaign_id="test_campaign",
            session_id="session_001",
        )

        # Find the record_moment_tool
        record_tool = next(t for t in tools if t.name == "record_moment_tool")

        # Call it
        result = await record_tool.run_json(
            {
                "actor_id": "pc_throk",
                "moment_type": "creative",
                "description": "Throk swings from the chandelier to kick the goblin",
            },
            cancellation_token=None,
        )

        # Verify neo4j was called
        mock_neo4j.record_moment.assert_called_once()
        call_args = mock_neo4j.record_moment.call_args
        assert call_args.kwargs["actor_id"] == "pc_throk"
        assert call_args.kwargs["moment_type"] == "creative"
        assert "chandelier" in call_args.kwargs["description"]

    @pytest.mark.asyncio
    async def test_record_moment_tool_without_neo4j(self):
        """record_moment_tool should return gracefully without neo4j."""
        engine = MechanicsEngine()
        tools = create_referee_tools(engine)  # No neo4j

        record_tool = next(t for t in tools if t.name == "record_moment_tool")

        # Should not raise, just return acknowledgment
        result = await record_tool.run_json(
            {
                "actor_id": "pc_throk",
                "moment_type": "creative",
                "description": "Some cool move",
            },
            cancellation_token=None,
        )

        assert "recorded" in result.lower() or "noted" in result.lower()
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_referee_moment_tool.py -v
```

Expected: FAIL - `record_moment_tool` not in tools

**Step 3: Add record_moment_tool to referee_tools.py**

Add inside `create_referee_tools` function:

```python
async def record_moment_tool(
    actor_id: str,
    moment_type: str,
    description: str,
    target_id: str | None = None,
) -> str:
    """Record a noteworthy moment to the campaign history.

    Use this for dramatic, creative, or memorable events that should be
    remembered for future sessions. Examples:
    - Creative tactics: "Throk swings from chandelier to kick goblin off ledge"
    - Environmental actions: "Zara shoots the rope holding the portcullis"
    - Dramatic reversals: "Elena catches the falling torch before it hits the oil"
    - Tense moments: "The party holds their breath as the dragon sniffs the air"

    When in doubt, record it. Missing a cool moment is worse than recording
    a mediocre one.

    Args:
        actor_id: Character ID of who did the cool thing (e.g., "pc_throk")
        moment_type: Type of moment - "creative", "environmental", "dramatic", "tense"
        description: What happened, in 1-2 sentences
        target_id: Optional target character ID if action was directed at someone

    Returns:
        Confirmation message
    """
    if neo4j and campaign_id:
        turn = engine.current_turn if hasattr(engine, 'current_turn') else 0
        moment_id = await neo4j.record_moment(
            campaign_id=campaign_id,
            actor_id=actor_id,
            moment_type=moment_type,
            description=description,
            session=session_id or "unknown",
            turn=turn,
            target_id=target_id,
        )
        return f"Moment recorded: {moment_id}. {description}"
    else:
        return f"Moment noted (not persisted): {description}"
```

Add to the tools list:
```python
tools = [
    # ... existing tools ...
    FunctionTool(record_moment_tool, description=record_moment_tool.__doc__),
]
```

**Step 4: Run tests**

```bash
pytest tests/test_referee_moment_tool.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/dndbots/referee_tools.py tests/test_referee_moment_tool.py
git commit -m "feat(referee): add record_moment_tool for creative actions"
```

---

## Task 2: Update Referee Prompt with Moment Guidance

**Files:**
- Modify: `src/dndbots/prompts.py`
- Modify: `tests/test_prompts.py`

**Step 1: Write the failing test**

Add to `tests/test_prompts.py`:

```python
def test_referee_prompt_includes_moment_recording_guidance(self):
    """Referee prompt includes guidance on recording moments."""
    prompt = build_referee_prompt()
    assert "record_moment" in prompt.lower()
    assert "creative" in prompt.lower()
    assert "environmental" in prompt.lower()
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_prompts.py::TestRefereePrompt::test_referee_prompt_includes_moment_recording_guidance -v
```

Expected: FAIL

**Step 3: Update referee prompt in prompts.py**

In `build_referee_prompt`, add a new section after `=== STYLE ===`:

```python
=== RECORDING MOMENTS ===
Use record_moment_tool for noteworthy events beyond standard mechanics:

ALWAYS RECORD:
- Creative tactics (swinging from chandeliers, improvised weapons)
- Environmental actions (shooting ropes, collapsing pillars, using terrain)
- Dramatic reversals (catching falling allies, last-second saves)
- Tense standoffs (holding breath, bluffing, nerve-wracking skill uses)

MOMENT TYPES:
- "creative" - Clever or unexpected player tactics
- "environmental" - Using the environment as weapon/tool
- "dramatic" - Emotional or story-significant beats
- "tense" - Held-breath moments of uncertainty

When in doubt, record it. Missing a cool moment is worse than recording a mediocre one.

Example calls:
  record_moment_tool("pc_throk", "creative", "Throk kicks the table into the goblins")
  record_moment_tool("pc_zara", "environmental", "Zara cuts the rope bridge while enemies cross")
```

**Step 4: Run test**

```bash
pytest tests/test_prompts.py::TestRefereePrompt::test_referee_prompt_includes_moment_recording_guidance -v
```

Expected: PASS

**Step 5: Run all prompt tests**

```bash
pytest tests/test_prompts.py -v
```

Expected: All PASS

**Step 6: Commit**

```bash
git add src/dndbots/prompts.py tests/test_prompts.py
git commit -m "feat(prompts): add moment recording guidance to Referee"
```

---

## Phase C Complete Checklist

- [ ] record_moment_tool exists in referee tools
- [ ] Tool correctly calls neo4j.record_moment when configured
- [ ] Tool returns gracefully when neo4j not configured
- [ ] Referee prompt includes moment recording guidance
- [ ] Moment types documented (creative, environmental, dramatic, tense)
- [ ] All tests pass

**Next Phase:** D - DM Narrative Tools
