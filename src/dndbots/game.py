"""Game loop orchestration using AutoGen 0.4."""

from typing import Sequence

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_core.tools import FunctionTool
from autogen_ext.models.openai import OpenAIChatCompletionClient

from dndbots.campaign import Campaign
from dndbots.events import GameEvent, EventType
from dndbots.memory import MemoryBuilder
from dndbots.models import Character
from dndbots.prompts import build_dm_prompt, build_player_prompt, build_referee_prompt
from dndbots.output import EventBus, OutputEvent, OutputEventType
from dndbots.output.plugins import ConsolePlugin
from dndbots.rules_tools import create_rules_tools
from dndbots.mechanics import MechanicsEngine
from dndbots.referee_tools import create_referee_tools


def create_dm_agent(
    scenario: str,
    model: str = "gpt-4o",
    enable_rules_tools: bool = True,
    party_document: str | None = None,
) -> AssistantAgent:
    """Create the Dungeon Master agent.

    Args:
        scenario: The adventure scenario
        model: OpenAI model to use
        enable_rules_tools: Enable rules lookup tools (default: True)
        party_document: Optional party background from Session Zero

    Returns:
        Configured DM agent with optional rules tools
    """
    model_client = OpenAIChatCompletionClient(model=model)

    # Create rules tools if enabled
    tools = []
    if enable_rules_tools:
        lookup, list_rules, search = create_rules_tools()
        tools = [lookup, list_rules, search]

    return AssistantAgent(
        name="dm",
        model_client=model_client,
        system_message=build_dm_prompt(scenario, party_document=party_document),
        tools=tools,
        reflect_on_tool_use=True,  # Summarize tool output naturally
    )


def create_player_agent(
    character: Character,
    model: str = "gpt-4o",
    memory: str | None = None,
    party_document: str | None = None,
) -> AssistantAgent:
    """Create a player agent for a character.

    Args:
        character: The character to play
        model: OpenAI model to use
        memory: Optional DCML memory block
        party_document: Optional party background from Session Zero

    Returns:
        Configured player agent
    """
    model_client = OpenAIChatCompletionClient(model=model)

    return AssistantAgent(
        name=character.name,
        model_client=model_client,
        system_message=build_player_prompt(character, memory=memory, party_document=party_document),
    )


def create_referee_agent(
    engine: MechanicsEngine,
    model: str = "gpt-4o",
) -> AssistantAgent:
    """Create the Rules Referee agent.

    Args:
        engine: MechanicsEngine instance for mechanics resolution
        model: OpenAI model to use

    Returns:
        Configured Referee agent with mechanics tools
    """
    model_client = OpenAIChatCompletionClient(model=model)
    tools = create_referee_tools(engine)

    return AssistantAgent(
        name="referee",
        model_client=model_client,
        system_message=build_referee_prompt(),
        tools=tools,
        reflect_on_tool_use=True,  # Summarize tool output naturally
    )


def dm_selector(messages: Sequence) -> str | None:
    """Custom selector: DM controls turn order with Referee for mechanics.

    Turn order flow:
    - After player speaks → Referee (for mechanical resolution)
    - After Referee speaks → DM (to narrate consequences)
    - After DM speaks → model decides next player

    Args:
        messages: Sequence of messages in the conversation

    Returns:
        Agent name to speak next, or None to use model-based selection
    """
    if not messages:
        return "dm"

    last_speaker = messages[-1].source

    # After Referee speaks, return to DM
    if last_speaker == "referee":
        return "dm"

    # After player speaks, pass to Referee for mechanical resolution
    if last_speaker != "dm" and last_speaker != "referee":
        return "referee"

    # DM just spoke - let the model selector figure out who was addressed
    return None


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

        return f"Party document updated successfully with new section: {section}"

    return FunctionTool(update_party_document, description=update_party_document.__doc__)


class DnDGame:
    """Orchestrates a D&D game session."""

    def __init__(
        self,
        scenario: str,
        characters: list[Character],
        dm_model: str = "gpt-4o",
        player_model: str = "gpt-4o",
        campaign: Campaign | None = None,
        enable_memory: bool = True,
        event_bus: EventBus | None = None,
        party_document: str | None = None,
        enable_referee: bool = True,
    ):
        """Initialize a game session.

        Args:
            scenario: The adventure scenario
            characters: List of player characters
            dm_model: Model for DM agent
            player_model: Model for player agents
            campaign: Optional campaign for persistence
            enable_memory: Enable DCML memory projection (default: True)
            event_bus: Optional event bus for output (default: ConsolePlugin)
            party_document: Optional party background from Session Zero
            enable_referee: Enable Referee agent for mechanics (default: True)
        """
        self.scenario = scenario
        self.characters = characters
        self.campaign = campaign
        self.party_document = party_document
        self._memory_builder = MemoryBuilder() if enable_memory else None

        # Initialize event bus (default to console output)
        if event_bus is None:
            event_bus = EventBus()
            event_bus.register(ConsolePlugin())
        self._event_bus = event_bus

        # Initialize MechanicsEngine
        self.mechanics_engine = MechanicsEngine()

        # Create agents
        self.dm = create_dm_agent(scenario, dm_model, party_document=party_document)

        # Add update_party_document tool if party_document exists
        if self.party_document is not None:
            update_tool = create_update_party_document_tool(self)
            self.dm._tools.append(update_tool)

        # Create Referee agent if enabled
        self.referee = None
        if enable_referee:
            self.referee = create_referee_agent(self.mechanics_engine, dm_model)

        self.players = [
            create_player_agent(char, player_model, party_document=party_document)
            for char in characters
        ]

        # Build participant list (DM first, then Referee if enabled, then players)
        participants = [self.dm]
        if self.referee is not None:
            participants.append(self.referee)
        participants.extend(self.players)

        # Create the group chat with DM-controlled selection
        self.team = SelectorGroupChat(
            participants=participants,
            model_client=OpenAIChatCompletionClient(model=dm_model),
            selector_func=dm_selector,
            termination_condition=TextMentionTermination("SESSION PAUSE"),
        )

    async def run(self) -> None:
        """Run the game session.

        Note:
            Phase 1 uses "SESSION PAUSE" termination condition.
            Turn counting/max_turns will be added in a future phase if needed.
        """
        # Start the event bus
        await self._event_bus.start()

        # Emit session start event
        campaign_id = self.campaign.campaign_id if self.campaign else "unknown"
        await self._event_bus.emit(OutputEvent(
            event_type=OutputEventType.SESSION_START,
            source="system",
            content=f"Session started: {campaign_id}",
        ))

        try:
            # Start with DM setting the scene
            initial_message = (
                f"Begin the adventure. Set the scene for the party: "
                f"{', '.join(c.name for c in self.characters)}. "
                f"Describe where they are and what they see."
            )

            async for message in self.team.run_stream(task=initial_message):
                # Emit message to output plugins
                if hasattr(message, 'source') and hasattr(message, 'content'):
                    await self._emit_message(message)

                    # Record event if campaign is set
                    if self.campaign:
                        # Determine event type based on source
                        if message.source == "dm":
                            event_type = EventType.DM_NARRATION
                        else:
                            event_type = EventType.PLAYER_ACTION

                        event = GameEvent(
                            event_type=event_type,
                            source=message.source,
                            content=message.content,
                            session_id=self.campaign.current_session_id or "unknown",
                        )
                        await self.campaign.record_event(event)
        finally:
            # Emit session end and stop the bus
            await self._event_bus.emit(OutputEvent(
                event_type=OutputEventType.SESSION_END,
                source="system",
                content="Session ended",
            ))
            await self._event_bus.stop()

    async def _emit_message(self, message) -> None:
        """Convert AutoGen message to OutputEvent and emit.

        Args:
            message: AutoGen message with source and content attributes
        """
        source = getattr(message, 'source', 'unknown')
        content = getattr(message, 'content', str(message))

        # Determine event type based on source
        if source == "dm":
            event_type = OutputEventType.NARRATION
        elif source == "referee":
            event_type = OutputEventType.SYSTEM
        elif source.startswith("pc_") or any(source == c.name for c in self.characters):
            event_type = OutputEventType.PLAYER_ACTION
        else:
            event_type = OutputEventType.SYSTEM

        await self._event_bus.emit(OutputEvent(
            event_type=event_type,
            source=source,
            content=content,
        ))

    def _build_player_memory(self, char: Character) -> str | None:
        """Build DCML memory for a player character.

        Args:
            char: The character to build memory for

        Returns:
            DCML memory document, or None if memory is disabled
        """
        if not self._memory_builder:
            return None

        char_id = getattr(char, 'char_id', None) or f"pc_{char.name.lower()}_001"

        # Get events from campaign if available
        events = []
        if self.campaign:
            # TODO: Get events from campaign.get_session_events()
            pass

        return self._memory_builder.build_memory_document(
            pc_id=char_id,
            character=char,
            all_characters=self.characters,
            events=events,
        )
