#!/usr/bin/env python3
"""E2E Test: Agent uses character guide to create an interesting character."""

from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

from dndbots.rules_tools import create_rules_tools


async def main():
    lookup, list_rules, search = create_rules_tools()

    model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")

    agent = AssistantAgent(
        name="character_creator",
        model_client=model_client,
        tools=[lookup, list_rules, search],
        system_message="""You are a character creation assistant for Basic D&D (1983 Red Box).

Tools available:
- lookup_rules(path, detail): Get rules by path. Examples:
  - "classes/fighter" for class details
  - "guides/interesting-characters" for creative guidance
- list_rules_tool(category): List entries in "classes", "guide", etc.
- search_rules_tool(query): Search by keyword

When creating a character, FIRST look up the character creation guide for tips on making them interesting, THEN look up the class rules.""",
        reflect_on_tool_use=True,
    )

    print("=" * 70)
    print("E2E TEST: Create interesting character using guide")
    print("=" * 70)

    await Console(
        agent.run_stream(task="Create an interesting 1st-level Fighter character. Use the character creation guide first to make them memorable, then use the class rules for the mechanical details.")
    )

    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
