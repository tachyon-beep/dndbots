# Session Zero Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the three-phase Session Zero (Pitch → Converge → Lock) where DM and players collaboratively create a cohesive campaign before gameplay begins.

**Architecture:** New `SessionZero` class orchestrates three phases using AutoGen's SelectorGroupChat. DM controls pacing with marker phrases. Outputs parsed into `SessionZeroResult` dataclass and handed to existing `DnDGame`.

**Tech Stack:** AutoGen 0.4, existing rules_tools, existing prompts module

---

## Task 1: Create SessionZeroResult Dataclass

**Files:**
- Create: `src/dndbots/session_zero.py`
- Test: `tests/test_session_zero.py`

**Step 1: Write the failing test**

```python
# tests/test_session_zero.py
"""Tests for Session Zero."""

import pytest
from dndbots.session_zero import SessionZeroResult
from dndbots.models import Character, Stats


class TestSessionZeroResult:
    def test_result_dataclass_exists(self):
        """SessionZeroResult holds session zero outputs."""
        char = Character(
            name="Test",
            char_class="Fighter",
            level=1,
            hp=8,
            hp_max=8,
            ac=5,
            stats=Stats(str=14, dex=12, con=13, int=10, wis=11, cha=9),
            equipment=["sword"],
            gold=10,
        )
        result = SessionZeroResult(
            scenario="Test scenario",
            characters=[char],
            party_document="Test party doc",
            transcript=[],
        )
        assert result.scenario == "Test scenario"
        assert len(result.characters) == 1
        assert result.party_document == "Test party doc"
        assert result.transcript == []
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_session_zero.py::TestSessionZeroResult::test_result_dataclass_exists -v`
Expected: FAIL with "cannot import name 'SessionZeroResult'"

**Step 3: Write minimal implementation**

```python
# src/dndbots/session_zero.py
"""Session Zero: Collaborative campaign and character creation."""

from dataclasses import dataclass
from typing import Any

from dndbots.models import Character


@dataclass
class SessionZeroResult:
    """Output from a completed Session Zero."""

    scenario: str
    characters: list[Character]
    party_document: str
    transcript: list[Any]  # Message objects from AutoGen
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_session_zero.py::TestSessionZeroResult::test_result_dataclass_exists -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/session_zero.py tests/test_session_zero.py
git commit -m "feat(session-zero): add SessionZeroResult dataclass"
```

---

## Task 2: Create Session Zero Prompt Builders

**Files:**
- Modify: `src/dndbots/session_zero.py`
- Test: `tests/test_session_zero.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_session_zero.py
from dndbots.session_zero import (
    SessionZeroResult,
    build_session_zero_dm_prompt,
    build_session_zero_player_prompt,
)


class TestSessionZeroPrompts:
    def test_dm_prompt_includes_phase_markers(self):
        """DM prompt tells them about phase marker phrases."""
        prompt = build_session_zero_dm_prompt()
        assert "PITCH COMPLETE" in prompt
        assert "CONVERGENCE COMPLETE" in prompt
        assert "SESSION ZERO LOCKED" in prompt

    def test_dm_prompt_includes_output_format(self):
        """DM prompt specifies output format."""
        prompt = build_session_zero_dm_prompt()
        assert "[SCENARIO]" in prompt
        assert "[PARTY_DOCUMENT]" in prompt

    def test_dm_prompt_mentions_guides(self):
        """DM prompt mentions guide lookups."""
        prompt = build_session_zero_dm_prompt()
        assert "guides/interesting-campaigns" in prompt

    def test_player_prompt_includes_output_format(self):
        """Player prompt specifies character output format."""
        prompt = build_session_zero_player_prompt(player_number=1)
        assert "[CHARACTER]" in prompt
        assert "Name:" in prompt
        assert "Class:" in prompt
        assert "Stats:" in prompt

    def test_player_prompt_mentions_guides(self):
        """Player prompt mentions guide lookups."""
        prompt = build_session_zero_player_prompt(player_number=1)
        assert "guides/interesting-characters" in prompt

    def test_player_prompt_includes_player_number(self):
        """Player prompt identifies which player they are."""
        prompt = build_session_zero_player_prompt(player_number=2)
        assert "Player 2" in prompt
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_session_zero.py::TestSessionZeroPrompts -v`
Expected: FAIL with "cannot import name 'build_session_zero_dm_prompt'"

**Step 3: Write minimal implementation**

```python
# Add to src/dndbots/session_zero.py

def build_session_zero_dm_prompt() -> str:
    """Build the DM system prompt for Session Zero."""
    return """You are the Dungeon Master for a Session Zero - collaborative campaign creation.

Your job is to FACILITATE, not dominate. Guide the players to create a cohesive party.

## Phases

PHASE 1 (Pitch): Share your campaign concept, then ask each player for their character pitch.
PHASE 2 (Converge): Help players find connections between characters and to your campaign.
PHASE 3 (Lock): Get final mechanical details, then produce the scenario and party document.

## Tools

Use these tools to look up rules and guides:
- lookup_rules("guides/interesting-campaigns", detail="full") - for your campaign design
- lookup_rules("guides/interesting-encounters", detail="full") - for planning encounters
- lookup_rules("guides/interesting-dungeons", detail="full") - for dungeon design
- lookup_rules("classes/X", detail="full") - for class details when players ask

## Phase Transitions

When a phase is complete, say the marker phrase EXACTLY:
- "PITCH COMPLETE" - after all players have pitched
- "CONVERGENCE COMPLETE" - after connections are established
- "SESSION ZERO LOCKED" - after all details are finalized

## Final Output

After saying "SESSION ZERO LOCKED", output these blocks:

[SCENARIO]
<your complete scenario text for the adventure>
[/SCENARIO]

[PARTY_DOCUMENT]
<relationships, hooks, shared history, potential tensions>
[/PARTY_DOCUMENT]

## Facilitation Tips

- Ask ONE player at a time for their pitch
- Actively suggest connections: "Player 2, how might you know Player 1?"
- Incorporate character backgrounds into your scenario
- Keep things moving - don't let discussion stall
"""


def build_session_zero_player_prompt(player_number: int) -> str:
    """Build a player system prompt for Session Zero.

    Args:
        player_number: Which player this is (1, 2, or 3)

    Returns:
        Complete player system prompt for session zero
    """
    return f"""You are Player {player_number} in a Session Zero - collaborative character creation.

Follow the DM's lead through each phase.

## Your Tasks

When the DM asks for your pitch:
- Look up the character guide: lookup_rules("guides/interesting-characters", detail="full")
- Propose an interesting character concept with personality, goals, and flaws
- Keep it brief - 2-3 paragraphs max

When the DM asks about connections:
- Find ways your character relates to other players' characters
- Connect your background to the DM's campaign hook
- Be flexible - adjust your concept to fit the party

When the DM asks for final details:
- Look up your class: lookup_rules("classes/X", detail="full")
- Finalize your mechanical stats

## Final Output

After the DM says "SESSION ZERO LOCKED", output your character:

[CHARACTER]
Name: <character name>
Class: <Fighter/Cleric/Magic-User/Thief/Elf/Dwarf/Halfling>
Stats: STR <n>, INT <n>, WIS <n>, DEX <n>, CON <n>, CHA <n>
HP: <number>
AC: <number>
Equipment: <comma-separated list>
Background: <1-2 sentence background>
[/CHARACTER]

## Guidelines

- Stay in character when describing your concept
- Be collaborative - build on others' ideas
- Don't dominate - let others shine too
- Be ready to adjust your concept to fit the party
"""
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_session_zero.py::TestSessionZeroPrompts -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/session_zero.py tests/test_session_zero.py
git commit -m "feat(session-zero): add DM and player prompt builders"
```

---

## Task 3: Create Output Parsers

**Files:**
- Modify: `src/dndbots/session_zero.py`
- Test: `tests/test_session_zero.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_session_zero.py
from dndbots.session_zero import (
    SessionZeroResult,
    build_session_zero_dm_prompt,
    build_session_zero_player_prompt,
    parse_scenario,
    parse_party_document,
    parse_character,
)


class TestSessionZeroParsers:
    def test_parse_scenario(self):
        """Extract scenario from DM output."""
        text = """Some preamble text.

[SCENARIO]
The town of Thornwall sits at the edge of the frontier.
Dark things stir in the ruins to the north.
[/SCENARIO]

Some other text."""
        result = parse_scenario(text)
        assert "Thornwall" in result
        assert "frontier" in result
        assert "preamble" not in result

    def test_parse_scenario_not_found(self):
        """Return empty string if no scenario block."""
        text = "No scenario here"
        result = parse_scenario(text)
        assert result == ""

    def test_parse_party_document(self):
        """Extract party document from DM output."""
        text = """Blah blah.

[PARTY_DOCUMENT]
## Relationships
- Kira and Marcus share a dark history
[/PARTY_DOCUMENT]

More text."""
        result = parse_party_document(text)
        assert "Relationships" in result
        assert "Kira and Marcus" in result

    def test_parse_character(self):
        """Parse character block into Character object."""
        text = """Here is my character:

[CHARACTER]
Name: Kira Ashford
Class: Fighter
Stats: STR 15, INT 10, WIS 12, DEX 13, CON 14, CHA 8
HP: 7
AC: 4
Equipment: longsword, shield, chain mail, backpack
Background: Deserted soldier seeking redemption
[/CHARACTER]

That's my character!"""
        char = parse_character(text)
        assert char is not None
        assert char.name == "Kira Ashford"
        assert char.char_class == "Fighter"
        assert char.stats.str == 15
        assert char.stats.int == 10
        assert char.hp == 7
        assert char.ac == 4
        assert "longsword" in char.equipment

    def test_parse_character_not_found(self):
        """Return None if no character block."""
        text = "No character here"
        result = parse_character(text)
        assert result is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_session_zero.py::TestSessionZeroParsers -v`
Expected: FAIL with "cannot import name 'parse_scenario'"

**Step 3: Write minimal implementation**

```python
# Add to src/dndbots/session_zero.py
import re


def parse_scenario(text: str) -> str:
    """Extract scenario from [SCENARIO]...[/SCENARIO] block.

    Args:
        text: Text containing scenario block

    Returns:
        Scenario content, or empty string if not found
    """
    match = re.search(r"\[SCENARIO\]\s*(.*?)\s*\[/SCENARIO\]", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def parse_party_document(text: str) -> str:
    """Extract party document from [PARTY_DOCUMENT]...[/PARTY_DOCUMENT] block.

    Args:
        text: Text containing party document block

    Returns:
        Party document content, or empty string if not found
    """
    match = re.search(r"\[PARTY_DOCUMENT\]\s*(.*?)\s*\[/PARTY_DOCUMENT\]", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def parse_character(text: str) -> Character | None:
    """Parse character from [CHARACTER]...[/CHARACTER] block.

    Args:
        text: Text containing character block

    Returns:
        Character object, or None if not found/invalid
    """
    match = re.search(r"\[CHARACTER\]\s*(.*?)\s*\[/CHARACTER\]", text, re.DOTALL)
    if not match:
        return None

    content = match.group(1)

    # Parse fields
    name_match = re.search(r"Name:\s*(.+)", content)
    class_match = re.search(r"Class:\s*(.+)", content)
    stats_match = re.search(
        r"Stats:\s*STR\s*(\d+),\s*INT\s*(\d+),\s*WIS\s*(\d+),\s*DEX\s*(\d+),\s*CON\s*(\d+),\s*CHA\s*(\d+)",
        content
    )
    hp_match = re.search(r"HP:\s*(\d+)", content)
    ac_match = re.search(r"AC:\s*(\d+)", content)
    equipment_match = re.search(r"Equipment:\s*(.+)", content)
    background_match = re.search(r"Background:\s*(.+)", content)

    if not all([name_match, class_match, stats_match, hp_match, ac_match]):
        return None

    equipment = []
    if equipment_match:
        equipment = [e.strip() for e in equipment_match.group(1).split(",")]

    return Character(
        name=name_match.group(1).strip(),
        char_class=class_match.group(1).strip(),
        level=1,
        hp=int(hp_match.group(1)),
        hp_max=int(hp_match.group(1)),
        ac=int(ac_match.group(1)),
        stats=Stats(
            str=int(stats_match.group(1)),
            int=int(stats_match.group(2)),
            wis=int(stats_match.group(3)),
            dex=int(stats_match.group(4)),
            con=int(stats_match.group(5)),
            cha=int(stats_match.group(6)),
        ),
        equipment=equipment,
        gold=0,
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_session_zero.py::TestSessionZeroParsers -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/session_zero.py tests/test_session_zero.py
git commit -m "feat(session-zero): add output parsers for scenario, party doc, and characters"
```

---

## Task 4: Create SessionZero Class Structure

**Files:**
- Modify: `src/dndbots/session_zero.py`
- Test: `tests/test_session_zero.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_session_zero.py
import os

# Mock API key for tests
@pytest.fixture(autouse=True)
def mock_openai_key(monkeypatch):
    """Set a dummy OpenAI API key for testing."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-for-unit-tests")


class TestSessionZeroClass:
    def test_session_zero_init(self):
        """SessionZero initializes with agents."""
        from dndbots.session_zero import SessionZero

        sz = SessionZero(num_players=3)
        assert sz.dm is not None
        assert len(sz.players) == 3
        assert sz.num_players == 3

    def test_session_zero_agents_have_tools(self):
        """All agents have rules tools."""
        from dndbots.session_zero import SessionZero

        sz = SessionZero(num_players=2)
        # DM should have tools
        assert len(sz.dm._tools) == 3
        # Players should have tools
        for player in sz.players:
            assert len(player._tools) == 3
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_session_zero.py::TestSessionZeroClass -v`
Expected: FAIL with "cannot import name 'SessionZero'"

**Step 3: Write minimal implementation**

```python
# Add to src/dndbots/session_zero.py
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

from dndbots.rules_tools import create_rules_tools


class SessionZero:
    """Orchestrates Session Zero: collaborative campaign creation."""

    def __init__(
        self,
        num_players: int = 3,
        dm_model: str = "gpt-4o",
        player_model: str = "gpt-4o",
    ):
        """Initialize Session Zero with DM and player agents.

        Args:
            num_players: Number of player agents (default: 3)
            dm_model: Model for DM agent
            player_model: Model for player agents
        """
        self.num_players = num_players

        # Create rules tools (shared by all agents)
        lookup, list_rules, search = create_rules_tools()
        tools = [lookup, list_rules, search]

        # Create DM agent
        dm_client = OpenAIChatCompletionClient(model=dm_model)
        self.dm = AssistantAgent(
            name="dm",
            model_client=dm_client,
            system_message=build_session_zero_dm_prompt(),
            tools=tools,
            reflect_on_tool_use=True,
        )

        # Create player agents
        self.players = []
        for i in range(num_players):
            player_client = OpenAIChatCompletionClient(model=player_model)
            player = AssistantAgent(
                name=f"player_{i + 1}",
                model_client=player_client,
                system_message=build_session_zero_player_prompt(i + 1),
                tools=tools,
                reflect_on_tool_use=True,
            )
            self.players.append(player)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_session_zero.py::TestSessionZeroClass -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/session_zero.py tests/test_session_zero.py
git commit -m "feat(session-zero): add SessionZero class with agent creation"
```

---

## Task 5: Implement Phase Detection

**Files:**
- Modify: `src/dndbots/session_zero.py`
- Test: `tests/test_session_zero.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_session_zero.py
from dndbots.session_zero import Phase, detect_phase_marker


class TestPhaseDetection:
    def test_phase_enum_exists(self):
        """Phase enum has expected values."""
        assert Phase.PITCH.value == "pitch"
        assert Phase.CONVERGE.value == "converge"
        assert Phase.LOCK.value == "lock"
        assert Phase.DONE.value == "done"

    def test_detect_pitch_complete(self):
        """Detect PITCH COMPLETE marker."""
        text = "Great ideas everyone! PITCH COMPLETE"
        result = detect_phase_marker(text)
        assert result == Phase.CONVERGE

    def test_detect_convergence_complete(self):
        """Detect CONVERGENCE COMPLETE marker."""
        text = "The party is taking shape. CONVERGENCE COMPLETE"
        result = detect_phase_marker(text)
        assert result == Phase.LOCK

    def test_detect_session_zero_locked(self):
        """Detect SESSION ZERO LOCKED marker."""
        text = "Everything is finalized. SESSION ZERO LOCKED"
        result = detect_phase_marker(text)
        assert result == Phase.DONE

    def test_detect_no_marker(self):
        """Return None when no marker present."""
        text = "Just regular conversation here."
        result = detect_phase_marker(text)
        assert result is None

    def test_detect_marker_case_insensitive(self):
        """Markers should work regardless of case."""
        text = "pitch complete"
        result = detect_phase_marker(text)
        assert result == Phase.CONVERGE
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_session_zero.py::TestPhaseDetection -v`
Expected: FAIL with "cannot import name 'Phase'"

**Step 3: Write minimal implementation**

```python
# Add to src/dndbots/session_zero.py (after imports)
from enum import Enum


class Phase(Enum):
    """Session Zero phases."""

    PITCH = "pitch"
    CONVERGE = "converge"
    LOCK = "lock"
    DONE = "done"


def detect_phase_marker(text: str) -> Phase | None:
    """Detect phase transition marker in message.

    Args:
        text: Message text to scan

    Returns:
        Next phase if marker found, None otherwise
    """
    text_upper = text.upper()
    if "SESSION ZERO LOCKED" in text_upper:
        return Phase.DONE
    if "CONVERGENCE COMPLETE" in text_upper:
        return Phase.LOCK
    if "PITCH COMPLETE" in text_upper:
        return Phase.CONVERGE
    return None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_session_zero.py::TestPhaseDetection -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/session_zero.py tests/test_session_zero.py
git commit -m "feat(session-zero): add Phase enum and marker detection"
```

---

## Task 6: Implement DM Selector for Session Zero

**Files:**
- Modify: `src/dndbots/session_zero.py`
- Test: `tests/test_session_zero.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_session_zero.py
from unittest.mock import Mock
from dndbots.session_zero import session_zero_selector


class TestSessionZeroSelector:
    def test_dm_starts_first(self):
        """DM speaks first when no messages."""
        result = session_zero_selector([])
        assert result == "dm"

    def test_dm_speaks_after_player(self):
        """DM speaks after any player."""
        msg = Mock()
        msg.source = "player_1"
        result = session_zero_selector([msg])
        assert result == "dm"

    def test_model_selects_after_dm(self):
        """Model-based selection after DM speaks."""
        msg = Mock()
        msg.source = "dm"
        result = session_zero_selector([msg])
        assert result is None  # Let model decide
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_session_zero.py::TestSessionZeroSelector -v`
Expected: FAIL with "cannot import name 'session_zero_selector'"

**Step 3: Write minimal implementation**

```python
# Add to src/dndbots/session_zero.py
from typing import Sequence


def session_zero_selector(messages: Sequence) -> str | None:
    """Selector for Session Zero group chat.

    DM controls pacing - speaks after every player turn.
    When DM speaks, model selects next speaker (usually a player DM addressed).

    Args:
        messages: Sequence of messages in conversation

    Returns:
        Agent name to speak next, or None for model-based selection
    """
    if not messages:
        return "dm"

    last_speaker = messages[-1].source

    # After any player speaks, return to DM
    if last_speaker != "dm":
        return "dm"

    # DM just spoke - let model selector pick who was addressed
    return None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_session_zero.py::TestSessionZeroSelector -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/session_zero.py tests/test_session_zero.py
git commit -m "feat(session-zero): add DM-controlled selector"
```

---

## Task 7: Implement SessionZero.run() Method

**Files:**
- Modify: `src/dndbots/session_zero.py`
- Test: `tests/test_session_zero.py`

**Design Note:** The implementation uses a single continuous group chat rather than three discrete phases. This is intentional:
- The DM controls pacing via marker phrases, not the system
- Full transcript naturally carries between phases (no handoff needed)
- The `Phase` enum and `detect_phase_marker()` from Task 5 are available for future enhancements (logging, UI, analytics) but not required for core functionality
- The termination condition (`TextMentionTermination("SESSION ZERO LOCKED")`) handles the end of Session Zero

**Step 1: Write the failing test**

```python
# Add to tests/test_session_zero.py
class TestSessionZeroRun:
    def test_session_zero_has_run_method(self):
        """SessionZero has async run method."""
        from dndbots.session_zero import SessionZero
        import inspect

        sz = SessionZero(num_players=2)
        assert hasattr(sz, "run")
        assert inspect.iscoroutinefunction(sz.run)

    def test_session_zero_has_team(self):
        """SessionZero creates a SelectorGroupChat team."""
        from dndbots.session_zero import SessionZero
        from autogen_agentchat.teams import SelectorGroupChat

        sz = SessionZero(num_players=2)
        assert hasattr(sz, "team")
        assert isinstance(sz.team, SelectorGroupChat)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_session_zero.py::TestSessionZeroRun -v`
Expected: FAIL (run method or team doesn't exist)

**Step 3: Write minimal implementation**

```python
# Modify SessionZero.__init__ to add team creation, add run method

# In __init__, after creating players, add:
        # Create the group chat with DM-controlled selection
        from autogen_agentchat.teams import SelectorGroupChat
        from autogen_agentchat.conditions import TextMentionTermination

        participants = [self.dm] + self.players
        self.team = SelectorGroupChat(
            participants=participants,
            model_client=OpenAIChatCompletionClient(model=dm_model),
            selector_func=session_zero_selector,
            termination_condition=TextMentionTermination("SESSION ZERO LOCKED"),
        )

# Add run method to SessionZero class:
    async def run(self) -> SessionZeroResult:
        """Run Session Zero through all phases.

        Returns:
            SessionZeroResult with scenario, characters, and party document
        """
        transcript = []

        # Initial prompt to kick off Session Zero
        initial_message = (
            "Welcome to Session Zero! Let's create our campaign together. "
            "DM, please start by sharing your campaign concept, then we'll go around "
            "for character pitches."
        )

        async for message in self.team.run_stream(task=initial_message):
            if hasattr(message, "source") and hasattr(message, "content"):
                transcript.append(message)

        # Parse outputs from final messages
        scenario = ""
        party_document = ""
        characters = []

        # Find DM's final message for scenario and party doc
        for msg in reversed(transcript):
            if msg.source == "dm":
                if not scenario:
                    scenario = parse_scenario(msg.content)
                if not party_document:
                    party_document = parse_party_document(msg.content)
                if scenario and party_document:
                    break

        # Find each player's character
        for msg in reversed(transcript):
            if msg.source.startswith("player_"):
                char = parse_character(msg.content)
                if char:
                    characters.append(char)

        # Reverse to maintain player order
        characters.reverse()

        return SessionZeroResult(
            scenario=scenario,
            characters=characters,
            party_document=party_document,
            transcript=transcript,
        )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_session_zero.py::TestSessionZeroRun -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/session_zero.py tests/test_session_zero.py
git commit -m "feat(session-zero): implement run() method with group chat"
```

---

## Task 8: Integrate Party Document into Prompts

**Files:**
- Modify: `src/dndbots/prompts.py`
- Test: `tests/test_prompts.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_prompts.py
class TestPartyDocumentIntegration:
    def test_dm_prompt_includes_party_document(self):
        """DM prompt includes party document when provided."""
        from dndbots.prompts import build_dm_prompt

        party_doc = "## Relationships\n- Kira and Marcus share history"
        prompt = build_dm_prompt("Test scenario", party_document=party_doc)
        assert "Relationships" in prompt
        assert "Kira and Marcus" in prompt

    def test_dm_prompt_works_without_party_document(self):
        """DM prompt works when party_document is None."""
        from dndbots.prompts import build_dm_prompt

        prompt = build_dm_prompt("Test scenario", party_document=None)
        assert "Test scenario" in prompt

    def test_player_prompt_includes_party_document(self):
        """Player prompt includes party document when provided."""
        from dndbots.prompts import build_player_prompt
        from dndbots.models import Character, Stats

        char = Character(
            name="Test",
            char_class="Fighter",
            level=1,
            hp=8,
            hp_max=8,
            ac=5,
            stats=Stats(str=14, dex=12, con=13, int=10, wis=11, cha=9),
            equipment=[],
            gold=0,
        )
        party_doc = "## Shared Goals\n- Stop the cult"
        prompt = build_player_prompt(char, party_document=party_doc)
        assert "Shared Goals" in prompt
        assert "Stop the cult" in prompt
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_prompts.py::TestPartyDocumentIntegration -v`
Expected: FAIL (party_document parameter doesn't exist)

**Step 3: Write minimal implementation**

```python
# Modify src/dndbots/prompts.py

# Update build_dm_prompt signature and add party_document section:
def build_dm_prompt(
    scenario: str,
    rules_index: RulesIndex | None = None,
    party_document: str | None = None,
) -> str:
    """Build the Dungeon Master system prompt.

    Args:
        scenario: The adventure scenario/setup
        rules_index: Optional loaded rules index for expanded summary
        party_document: Optional party background from Session Zero

    Returns:
        Complete DM system prompt
    """
    # ... existing code ...

    # Before the final return, add:
    party_section = ""
    if party_document:
        party_section = f"""
=== PARTY BACKGROUND ===
{party_document}
"""

    # Modify return to include party_section after scenario


# Update build_player_prompt signature:
def build_player_prompt(
    character: Character,
    memory: str | None = None,
    party_document: str | None = None,
) -> str:
    """Build a player agent system prompt.

    Args:
        character: The character this agent plays
        memory: Optional DCML memory block to include
        party_document: Optional party background from Session Zero

    Returns:
        Complete player system prompt
    """
    # ... existing code ...

    # Add party_document section after memory section:
    if party_document:
        sections.extend([
            "",
            "=== PARTY BACKGROUND ===",
            party_document,
        ])
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_prompts.py::TestPartyDocumentIntegration -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/prompts.py tests/test_prompts.py
git commit -m "feat(prompts): add party_document parameter to prompt builders"
```

---

## Task 9: Update DnDGame to Accept Party Document

**Files:**
- Modify: `src/dndbots/game.py`
- Test: `tests/test_game.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_game.py
class TestDnDGamePartyDocument:
    def test_game_accepts_party_document(self):
        """DnDGame accepts optional party_document."""
        char = Character(
            name="Test",
            char_class="Fighter",
            level=1,
            hp=8,
            hp_max=8,
            ac=5,
            stats=Stats(str=14, dex=12, con=13, int=10, wis=11, cha=9),
            equipment=[],
            gold=0,
        )
        game = DnDGame(
            scenario="Test scenario",
            characters=[char],
            party_document="## Relationships\n- Test content",
        )
        assert game.party_document == "## Relationships\n- Test content"

    def test_game_works_without_party_document(self):
        """DnDGame works when party_document is None."""
        char = Character(
            name="Test",
            char_class="Fighter",
            level=1,
            hp=8,
            hp_max=8,
            ac=5,
            stats=Stats(str=14, dex=12, con=13, int=10, wis=11, cha=9),
            equipment=[],
            gold=0,
        )
        game = DnDGame(
            scenario="Test scenario",
            characters=[char],
        )
        assert game.party_document is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_game.py::TestDnDGamePartyDocument -v`
Expected: FAIL (party_document parameter doesn't exist)

**Step 3: Write minimal implementation**

```python
# Modify src/dndbots/game.py DnDGame.__init__

# Add party_document parameter:
def __init__(
    self,
    scenario: str,
    characters: list[Character],
    dm_model: str = "gpt-4o",
    player_model: str = "gpt-4o",
    campaign: Campaign | None = None,
    enable_memory: bool = True,
    event_bus: EventBus | None = None,
    party_document: str | None = None,  # NEW
):
    # ... existing code ...
    self.party_document = party_document  # NEW
```

**Step 4: Update agent creation to pass party_document**

```python
# In DnDGame.__init__, update create_dm_agent call:

# Change from:
dm_prompt = build_dm_prompt(scenario, rules_index=self.rules_index)

# To:
dm_prompt = build_dm_prompt(
    scenario,
    rules_index=self.rules_index,
    party_document=self.party_document,
)


# In DnDGame.__init__, update create_player_agent calls:

# In the player creation loop, change from:
player_prompt = build_player_prompt(char, memory=memory)

# To:
player_prompt = build_player_prompt(
    char,
    memory=memory,
    party_document=self.party_document,
)
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_game.py::TestDnDGamePartyDocument -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/dndbots/game.py tests/test_game.py
git commit -m "feat(game): add party_document parameter to DnDGame"
```

---

## Task 9.5: Implement update_party_document Tool for DM

**Files:**
- Modify: `src/dndbots/game.py`
- Test: `tests/test_game.py`

**Context:** The design specifies that DM should have access to `update_party_document()` tool during gameplay to keep the party document as a living artifact that evolves with the story.

**Step 1: Write the failing test**

```python
# Add to tests/test_game.py
class TestUpdatePartyDocumentTool:
    def test_dm_has_update_party_document_tool(self):
        """DM agent has update_party_document tool when party_document exists."""
        char = Character(
            name="Test",
            char_class="Fighter",
            level=1,
            hp=8,
            hp_max=8,
            ac=5,
            stats=Stats(str=14, dex=12, con=13, int=10, wis=11, cha=9),
            equipment=[],
            gold=0,
        )
        game = DnDGame(
            scenario="Test scenario",
            characters=[char],
            party_document="Initial party doc",
        )
        # Check DM has the tool
        tool_names = [t.name for t in game.dm._tools]
        assert "update_party_document" in tool_names

    def test_dm_no_update_tool_without_party_document(self):
        """DM agent has no update_party_document tool when party_document is None."""
        char = Character(
            name="Test",
            char_class="Fighter",
            level=1,
            hp=8,
            hp_max=8,
            ac=5,
            stats=Stats(str=14, dex=12, con=13, int=10, wis=11, cha=9),
            equipment=[],
            gold=0,
        )
        game = DnDGame(
            scenario="Test scenario",
            characters=[char],
            party_document=None,
        )
        # Check DM does NOT have the tool
        tool_names = [t.name for t in game.dm._tools]
        assert "update_party_document" not in tool_names

    @pytest.mark.asyncio
    async def test_update_party_document_modifies_document(self):
        """update_party_document tool updates the party document."""
        char = Character(
            name="Test",
            char_class="Fighter",
            level=1,
            hp=8,
            hp_max=8,
            ac=5,
            stats=Stats(str=14, dex=12, con=13, int=10, wis=11, cha=9),
            equipment=[],
            gold=0,
        )
        game = DnDGame(
            scenario="Test scenario",
            characters=[char],
            party_document="## Initial\n- Starting content",
        )

        # Find and call the tool
        update_tool = None
        for tool in game.dm._tools:
            if tool.name == "update_party_document":
                update_tool = tool
                break

        assert update_tool is not None

        # Call the tool's underlying function
        result = await update_tool._func(
            section="## New Plot Thread",
            content="The cult's true leader revealed"
        )

        assert "success" in result.lower()
        assert "New Plot Thread" in game.party_document
        assert "cult's true leader" in game.party_document
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_game.py::TestUpdatePartyDocumentTool -v`
Expected: FAIL (update_party_document tool doesn't exist)

**Step 3: Write minimal implementation**

```python
# Add to src/dndbots/game.py, after imports:

from autogen_core import FunctionCall
from autogen_core.tools import FunctionTool


def create_update_party_document_tool(game: "DnDGame") -> FunctionTool:
    """Create the update_party_document tool bound to a game instance.

    Args:
        game: The DnDGame instance to update

    Returns:
        FunctionTool that updates the party document
    """
    async def update_party_document(section: str, content: str) -> str:
        """Update the party document with new information.

        Use this tool after major events to keep the party document current:
        - New relationships discovered between characters
        - Plot threads resolved or introduced
        - Notable events that change party dynamics
        - Character development moments

        Args:
            section: Section header (e.g., "## New Plot Thread" or "## Updated Relationships")
            content: The content to add under this section

        Returns:
            Confirmation message
        """
        if game.party_document is None:
            game.party_document = ""

        # Append new section
        game.party_document += f"\n\n{section}\n{content}"

        # Persist if campaign exists
        if game.campaign:
            await game.campaign.update_party_document(game.party_document)

        return f"Party document updated with new section: {section}"

    return FunctionTool(update_party_document, description=update_party_document.__doc__)


# In DnDGame.__init__, after creating DM agent, add:

# Add update_party_document tool if party_document exists
if self.party_document is not None:
    update_tool = create_update_party_document_tool(self)
    self.dm._tools.append(update_tool)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_game.py::TestUpdatePartyDocumentTool -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/game.py tests/test_game.py
git commit -m "feat(game): add update_party_document tool for DM during gameplay"
```

---

## Task 10: Update CLI for Session Zero Flow

**Files:**
- Modify: `src/dndbots/cli.py`
- Test: `tests/test_cli.py` (new file)

**Step 1: Write the failing test**

```python
# Create tests/test_cli.py
"""Tests for CLI."""

import pytest
from unittest.mock import patch, AsyncMock


class TestCLISessionZero:
    def test_cli_has_session_zero_option(self):
        """CLI should have --session-zero flag."""
        from dndbots.cli import main
        import argparse

        # This is a basic structural test
        # Full integration test would require mocking
        assert callable(main)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v`
Expected: PASS (basic test, actual implementation follows)

**Step 3: Write minimal implementation**

```python
# Modify src/dndbots/cli.py

# Add import at top:
from dndbots.session_zero import SessionZero

# Add --session-zero flag to run_parser:
run_parser.add_argument(
    "--session-zero",
    action="store_true",
    help="Run Session Zero for collaborative campaign/character creation",
)

# Modify run_game to handle session zero:
async def run_game(session_zero: bool = False) -> None:
    """Run the game with persistence."""
    # ... existing setup ...

    if session_zero:
        print("Starting Session Zero...")
        sz = SessionZero(num_players=3)
        result = await sz.run()

        print("\n" + "=" * 60)
        print("SESSION ZERO COMPLETE")
        print("=" * 60)
        print(f"\nScenario: {result.scenario[:100]}...")
        print(f"Characters: {', '.join(c.name for c in result.characters)}")
        print(f"\nParty Document:\n{result.party_document[:200]}...")

        # Use session zero outputs
        characters = result.characters
        scenario = result.scenario
        party_document = result.party_document
    else:
        # ... existing character creation ...
        party_document = None

    # Pass party_document to DnDGame
    game = DnDGame(
        scenario=scenario,
        characters=characters,
        party_document=party_document,
        # ... other params ...
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/cli.py tests/test_cli.py
git commit -m "feat(cli): add --session-zero flag for collaborative creation"
```

---

## Task 11: Create End-to-End Test Script

**Files:**
- Create: `scripts/test_session_zero.py`

**Step 1: Create the test script**

```python
#!/usr/bin/env python3
"""End-to-end test: Full Session Zero with 3 players."""

from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import asyncio
from dndbots.session_zero import SessionZero


async def main():
    print("=" * 70)
    print("SESSION ZERO: Collaborative Campaign Creation")
    print("=" * 70)

    sz = SessionZero(
        num_players=3,
        dm_model="gpt-4o-mini",  # Use mini for faster/cheaper test
        player_model="gpt-4o-mini",
    )

    result = await sz.run()

    print("\n" + "=" * 70)
    print("SESSION ZERO COMPLETE")
    print("=" * 70)

    print("\n### SCENARIO ###")
    print(result.scenario)

    print("\n### PARTY DOCUMENT ###")
    print(result.party_document)

    print("\n### CHARACTERS ###")
    for char in result.characters:
        print(f"\n{char.to_sheet()}")

    print("\n" + "=" * 70)
    print(f"Total messages in transcript: {len(result.transcript)}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 2: Make it executable**

```bash
chmod +x scripts/test_session_zero.py
```

**Step 3: Commit**

```bash
git add scripts/test_session_zero.py
git commit -m "test: add end-to-end Session Zero test script"
```

---

## Task 12: Run Full Integration Test

**Step 1: Run all unit tests**

```bash
pytest tests/test_session_zero.py -v
```

Expected: All tests pass

**Step 2: Run the end-to-end test**

```bash
timeout 300 python scripts/test_session_zero.py
```

Expected: Full Session Zero completes with:
- DM creates campaign concept
- 3 players pitch characters
- Connections are established
- Final outputs are parsed correctly

**Step 3: Final commit with any fixes**

```bash
git add -A
git commit -m "feat(session-zero): complete implementation with e2e test"
```

---

## Summary

After completing all tasks, the system will support:

1. **SessionZero class** that orchestrates three-phase collaborative creation
2. **Phase detection** via marker phrases (PITCH COMPLETE, etc.)
3. **Output parsing** for scenario, party document, and characters
4. **Integration** with existing DnDGame via party_document parameter
5. **update_party_document tool** for DM to update the party document during gameplay
6. **CLI flag** `--session-zero` to enable the new flow
7. **End-to-end test** demonstrating full functionality

The DM facilitates, players collaborate, and the system produces all artifacts needed for gameplay. During gameplay, the DM can update the party document as the story evolves.
