"""Game loop orchestration using AutoGen 0.4."""

from typing import Sequence

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_core.tools import FunctionTool

from dndbots.campaign import Campaign
from dndbots.events import GameEvent, EventType
from dndbots.memory import MemoryBuilder
from dndbots.models import Character
from dndbots.prompts import build_dm_prompt, build_player_prompt, build_referee_prompt
from dndbots.output import EventBus, OutputEvent, OutputEventType
from dndbots.output.plugins import ConsolePlugin
from dndbots.providers import Provider, create_model_client
from dndbots.rules_tools import create_rules_tools
from dndbots.mechanics import MechanicsEngine
from dndbots.referee_tools import create_referee_tools
from dndbots.dm_tools import create_dm_tools


def create_dm_agent(
    scenario: str,
    model: str = "gpt-4o",
    enable_rules_tools: bool = True,
    party_document: str | None = None,
    neo4j: "Neo4jStore | None" = None,
    campaign_id: str | None = None,
    provider: Provider | None = None,
) -> AssistantAgent:
    """Create the Dungeon Master agent.

    Args:
        scenario: The adventure scenario
        model: Model name or alias to use
        enable_rules_tools: Enable rules lookup tools (default: True)
        party_document: Optional party background from Session Zero
        neo4j: Optional Neo4jStore for narrative tools
        campaign_id: Campaign ID for recording
        provider: Model provider (auto-detected from env if None)

    Returns:
        Configured DM agent with optional rules and narrative tools
    """
    model_client = create_model_client(provider=provider, model=model)

    # Create rules tools if enabled
    tools = []
    if enable_rules_tools:
        lookup, list_rules, search = create_rules_tools()
        tools = [lookup, list_rules, search]

    # Add DM narrative/query tools if Neo4j configured
    if neo4j and campaign_id:
        dm_tools = create_dm_tools(neo4j=neo4j, campaign_id=campaign_id)
        tools.extend(dm_tools)

    return AssistantAgent(
        name="dm",
        model_client=model_client,
        system_message=build_dm_prompt(scenario, party_document=party_document),
        tools=tools,
        reflect_on_tool_use=True,  # Summarize tool output naturally
    )


def sanitize_agent_name(name: str) -> str:
    """Sanitize character name to be a valid Python identifier for AutoGen.

    Args:
        name: Character name (may include nicknames, quotes, etc.)

    Returns:
        Valid Python identifier (first name only, alphanumeric)
    """
    import re
    # Extract first word before any quotes, parentheses, or "the"
    # e.g., 'Thalia "The Wandering Shadow"' -> 'Thalia'
    first_name = name.split()[0].split('"')[0].split("'")[0]
    # Remove any non-alphanumeric characters
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '', first_name)
    # Ensure it doesn't start with a number
    if sanitized and sanitized[0].isdigit():
        sanitized = '_' + sanitized
    return sanitized or 'player'


def create_player_agent(
    character: Character,
    model: str = "gpt-4o",
    memory: str | None = None,
    party_document: str | None = None,
    provider: Provider | None = None,
) -> AssistantAgent:
    """Create a player agent for a character.

    Args:
        character: The character to play
        model: Model name or alias to use
        memory: Optional DCML memory block
        party_document: Optional party background from Session Zero
        provider: Model provider (auto-detected from env if None)

    Returns:
        Configured player agent
    """
    model_client = create_model_client(provider=provider, model=model)
    agent_name = sanitize_agent_name(character.name)

    return AssistantAgent(
        name=agent_name,
        model_client=model_client,
        system_message=build_player_prompt(character, memory=memory, party_document=party_document),
    )


def create_referee_agent(
    engine: MechanicsEngine,
    model: str = "gpt-4o",
    neo4j: "Neo4jStore | None" = None,
    campaign_id: str | None = None,
    session_id: str | None = None,
    provider: Provider | None = None,
) -> AssistantAgent:
    """Create the Rules Referee agent.

    Args:
        engine: MechanicsEngine instance for mechanics resolution
        model: Model name or alias to use
        neo4j: Optional Neo4jStore for recording moments
        campaign_id: Campaign ID for recording
        session_id: Session ID for recording
        provider: Model provider (auto-detected from env if None)

    Returns:
        Configured Referee agent with mechanics tools
    """
    model_client = create_model_client(provider=provider, model=model)
    tools = create_referee_tools(
        engine,
        neo4j=neo4j,
        campaign_id=campaign_id,
        session_id=session_id,
    )

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
    - After initial task (user) → DM (to set the scene)
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

    # Initial task message comes from "user" - DM should respond first
    if last_speaker == "user":
        return "dm"

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
        provider: Provider | None = None,
    ):
        """Initialize a game session.

        Args:
            scenario: The adventure scenario
            characters: List of player characters
            dm_model: Model name or alias for DM agent
            player_model: Model name or alias for player agents
            campaign: Optional campaign for persistence
            enable_memory: Enable DCML memory projection (default: True)
            event_bus: Optional event bus for output (default: ConsolePlugin)
            party_document: Optional party background from Session Zero
            enable_referee: Enable Referee agent for mechanics (default: True)
            provider: Model provider (auto-detected from env if None)
        """
        self.provider = provider
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
        neo4j_store = campaign._neo4j if campaign else None
        campaign_id = campaign.campaign_id if campaign else None

        self.dm = create_dm_agent(
            scenario,
            dm_model,
            party_document=party_document,
            neo4j=neo4j_store,
            campaign_id=campaign_id,
            provider=self.provider,
        )

        # Add update_party_document tool if party_document exists
        if self.party_document is not None:
            update_tool = create_update_party_document_tool(self)
            self.dm._tools.append(update_tool)

        # Create Referee agent if enabled
        self.referee = None
        if enable_referee:
            self.referee = create_referee_agent(
                self.mechanics_engine,
                dm_model,
                neo4j=neo4j_store,
                campaign_id=campaign_id,
                session_id=campaign.current_session_id if campaign else None,
                provider=self.provider,
            )

        self.players = [
            create_player_agent(
                char, player_model, party_document=party_document, provider=self.provider
            )
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
            model_client=create_model_client(provider=self.provider, model=dm_model),
            selector_func=dm_selector,
            termination_condition=TextMentionTermination("SESSION PAUSE"),
        )

    async def initialize(self) -> None:
        """Async initialization - inject recap and player memories."""
        from autogen_core.models import SystemMessage

        # Inject DM recap
        if self.campaign and self.campaign._neo4j:
            recap = await self.campaign.generate_session_recap()
            if recap:
                # Update DM's system message
                current_message = self.dm._system_messages[0].content
                self.dm._system_messages[0] = SystemMessage(
                    content=f"{current_message}\n\n{recap}",
                )

        # Build player memories from graph
        if self._memory_builder and self.campaign and self.campaign._neo4j:
            for i, player in enumerate(self.players):
                char = self.characters[i]
                memory = await self._build_player_memory(char)
                if memory:
                    # Inject memory into player's system message
                    current = player._system_messages[0].content
                    player._system_messages[0] = SystemMessage(
                        content=f"{current}\n\n{memory}",
                    )

    async def run(self) -> None:
        """Run the game session.

        Note:
            Phase 1 uses "SESSION PAUSE" termination condition.
            Turn counting/max_turns will be added in a future phase if needed.
        """
        # Initialize (inject recap, etc.)
        await self.initialize()

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

                        # Handle content that may be a list (e.g., MultiModalMessage)
                        content = message.content
                        if isinstance(content, list):
                            content = " ".join(str(c) for c in content)

                        event = GameEvent(
                            event_type=event_type,
                            source=message.source,
                            content=content,
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
        # Note: AutoGen source is the sanitized agent name (e.g., "Throk" not "Throk the Mighty")
        if source == "dm":
            event_type = OutputEventType.NARRATION
        elif source == "referee":
            event_type = OutputEventType.REFEREE
        elif source.startswith("pc_") or any(
            source == sanitize_agent_name(c.name) for c in self.characters
        ):
            event_type = OutputEventType.PLAYER_ACTION
        else:
            event_type = OutputEventType.SYSTEM

        await self._event_bus.emit(OutputEvent(
            event_type=event_type,
            source=source,
            content=content,
        ))

    async def _build_player_memory(self, char: Character) -> str | None:
        """Build DCML memory for a player character.

        Prefers Neo4j graph if available, falls back to event-based.

        Args:
            char: The character to build memory for

        Returns:
            DCML memory document, or None if memory is disabled
        """
        if not self._memory_builder:
            return None

        char_id = getattr(char, 'char_id', None) or f"pc_{char.name.lower()}_001"

        # Use graph-based memory if Neo4j is available
        if self.campaign and self.campaign._neo4j:
            return await self._memory_builder.build_from_graph(
                pc_id=char_id,
                character=char,
                neo4j=self.campaign._neo4j,
            )

        # Fallback to event-based memory
        events = []
        if self.campaign:
            events = await self.campaign.get_session_events()

        return self._memory_builder.build_memory_document(
            pc_id=char_id,
            character=char,
            all_characters=self.characters,
            events=events,
        )
