# Phase 1: Minimal Viable Game Loop

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Get a basic D&D game loop running with one DM and one player agent, console output only, no persistence.

**Architecture:** AutoGen 0.4 SelectorGroupChat with custom selector function for DM control. Hardcoded character sheet. In-memory state only. This is the "walking skeleton" - prove the orchestration works before adding complexity.

**Tech Stack:** Python 3.11+, autogen-agentchat 0.4, autogen-ext (OpenAI client), python-dotenv

**Phases Overview:**
- **Phase 1** (this doc): Minimal game loop - DM + 1 player, console output, no persistence
- Phase 2: Persistence layer - SQLite + Neo4j, event logging
- Phase 3: Multi-provider - Multiple players, character creation
- Phase 4: Compression - StoryShorthand, RulesShorthand
- Phase 5: Output layer - Discord, event bus
- Phase 6: Admin - Web UI, graceful shutdown

---

## Task 1: Project Structure

**Files:**
- Create: `pyproject.toml`
- Create: `src/dndbots/__init__.py`
- Create: `src/dndbots/py.typed`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

**Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "dndbots"
version = "0.1.0"
description = "Multi-AI D&D campaign system"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "autogen-agentchat>=0.4.0",
    "autogen-ext[openai]>=0.4.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "ruff>=0.8.0",
]

[tool.hatch.build.targets.wheel]
packages = ["src/dndbots"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
line-length = 100
target-version = "py311"
```

**Step 2: Create package structure**

```bash
mkdir -p src/dndbots tests
touch src/dndbots/__init__.py
touch src/dndbots/py.typed
touch tests/__init__.py
```

**Step 3: Create tests/conftest.py**

```python
"""Shared pytest fixtures."""

import pytest


@pytest.fixture
def sample_character() -> dict:
    """A basic fighter character for testing."""
    return {
        "name": "Throk",
        "class": "Fighter",
        "level": 1,
        "hp": 8,
        "hp_max": 8,
        "ac": 5,  # Chain mail + shield in Basic D&D
        "stats": {"str": 16, "dex": 12, "con": 14, "int": 9, "wis": 10, "cha": 11},
        "equipment": ["longsword", "chain mail", "shield", "backpack", "torch x3"],
        "gold": 25,
    }
```

**Step 4: Create virtual environment and install**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Expected: Installation completes without errors.

**Step 5: Verify installation**

```bash
python -c "import autogen_agentchat; print(autogen_agentchat.__version__)"
```

Expected: Prints version number (0.4.x)

**Step 6: Commit**

```bash
git add pyproject.toml src/ tests/
git commit -m "chore: project structure with AutoGen 0.4 deps"
```

---

## Task 2: Dice Rolling Utility

**Files:**
- Create: `src/dndbots/dice.py`
- Create: `tests/test_dice.py`

**Step 1: Write the failing test**

```python
"""Tests for dice rolling utilities."""

import re

from dndbots.dice import roll, parse_roll


class TestRoll:
    def test_roll_d20_returns_int_in_range(self):
        for _ in range(100):
            result = roll(1, 20)
            assert 1 <= result <= 20

    def test_roll_2d6_returns_sum_in_range(self):
        for _ in range(100):
            result = roll(2, 6)
            assert 2 <= result <= 12

    def test_roll_with_modifier(self):
        for _ in range(100):
            result = roll(1, 20, modifier=5)
            assert 6 <= result <= 25


class TestParseRoll:
    def test_parse_d20(self):
        result = parse_roll("d20")
        assert result["dice"] == 1
        assert result["sides"] == 20
        assert result["modifier"] == 0

    def test_parse_2d6(self):
        result = parse_roll("2d6")
        assert result["dice"] == 2
        assert result["sides"] == 6
        assert result["modifier"] == 0

    def test_parse_d20_plus_5(self):
        result = parse_roll("d20+5")
        assert result["dice"] == 1
        assert result["sides"] == 20
        assert result["modifier"] == 5

    def test_parse_3d6_minus_2(self):
        result = parse_roll("3d6-2")
        assert result["dice"] == 3
        assert result["sides"] == 6
        assert result["modifier"] == -2
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_dice.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'dndbots.dice'`

**Step 3: Write minimal implementation**

```python
"""Dice rolling utilities for D&D mechanics."""

import random
import re
from typing import TypedDict


class ParsedRoll(TypedDict):
    dice: int
    sides: int
    modifier: int


def roll(dice: int, sides: int, modifier: int = 0) -> int:
    """Roll dice and return total with modifier.

    Args:
        dice: Number of dice to roll
        sides: Number of sides per die
        modifier: Flat modifier to add to result

    Returns:
        Total of all dice plus modifier
    """
    total = sum(random.randint(1, sides) for _ in range(dice))
    return total + modifier


def parse_roll(notation: str) -> ParsedRoll:
    """Parse dice notation like '2d6+3' into components.

    Args:
        notation: Dice notation string (e.g., 'd20', '2d6', '3d6+2', 'd20-1')

    Returns:
        Dict with dice count, sides, and modifier

    Raises:
        ValueError: If notation is invalid
    """
    pattern = r"^(\d*)d(\d+)([+-]\d+)?$"
    match = re.match(pattern, notation.lower().replace(" ", ""))

    if not match:
        raise ValueError(f"Invalid dice notation: {notation}")

    dice_str, sides_str, mod_str = match.groups()

    return ParsedRoll(
        dice=int(dice_str) if dice_str else 1,
        sides=int(sides_str),
        modifier=int(mod_str) if mod_str else 0,
    )
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_dice.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/dndbots/dice.py tests/test_dice.py
git commit -m "feat: dice rolling utility with notation parser"
```

---

## Task 3: Character Sheet Model

**Files:**
- Create: `src/dndbots/models.py`
- Create: `tests/test_models.py`

**Step 1: Write the failing test**

```python
"""Tests for game data models."""

import pytest

from dndbots.models import Character, Stats


class TestStats:
    def test_modifier_for_high_stat(self):
        stats = Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11)
        assert stats.modifier("str") == 2  # 16 = +2 in Basic D&D

    def test_modifier_for_average_stat(self):
        stats = Stats(str=10, dex=10, con=10, int=10, wis=10, cha=10)
        assert stats.modifier("str") == 0

    def test_modifier_for_low_stat(self):
        stats = Stats(str=6, dex=10, con=10, int=10, wis=10, cha=10)
        assert stats.modifier("str") == -1


class TestCharacter:
    def test_character_creation(self):
        char = Character(
            name="Throk",
            char_class="Fighter",
            level=1,
            hp=8,
            hp_max=8,
            ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=["longsword", "chain mail"],
            gold=25,
        )
        assert char.name == "Throk"
        assert char.is_alive

    def test_character_take_damage(self):
        char = Character(
            name="Throk",
            char_class="Fighter",
            level=1,
            hp=8,
            hp_max=8,
            ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=[],
            gold=0,
        )
        char.take_damage(5)
        assert char.hp == 3
        assert char.is_alive

    def test_character_dies_at_zero_hp(self):
        char = Character(
            name="Throk",
            char_class="Fighter",
            level=1,
            hp=8,
            hp_max=8,
            ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=[],
            gold=0,
        )
        char.take_damage(10)
        assert char.hp == 0
        assert not char.is_alive

    def test_character_sheet_string(self):
        char = Character(
            name="Throk",
            char_class="Fighter",
            level=1,
            hp=8,
            hp_max=8,
            ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=["longsword"],
            gold=25,
        )
        sheet = char.to_sheet()
        assert "Throk" in sheet
        assert "Fighter" in sheet
        assert "HP: 8/8" in sheet
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_models.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'dndbots.models'`

**Step 3: Write minimal implementation**

```python
"""Game data models for D&D characters and state."""

from dataclasses import dataclass, field


@dataclass
class Stats:
    """Character ability scores (Basic D&D)."""

    str: int
    dex: int
    con: int
    int: int
    wis: int
    cha: int

    def modifier(self, stat: str) -> int:
        """Get modifier for a stat (Basic D&D table).

        Basic D&D modifiers:
        3: -3, 4-5: -2, 6-8: -1, 9-12: 0, 13-15: +1, 16-17: +2, 18: +3
        """
        value = getattr(self, stat)
        if value <= 3:
            return -3
        elif value <= 5:
            return -2
        elif value <= 8:
            return -1
        elif value <= 12:
            return 0
        elif value <= 15:
            return 1
        elif value <= 17:
            return 2
        else:
            return 3


@dataclass
class Character:
    """A player character or NPC."""

    name: str
    char_class: str
    level: int
    hp: int
    hp_max: int
    ac: int
    stats: Stats
    equipment: list[str] = field(default_factory=list)
    gold: int = 0

    @property
    def is_alive(self) -> bool:
        """Character is alive if HP > 0."""
        return self.hp > 0

    def take_damage(self, amount: int) -> None:
        """Apply damage to character. HP cannot go below 0."""
        self.hp = max(0, self.hp - amount)

    def heal(self, amount: int) -> None:
        """Heal character. HP cannot exceed max."""
        self.hp = min(self.hp_max, self.hp + amount)

    def to_sheet(self) -> str:
        """Generate a compact character sheet string for context."""
        equipment_str = ", ".join(self.equipment) if self.equipment else "none"
        return f"""=== {self.name} ===
Class: {self.char_class} | Level: {self.level}
HP: {self.hp}/{self.hp_max} | AC: {self.ac}
STR: {self.stats.str} ({self.stats.modifier('str'):+d}) | DEX: {self.stats.dex} ({self.stats.modifier('dex'):+d}) | CON: {self.stats.con} ({self.stats.modifier('con'):+d})
INT: {self.stats.int} ({self.stats.modifier('int'):+d}) | WIS: {self.stats.wis} ({self.stats.modifier('wis'):+d}) | CHA: {self.stats.cha} ({self.stats.modifier('cha'):+d})
Equipment: {equipment_str}
Gold: {self.gold}gp"""
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_models.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/dndbots/models.py tests/test_models.py
git commit -m "feat: Character and Stats models with Basic D&D modifiers"
```

---

## Task 4: Basic D&D Rules Reference

**Files:**
- Create: `src/dndbots/rules.py`
- Create: `tests/test_rules.py`

**Step 1: Write the failing test**

```python
"""Tests for rules reference."""

from dndbots.rules import RULES_SHORTHAND, get_thac0, check_hit


class TestThac0:
    def test_fighter_level_1_thac0(self):
        assert get_thac0("Fighter", 1) == 19

    def test_fighter_level_3_thac0(self):
        assert get_thac0("Fighter", 3) == 19  # Improves at 4

    def test_thief_level_1_thac0(self):
        assert get_thac0("Thief", 1) == 19

    def test_cleric_level_1_thac0(self):
        assert get_thac0("Cleric", 1) == 19

    def test_wizard_level_1_thac0(self):
        assert get_thac0("Magic-User", 1) == 19


class TestCheckHit:
    def test_hit_succeeds_when_roll_meets_target(self):
        # THAC0 19, AC 5 -> need 14 to hit
        assert check_hit(roll=14, thac0=19, target_ac=5) is True

    def test_hit_fails_when_roll_too_low(self):
        assert check_hit(roll=13, thac0=19, target_ac=5) is False

    def test_natural_20_always_hits(self):
        assert check_hit(roll=20, thac0=19, target_ac=-5) is True

    def test_natural_1_always_misses(self):
        assert check_hit(roll=1, thac0=10, target_ac=9) is False


class TestRulesShorthand:
    def test_rules_shorthand_exists(self):
        assert len(RULES_SHORTHAND) > 100  # Should be substantial
        assert "COMBAT" in RULES_SHORTHAND
        assert "THAC0" in RULES_SHORTHAND
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_rules.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'dndbots.rules'`

**Step 3: Write minimal implementation**

```python
"""Basic D&D rules reference and utilities."""

# THAC0 tables for Basic D&D (levels 1-3 for now)
THAC0_TABLE: dict[str, dict[int, int]] = {
    "Fighter": {1: 19, 2: 19, 3: 19, 4: 17, 5: 17, 6: 17},
    "Cleric": {1: 19, 2: 19, 3: 19, 4: 19, 5: 17, 6: 17},
    "Thief": {1: 19, 2: 19, 3: 19, 4: 19, 5: 17, 6: 17},
    "Magic-User": {1: 19, 2: 19, 3: 19, 4: 19, 5: 19, 6: 17},
}


def get_thac0(char_class: str, level: int) -> int:
    """Get THAC0 for a character class and level.

    THAC0 = 'To Hit Armor Class 0'. Lower is better.
    Roll d20 >= (THAC0 - target_AC) to hit.
    """
    class_table = THAC0_TABLE.get(char_class, THAC0_TABLE["Fighter"])
    # Clamp level to table range
    clamped_level = min(level, max(class_table.keys()))
    return class_table.get(clamped_level, 19)


def check_hit(roll: int, thac0: int, target_ac: int) -> bool:
    """Check if an attack roll hits.

    Args:
        roll: The d20 roll result (before modifiers)
        thac0: Attacker's THAC0
        target_ac: Defender's Armor Class

    Returns:
        True if the attack hits
    """
    # Natural 1 always misses, natural 20 always hits
    if roll == 1:
        return False
    if roll == 20:
        return True

    # Need to roll >= (THAC0 - AC) to hit
    target_number = thac0 - target_ac
    return roll >= target_number


# Compressed rules for system prompts
RULES_SHORTHAND = """
=== BASIC D&D RULES (Red Box) ===

COMBAT:
• Initiative: d6 per side, high acts first
• Attack: d20 >= (THAC0 - target_AC) = hit
• THAC0: Starts at 19 for all classes (lower is better)
• Natural 20: Always hits | Natural 1: Always misses
• Damage: Weapon die + STR modifier

ARMOR CLASS (lower is better):
• Unarmored: AC 9
• Leather: AC 7
• Chain: AC 5
• Plate: AC 3
• Shield: -1 AC

SAVING THROWS (d20 >= target):
• Death/Poison, Wands, Paralysis/Stone, Dragon Breath, Spells
• Fighter L1: 12/13/14/15/16
• Cleric L1: 11/12/14/16/15
• Thief L1: 13/14/13/16/15
• Magic-User L1: 13/14/13/16/15

ABILITY MODIFIERS:
• 3: -3 | 4-5: -2 | 6-8: -1 | 9-12: 0 | 13-15: +1 | 16-17: +2 | 18: +3

HEALING:
• Rest: 1d3 HP per full day of rest
• Clerical healing: Cure Light Wounds = 1d6+1 HP

DEATH:
• 0 HP = dead (Basic D&D has no death saves)
"""
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_rules.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/dndbots/rules.py tests/test_rules.py
git commit -m "feat: Basic D&D rules reference with THAC0 and combat"
```

---

## Task 5: Agent Prompts

**Files:**
- Create: `src/dndbots/prompts.py`
- Create: `tests/test_prompts.py`

**Step 1: Write the failing test**

```python
"""Tests for agent prompt generation."""

from dndbots.prompts import build_dm_prompt, build_player_prompt
from dndbots.models import Character, Stats


class TestDMPrompt:
    def test_dm_prompt_contains_rules(self):
        prompt = build_dm_prompt(scenario="A goblin cave adventure")
        assert "THAC0" in prompt
        assert "COMBAT" in prompt

    def test_dm_prompt_contains_scenario(self):
        prompt = build_dm_prompt(scenario="A goblin cave adventure")
        assert "goblin cave" in prompt

    def test_dm_prompt_contains_dm_guidance(self):
        prompt = build_dm_prompt(scenario="test")
        assert "Dungeon Master" in prompt


class TestPlayerPrompt:
    def test_player_prompt_contains_character_sheet(self):
        char = Character(
            name="Throk",
            char_class="Fighter",
            level=1,
            hp=8,
            hp_max=8,
            ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=["longsword"],
            gold=25,
        )
        prompt = build_player_prompt(char)
        assert "Throk" in prompt
        assert "Fighter" in prompt
        assert "HP: 8/8" in prompt

    def test_player_prompt_contains_player_guidance(self):
        char = Character(
            name="Test",
            char_class="Fighter",
            level=1,
            hp=8,
            hp_max=8,
            ac=5,
            stats=Stats(str=10, dex=10, con=10, int=10, wis=10, cha=10),
            equipment=[],
            gold=0,
        )
        prompt = build_player_prompt(char)
        assert "roleplay" in prompt.lower() or "character" in prompt.lower()
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_prompts.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'dndbots.prompts'`

**Step 3: Write minimal implementation**

```python
"""Agent prompt builders for DM and players."""

from dndbots.models import Character
from dndbots.rules import RULES_SHORTHAND


def build_dm_prompt(scenario: str) -> str:
    """Build the Dungeon Master system prompt.

    Args:
        scenario: The adventure scenario/setup

    Returns:
        Complete DM system prompt
    """
    return f"""You are the Dungeon Master for a Basic D&D (1983 Red Box) campaign.

{RULES_SHORTHAND}

=== YOUR SCENARIO ===
{scenario}

=== DM GUIDELINES ===
• Describe scenes vividly but concisely
• Ask players what they want to do, don't assume actions
• Roll dice transparently - announce what you're rolling and why
• When a player attacks: announce their roll, calculate hit/miss, roll damage if hit
• Keep combat exciting with descriptions of hits and misses
• Be fair but challenging - Basic D&D is lethal
• Track monster HP and announce when enemies are wounded or defeated

=== TURN CONTROL ===
After describing a scene or resolving an action, explicitly address the next player.
Example: "Throk, the goblin snarls at you. What do you do?"

When you need to end the session or pause, say "SESSION PAUSE" clearly.
"""


def build_player_prompt(character: Character) -> str:
    """Build a player agent system prompt.

    Args:
        character: The character this agent plays

    Returns:
        Complete player system prompt
    """
    return f"""You are playing {character.name} in a Basic D&D campaign.

=== YOUR CHARACTER ===
{character.to_sheet()}

=== PLAYER GUIDELINES ===
• Stay in character - respond as {character.name} would
• Describe your actions clearly: "I attack the goblin with my sword"
• You can ask the DM questions: "How far away is the door?"
• Declare dice rolls you want to make: "I want to search for traps"
• Roleplay conversations with NPCs and other players
• Your character has their own personality, goals, and fears

=== PARTY PLAY ===
• "I defer to [other player]" or "I watch and wait" are VALID actions
• Only act if you have something valuable to add
• If another character is better suited for a task, let them shine
• Stepping back IS good roleplay

=== COMBAT ===
• On your turn, declare your action: attack, cast spell, use item, flee, etc.
• The DM will roll dice and describe results
• Keep track of your HP - you can ask the DM your current status

When the DM addresses you directly, respond in character.
"""
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_prompts.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/dndbots/prompts.py tests/test_prompts.py
git commit -m "feat: DM and player prompt builders"
```

---

## Task 6: Game Loop with AutoGen

**Files:**
- Create: `src/dndbots/game.py`
- Create: `tests/test_game.py`
- Create: `.env.example`

**Step 1: Write the failing test**

```python
"""Tests for game loop."""

import pytest

from dndbots.game import create_dm_agent, create_player_agent, DnDGame
from dndbots.models import Character, Stats


class TestAgentCreation:
    def test_create_dm_agent(self):
        agent = create_dm_agent(
            scenario="Test scenario",
            model="gpt-4o-mini",  # Use mini for tests
        )
        assert agent.name == "dm"

    def test_create_player_agent(self):
        char = Character(
            name="Throk",
            char_class="Fighter",
            level=1,
            hp=8,
            hp_max=8,
            ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=["longsword"],
            gold=25,
        )
        agent = create_player_agent(
            character=char,
            model="gpt-4o-mini",
        )
        assert agent.name == "Throk"


class TestDnDGame:
    def test_game_initialization(self):
        char = Character(
            name="Throk",
            char_class="Fighter",
            level=1,
            hp=8,
            hp_max=8,
            ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=["longsword"],
            gold=25,
        )
        game = DnDGame(
            scenario="A goblin cave",
            characters=[char],
            dm_model="gpt-4o-mini",
            player_model="gpt-4o-mini",
        )
        assert game.dm is not None
        assert len(game.players) == 1
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_game.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'dndbots.game'`

**Step 3: Write minimal implementation**

```python
"""Game loop orchestration using AutoGen 0.4."""

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_ext.models.openai import OpenAIChatCompletionClient

from dndbots.models import Character
from dndbots.prompts import build_dm_prompt, build_player_prompt


def create_dm_agent(
    scenario: str,
    model: str = "gpt-4o",
) -> AssistantAgent:
    """Create the Dungeon Master agent.

    Args:
        scenario: The adventure scenario
        model: OpenAI model to use

    Returns:
        Configured DM agent
    """
    model_client = OpenAIChatCompletionClient(model=model)

    return AssistantAgent(
        name="dm",
        model_client=model_client,
        system_message=build_dm_prompt(scenario),
    )


def create_player_agent(
    character: Character,
    model: str = "gpt-4o",
) -> AssistantAgent:
    """Create a player agent for a character.

    Args:
        character: The character to play
        model: OpenAI model to use

    Returns:
        Configured player agent
    """
    model_client = OpenAIChatCompletionClient(model=model)

    return AssistantAgent(
        name=character.name,
        model_client=model_client,
        system_message=build_player_prompt(character),
    )


def dm_selector(messages) -> str | None:
    """Custom selector: DM controls turn order.

    After any player speaks, return to DM.
    DM decides who goes next by addressing them.
    """
    if not messages:
        return "dm"

    last_speaker = messages[-1].source

    # After player speaks, always return to DM
    if last_speaker != "dm":
        return "dm"

    # DM just spoke - let the model selector figure out who was addressed
    return None


class DnDGame:
    """Orchestrates a D&D game session."""

    def __init__(
        self,
        scenario: str,
        characters: list[Character],
        dm_model: str = "gpt-4o",
        player_model: str = "gpt-4o",
    ):
        """Initialize a game session.

        Args:
            scenario: The adventure scenario
            characters: List of player characters
            dm_model: Model for DM agent
            player_model: Model for player agents
        """
        self.scenario = scenario
        self.characters = characters

        # Create agents
        self.dm = create_dm_agent(scenario, dm_model)
        self.players = [
            create_player_agent(char, player_model)
            for char in characters
        ]

        # Build participant list (DM first)
        participants = [self.dm] + self.players

        # Create the group chat with DM-controlled selection
        self.team = SelectorGroupChat(
            participants=participants,
            model_client=OpenAIChatCompletionClient(model=dm_model),
            selector_func=dm_selector,
            termination_condition=TextMentionTermination("SESSION PAUSE"),
        )

    async def run(self, max_turns: int = 20) -> None:
        """Run the game session.

        Args:
            max_turns: Maximum turns before auto-pause
        """
        # Start with DM setting the scene
        initial_message = (
            f"Begin the adventure. Set the scene for the party: "
            f"{', '.join(c.name for c in self.characters)}. "
            f"Describe where they are and what they see."
        )

        async for message in self.team.run_stream(task=initial_message):
            # Print each message as it comes
            if hasattr(message, 'source') and hasattr(message, 'content'):
                print(f"\n[{message.source}]: {message.content}")
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_game.py -v
```

Expected: All tests PASS

**Step 5: Create .env.example**

```bash
# .env.example - Copy to .env and fill in your API keys
OPENAI_API_KEY=sk-your-openai-key-here
```

**Step 6: Commit**

```bash
git add src/dndbots/game.py tests/test_game.py .env.example
git commit -m "feat: game loop with AutoGen SelectorGroupChat"
```

---

## Task 7: CLI Entry Point

**Files:**
- Create: `src/dndbots/cli.py`
- Modify: `pyproject.toml` (add script entry point)

**Step 1: Create CLI module**

```python
"""Command-line interface for running DnDBots."""

import asyncio
import os

from dotenv import load_dotenv

from dndbots.game import DnDGame
from dndbots.models import Character, Stats


# Default test scenario
DEFAULT_SCENARIO = """
The party stands at the entrance to the Caves of Chaos - a dark opening
in the hillside that locals say is home to goblins and worse.

The village of Millbrook has offered 50 gold pieces for clearing out
the goblin threat. Merchants have been attacked on the road, and
three villagers went missing last week.

Inside the cave entrance, you can see crude torches flickering in
wall sconces, and you hear guttural voices echoing from deeper within.

Start by describing the scene and asking the party what they want to do.
"""


def create_default_character() -> Character:
    """Create a default fighter character for testing."""
    return Character(
        name="Throk",
        char_class="Fighter",
        level=1,
        hp=8,
        hp_max=8,
        ac=5,
        stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
        equipment=["longsword", "chain mail", "shield", "backpack", "torch x3", "rope 50ft"],
        gold=25,
    )


def main() -> None:
    """Run a test game session."""
    # Load environment variables
    load_dotenv()

    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not set. Copy .env.example to .env and add your key.")
        return

    print("=" * 60)
    print("DnDBots - Basic D&D AI Campaign")
    print("=" * 60)
    print("\nStarting test session with 1 player (Throk the Fighter)")
    print("Type Ctrl+C to stop\n")

    # Create game
    character = create_default_character()
    game = DnDGame(
        scenario=DEFAULT_SCENARIO,
        characters=[character],
        dm_model="gpt-4o",
        player_model="gpt-4o",
    )

    # Run the game
    try:
        asyncio.run(game.run(max_turns=20))
    except KeyboardInterrupt:
        print("\n\n[System] Session interrupted by user.")

    print("\n" + "=" * 60)
    print("Session ended")
    print("=" * 60)


if __name__ == "__main__":
    main()
```

**Step 2: Add script entry point to pyproject.toml**

Add this section to `pyproject.toml`:

```toml
[project.scripts]
dndbots = "dndbots.cli:main"
```

**Step 3: Reinstall to get CLI command**

```bash
pip install -e ".[dev]"
```

**Step 4: Verify CLI is available**

```bash
dndbots --help || python -m dndbots.cli
```

Expected: Either shows help or runs (and fails with missing API key message)

**Step 5: Commit**

```bash
git add src/dndbots/cli.py pyproject.toml
git commit -m "feat: CLI entry point for running game sessions"
```

---

## Task 8: Integration Test (Manual)

**Files:**
- Create: `.env` (from `.env.example`, with real API key)

**Step 1: Set up real API key**

```bash
cp .env.example .env
# Edit .env and add your real OPENAI_API_KEY
```

**Step 2: Run the game**

```bash
dndbots
```

Expected:
- DM describes the cave entrance
- Addresses Throk
- Throk responds in character
- DM responds to Throk's action
- Continues for several turns or until "SESSION PAUSE"

**Step 3: Verify conversation flow**

Watch for:
- DM sets scene appropriately
- Throk responds in character as a fighter
- DM adjudicates actions and rolls dice
- Turn order follows DM -> Player -> DM pattern

**Step 4: Document any issues**

If issues found, note them for Phase 2 planning.

**Step 5: Final commit**

```bash
git add -A
git commit -m "chore: phase 1 complete - minimal game loop working"
```

---

## Phase 1 Complete Checklist

- [ ] Project structure with AutoGen 0.4 deps
- [ ] Dice rolling utility
- [ ] Character/Stats models
- [ ] Basic D&D rules reference
- [ ] DM and player prompts
- [ ] Game loop with SelectorGroupChat
- [ ] CLI entry point
- [ ] Manual integration test passed

## Next Phase Preview

**Phase 2: Persistence Layer** will add:
- SQLite for event logging and character persistence
- Neo4j for relationship tracking
- Save/load game state
- Event history in context

---

**End of Phase 1 Plan**
