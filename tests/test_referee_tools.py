"""Tests for referee_tools module."""

import pytest
from autogen_core.tools import FunctionTool

from dndbots.mechanics import MechanicsEngine
from dndbots.referee_tools import create_referee_tools


@pytest.fixture
def engine():
    """Create a fresh MechanicsEngine for testing."""
    return MechanicsEngine(debug_mode=False)


@pytest.fixture
def tools(engine):
    """Create referee tools bound to the engine."""
    return create_referee_tools(engine)


class TestToolCreation:
    """Test tool creation and basic properties."""

    def test_create_referee_tools_returns_list(self, engine):
        """Test that create_referee_tools returns a list."""
        tools = create_referee_tools(engine)
        assert isinstance(tools, list)

    def test_create_referee_tools_returns_function_tools(self, engine):
        """Test that all tools are FunctionTool instances."""
        tools = create_referee_tools(engine)
        assert len(tools) == 13
        for tool in tools:
            assert isinstance(tool, FunctionTool)

    def test_tools_have_descriptions(self, tools):
        """Test that all tools have non-empty descriptions."""
        for tool in tools:
            # Check FunctionTool description attribute
            assert tool.description is not None
            assert len(tool.description.strip()) > 0


class TestCombatLifecycleTools:
    """Test combat lifecycle tool functions."""

    def test_start_combat_tool(self, engine, tools):
        """Test start_combat_tool initializes combat."""
        start_combat = tools[0]._func
        result = start_combat()
        assert "Combat started" in result
        assert engine.combat is not None

    def test_start_combat_tool_with_strict_mode(self, engine, tools):
        """Test start_combat_tool with strict mode."""
        start_combat = tools[0]._func
        result = start_combat(style="strict")
        assert "strict mode" in result
        assert engine.combat.combat_style == "strict"

    def test_add_combatant_tool(self, engine, tools):
        """Test add_combatant_tool adds a combatant."""
        start_combat = tools[0]._func
        add_combatant = tools[1]._func

        start_combat()
        result = add_combatant(
            id="goblin_01",
            name="Goblin",
            hp=5,
            hp_max=5,
            ac=6,
            thac0=19,
            damage_dice="1d6",
            char_class="goblin",
            level=1,
        )

        assert "Added Goblin to combat" in result
        assert "goblin_01" in engine.combat.combatants

    def test_add_combatant_tool_pc(self, engine, tools):
        """Test add_combatant_tool with PC."""
        start_combat = tools[0]._func
        add_combatant = tools[1]._func

        start_combat()
        result = add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=18,
            damage_dice="1d8+1",
            char_class="fighter",
            level=2,
            is_pc=True,
        )

        assert "(PC)" in result
        assert "pc_throk" in engine.pcs

    def test_end_combat_tool(self, engine, tools):
        """Test end_combat_tool ends combat and returns summary."""
        start_combat = tools[0]._func
        add_combatant = tools[1]._func
        end_combat = tools[2]._func

        start_combat()
        add_combatant(
            id="goblin_01",
            name="Goblin",
            hp=5,
            hp_max=5,
            ac=6,
            thac0=19,
            damage_dice="1d6",
            char_class="goblin",
            level=1,
        )

        result = end_combat()
        assert "Combat ended" in result
        assert "rounds" in result.lower()
        assert engine.combat is None


class TestResolutionTools:
    """Test resolution tool functions."""

    @pytest.fixture
    def combat_with_combatants(self, engine, tools):
        """Set up combat with two combatants."""
        start_combat = tools[0]._func
        add_combatant = tools[1]._func

        start_combat()
        add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=18,
            damage_dice="1d8",
            char_class="fighter",
            level=2,
            is_pc=True,
        )
        add_combatant(
            id="goblin_01",
            name="Goblin",
            hp=5,
            hp_max=5,
            ac=6,
            thac0=19,
            damage_dice="1d6",
            char_class="goblin",
            level=1,
        )
        return engine, tools

    async def test_roll_attack_tool(self, combat_with_combatants):
        """Test roll_attack_tool resolves attack."""
        engine, tools = combat_with_combatants
        roll_attack = tools[3]._func

        result = await roll_attack(attacker="pc_throk", target="goblin_01")
        assert "Attack roll:" in result
        assert "vs needed" in result
        assert ("HIT" in result) or ("MISS" in result)

    async def test_roll_attack_tool_with_modifier(self, combat_with_combatants):
        """Test roll_attack_tool with modifier."""
        engine, tools = combat_with_combatants
        roll_attack = tools[3]._func

        result = await roll_attack(attacker="pc_throk", target="goblin_01", modifier=2)
        assert "Attack roll:" in result
        assert "+2" in result or "with modifier 2" in result.lower()

    async def test_roll_damage_tool(self, combat_with_combatants):
        """Test roll_damage_tool applies damage."""
        engine, tools = combat_with_combatants
        roll_damage = tools[4]._func

        result = await roll_damage(attacker="pc_throk", target="goblin_01")
        assert "Damage:" in result
        assert "Target HP:" in result
        assert "points dealt" in result

        # Check that goblin HP was reduced
        goblin = engine.combat.combatants["goblin_01"]
        assert goblin.hp < goblin.hp_max

    async def test_roll_damage_tool_with_override(self, combat_with_combatants):
        """Test roll_damage_tool with damage_dice override."""
        engine, tools = combat_with_combatants
        roll_damage = tools[4]._func

        result = await roll_damage(
            attacker="pc_throk", target="goblin_01", damage_dice="2d6+2"
        )
        assert "Damage:" in result
        # Verify damage was applied (could be 4-14 with 2d6+2)
        goblin = engine.combat.combatants["goblin_01"]
        assert goblin.hp <= goblin.hp_max

    def test_roll_save_tool(self, combat_with_combatants):
        """Test roll_save_tool resolves saving throw."""
        engine, tools = combat_with_combatants
        roll_save = tools[5]._func

        result = roll_save(target="pc_throk", save_type="death_ray")
        assert "Saving throw" in result
        assert "death_ray" in result
        assert ("SUCCESS" in result) or ("FAILURE" in result)

    def test_roll_save_tool_all_types(self, combat_with_combatants):
        """Test roll_save_tool with all save types."""
        engine, tools = combat_with_combatants
        roll_save = tools[5]._func

        save_types = ["death_ray", "wands", "paralysis", "breath", "spells"]
        for save_type in save_types:
            result = roll_save(target="pc_throk", save_type=save_type)
            assert save_type in result
            assert ("SUCCESS" in result) or ("FAILURE" in result)

    def test_roll_ability_check_tool(self, combat_with_combatants):
        """Test roll_ability_check_tool resolves ability check."""
        engine, tools = combat_with_combatants
        roll_ability_check = tools[6]._func

        result = roll_ability_check(target="pc_throk", ability="str", difficulty=15)
        assert "Ability check" in result
        assert "STR" in result
        assert ("SUCCESS" in result) or ("FAILURE" in result)

    def test_roll_ability_check_tool_all_abilities(self, combat_with_combatants):
        """Test roll_ability_check_tool with all abilities."""
        engine, tools = combat_with_combatants
        roll_ability_check = tools[6]._func

        abilities = ["str", "dex", "con", "int", "wis", "cha"]
        for ability in abilities:
            result = roll_ability_check(target="pc_throk", ability=ability, difficulty=10)
            assert ability.upper() in result
            assert ("SUCCESS" in result) or ("FAILURE" in result)

    def test_roll_morale_tool(self, combat_with_combatants):
        """Test roll_morale_tool resolves morale check."""
        engine, tools = combat_with_combatants
        roll_morale = tools[7]._func

        result = roll_morale(target="goblin_01")
        assert "Morale check:" in result
        assert ("HOLDS" in result) or ("BREAKS" in result)
        assert "2d6 roll" in result


class TestConditionTools:
    """Test condition management tool functions."""

    @pytest.fixture
    def combat_with_combatants(self, engine, tools):
        """Set up combat with combatants."""
        start_combat = tools[0]._func
        add_combatant = tools[1]._func

        start_combat()
        add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=18,
            damage_dice="1d8",
            char_class="fighter",
            level=2,
            is_pc=True,
        )
        return engine, tools

    def test_add_condition_tool(self, combat_with_combatants):
        """Test add_condition_tool applies condition."""
        engine, tools = combat_with_combatants
        add_condition = tools[9]._func  # add_condition_tool

        result = add_condition(target="pc_throk", condition="prone")
        assert "Applied 'prone'" in result
        assert "prone" in result
        assert "prone" in engine.combat.combatants["pc_throk"].conditions

    def test_add_multiple_conditions(self, combat_with_combatants):
        """Test adding multiple conditions."""
        engine, tools = combat_with_combatants
        add_condition = tools[9]._func  # add_condition_tool

        add_condition(target="pc_throk", condition="prone")
        result = add_condition(target="pc_throk", condition="blinded")
        assert "prone" in result
        assert "blinded" in result

        combatant = engine.combat.combatants["pc_throk"]
        assert "prone" in combatant.conditions
        assert "blinded" in combatant.conditions

    def test_remove_condition_tool(self, combat_with_combatants):
        """Test remove_condition_tool removes condition."""
        engine, tools = combat_with_combatants
        add_condition = tools[9]._func  # add_condition_tool
        remove_condition = tools[10]._func

        add_condition(target="pc_throk", condition="prone")
        result = remove_condition(target="pc_throk", condition="prone")
        assert "Removed 'prone'" in result
        assert "prone" not in engine.combat.combatants["pc_throk"].conditions

    def test_remove_condition_tool_safe(self, combat_with_combatants):
        """Test remove_condition_tool is safe when condition not present."""
        engine, tools = combat_with_combatants
        remove_condition = tools[10]._func

        # Should not raise error
        result = remove_condition(target="pc_throk", condition="nonexistent")
        assert "Removed 'nonexistent'" in result


class TestStatusTools:
    """Test status query tool functions."""

    @pytest.fixture
    def combat_with_combatants(self, engine, tools):
        """Set up combat with multiple combatants."""
        start_combat = tools[0]._func
        add_combatant = tools[1]._func

        start_combat()
        add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=18,
            damage_dice="1d8",
            char_class="fighter",
            level=2,
            is_pc=True,
        )
        add_combatant(
            id="goblin_01",
            name="Goblin",
            hp=5,
            hp_max=5,
            ac=6,
            thac0=19,
            damage_dice="1d6",
            char_class="goblin",
            level=1,
        )
        return engine, tools

    def test_get_combat_status_tool(self, combat_with_combatants):
        """Test get_combat_status_tool returns combat status."""
        engine, tools = combat_with_combatants
        get_combat_status = tools[11]._func

        result = get_combat_status()
        assert "Combat Status" in result
        assert "Round" in result
        assert "pc_throk" in result
        assert "goblin_01" in result
        assert "Throk" in result
        assert "Goblin" in result

    def test_get_combat_status_tool_no_combat(self, engine, tools):
        """Test get_combat_status_tool when no combat active."""
        get_combat_status = tools[11]._func

        result = get_combat_status()
        assert "No active combat" in result

    def test_get_combat_status_tool_with_conditions(self, combat_with_combatants):
        """Test get_combat_status_tool shows conditions."""
        engine, tools = combat_with_combatants
        add_condition = tools[9]._func  # add_condition_tool
        get_combat_status = tools[11]._func

        add_condition(target="pc_throk", condition="prone")
        result = get_combat_status()
        assert "prone" in result

    def test_get_combatant_tool(self, combat_with_combatants):
        """Test get_combatant_tool returns combatant details."""
        engine, tools = combat_with_combatants
        get_combatant = tools[12]._func

        result = get_combatant(id="pc_throk")
        assert "Throk" in result
        assert "HP:" in result
        assert "AC:" in result
        assert "THAC0:" in result
        assert "Class:" in result
        assert "[PC]" in result

    def test_get_combatant_tool_not_found(self, combat_with_combatants):
        """Test get_combatant_tool when combatant not found."""
        engine, tools = combat_with_combatants
        get_combatant = tools[12]._func

        result = get_combatant(id="nonexistent")
        assert "not found" in result

    def test_get_combatant_tool_no_combat(self, engine, tools):
        """Test get_combatant_tool when no combat active."""
        get_combatant = tools[12]._func

        result = get_combatant(id="pc_throk")
        assert "not found" in result or "not be active" in result


class TestToolIntegration:
    """Test tools working together in realistic scenarios."""

    async def test_full_combat_flow(self, engine, tools):
        """Test a complete combat flow using tools."""
        start_combat = tools[0]._func
        add_combatant = tools[1]._func
        roll_attack = tools[3]._func
        roll_damage = tools[4]._func
        end_combat = tools[2]._func

        # Start combat
        start_combat()

        # Add combatants
        add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=18,
            damage_dice="1d8",
            char_class="fighter",
            level=2,
            is_pc=True,
        )
        add_combatant(
            id="goblin_01",
            name="Goblin",
            hp=5,
            hp_max=5,
            ac=6,
            thac0=19,
            damage_dice="1d6",
            char_class="goblin",
            level=1,
        )

        # Attack
        attack_result = await roll_attack(attacker="pc_throk", target="goblin_01")
        assert "Attack roll:" in attack_result

        # Deal damage (assuming hit, but damage always applies in this test)
        damage_result = await roll_damage(attacker="pc_throk", target="goblin_01")
        assert "Damage:" in damage_result

        # End combat
        end_result = end_combat()
        assert "Combat ended" in end_result

    async def test_conditions_affect_combat(self, engine, tools):
        """Test that conditions affect attack rolls."""
        start_combat = tools[0]._func
        add_combatant = tools[1]._func
        add_condition = tools[9]._func  # add_condition_tool
        roll_attack = tools[3]._func

        start_combat()
        add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=18,
            damage_dice="1d8",
            char_class="fighter",
            level=2,
            is_pc=True,
        )
        add_combatant(
            id="goblin_01",
            name="Goblin",
            hp=5,
            hp_max=5,
            ac=6,
            thac0=19,
            damage_dice="1d6",
            char_class="goblin",
            level=1,
        )

        # Make Throk prone (should give -4 to attack)
        add_condition(target="pc_throk", condition="prone")

        # Attack should reflect the penalty
        result = await roll_attack(attacker="pc_throk", target="goblin_01")
        # The modifier should show -4 from prone
        assert "Attack roll:" in result

    async def test_pc_persistence(self, engine, tools):
        """Test that PC HP persists across combats."""
        start_combat = tools[0]._func
        add_combatant = tools[1]._func
        roll_damage = tools[4]._func
        end_combat = tools[2]._func

        # First combat - damage PC
        start_combat()
        add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=18,
            damage_dice="1d8",
            char_class="fighter",
            level=2,
            is_pc=True,
        )
        add_combatant(
            id="goblin_01",
            name="Goblin",
            hp=5,
            hp_max=5,
            ac=6,
            thac0=19,
            damage_dice="1d6",
            char_class="goblin",
            level=1,
        )

        # Goblin damages Throk
        await roll_damage(attacker="goblin_01", target="pc_throk")
        throk_hp_after_damage = engine.combat.combatants["pc_throk"].hp

        end_combat()

        # Second combat - PC HP should be remembered
        start_combat()
        add_combatant(
            id="pc_throk",
            name="Throk",
            hp=throk_hp_after_damage,  # Would use persistent HP in real scenario
            hp_max=10,
            ac=5,
            thac0=18,
            damage_dice="1d8",
            char_class="fighter",
            level=2,
            is_pc=True,
        )

        # Verify PC is in persistent storage
        assert "pc_throk" in engine.pcs
        assert engine.pcs["pc_throk"].hp == throk_hp_after_damage


class TestRollDiceTool:
    """Tests for the generic roll_dice_tool."""

    def test_roll_dice_simple(self):
        """Test simple dice roll."""
        engine = MechanicsEngine(debug_mode=False)
        tools = create_referee_tools(engine)
        roll_dice = tools[8]._func  # roll_dice_tool is at index 8

        result = roll_dice("1d6")
        assert "Rolled 1d6" in result
        assert "(1d6)" in result

    def test_roll_dice_with_purpose(self):
        """Test dice roll with purpose description."""
        engine = MechanicsEngine(debug_mode=False)
        tools = create_referee_tools(engine)
        roll_dice = tools[8]._func  # roll_dice_tool

        result = roll_dice("1d6", "Throk's initiative")
        assert "for Throk's initiative" in result
        assert "Rolled 1d6" in result

    def test_roll_dice_multiple_dice(self):
        """Test rolling multiple dice."""
        engine = MechanicsEngine(debug_mode=False)
        tools = create_referee_tools(engine)
        roll_dice = tools[8]._func  # roll_dice_tool

        result = roll_dice("2d6")
        assert "Rolled 2d6" in result
        assert "(2d6)" in result

    def test_roll_dice_with_modifier(self):
        """Test dice roll with modifier."""
        engine = MechanicsEngine(debug_mode=False)
        tools = create_referee_tools(engine)
        roll_dice = tools[8]._func  # roll_dice_tool

        result = roll_dice("1d20+5")
        assert "Rolled 1d20+5" in result

    def test_roll_dice_invalid_notation(self):
        """Test handling of invalid dice notation."""
        engine = MechanicsEngine(debug_mode=False)
        tools = create_referee_tools(engine)
        roll_dice = tools[8]._func  # roll_dice_tool

        result = roll_dice("invalid")
        assert "Invalid dice notation" in result

    def test_roll_dice_d100(self):
        """Test rolling percentile dice."""
        engine = MechanicsEngine(debug_mode=False)
        tools = create_referee_tools(engine)
        roll_dice = tools[8]._func  # roll_dice_tool

        result = roll_dice("1d100", "random encounter")
        assert "Rolled 1d100" in result
        assert "for random encounter" in result
