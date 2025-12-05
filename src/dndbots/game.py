"""Game loop orchestration using AutoGen 0.4."""

from typing import Sequence

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_ext.models.openai import OpenAIChatCompletionClient

from dndbots.campaign import Campaign
from dndbots.events import GameEvent, EventType
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


def dm_selector(messages: Sequence) -> str | None:
    """Custom selector: DM controls turn order.

    After any player speaks, return to DM.
    DM decides who goes next by addressing them.

    Args:
        messages: Sequence of messages in the conversation

    Returns:
        Agent name to speak next, or None to use model-based selection
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
        campaign: Campaign | None = None,
    ):
        """Initialize a game session.

        Args:
            scenario: The adventure scenario
            characters: List of player characters
            dm_model: Model for DM agent
            player_model: Model for player agents
            campaign: Optional campaign for persistence
        """
        self.scenario = scenario
        self.characters = characters
        self.campaign = campaign

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

    async def run(self) -> None:
        """Run the game session.

        Note:
            Phase 1 uses "SESSION PAUSE" termination condition.
            Turn counting/max_turns will be added in a future phase if needed.
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
