#!/usr/bin/env python3
"""End-to-end test: Agent creates character using rules tools."""

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
        name="dm",
        model_client=model_client,
        tools=[lookup, list_rules, search],
        system_message="""You are a DM for Basic D&D (1983 Red Box). Use the rules tools:
- lookup_rules(path, detail): Get entry by path like "monsters/goblin", "classes/thief"
- list_rules_tool(category): List entries in "monsters", "spells", "classes", "equipment"
- search_rules_tool(query): Search by keyword""",
        reflect_on_tool_use=True,
    )

    print("=" * 60)
    print("END-TO-END TEST")
    print("=" * 60)

    await Console(
        agent.run_stream(task="Look up the thief class requirements, then find a 1st-level monster for a solo thief to fight.")
    )

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
