# Session Zero Design

## Overview

Before gameplay begins, DM and players collaboratively create a cohesive campaign through three phases. This mirrors real tabletop Session Zero practices where players pitch ideas, find connections, then finalize characters and setting.

## Phases

### Phase 1: Pitch
Each agent proposes their initial concept:
- DM shares campaign concept, setting, and hook (using `guides/interesting-campaigns`)
- Each player pitches character concept and background (using `guides/interesting-characters`)
- DM facilitates by asking each player in turn

### Phase 2: Converge
Agents find connections between their concepts:
- DM actively facilitates: "Player 2, how does your character know Player 1's?"
- Players propose shared history, relationships, ties to campaign hook
- DM adjusts scenario to incorporate character backgrounds
- Iteration continues until cohesive party emerges

### Phase 3: Lock
Final mechanical details and artifact production:
- Each player finalizes stats, equipment, HP using class rules
- DM produces final scenario incorporating all threads
- DM produces party document summarizing relationships and hooks

## Communication Model

**Message history**: Each phase sees the full transcript of previous phases. Creative context benefits from seeing *how* others described things, not just structured output.

**DM-moderated turns**: DM always speaks last in each round, synthesizes, and prompts specific players. Matches existing `dm_selector` pattern in game.py.

**Phase markers**: DM declares phase transitions with exact phrases:
- `"PITCH COMPLETE"` - end of Phase 1
- `"CONVERGENCE COMPLETE"` - end of Phase 2
- `"SESSION ZERO LOCKED"` - end of Phase 3, triggers output parsing

## Outputs

Session Zero produces three artifacts for the game loop:

1. **scenario** (`str`) - Adventure setup text for DnDGame
2. **characters** (`list[Character]`) - Mechanical character data for 3 players
3. **party_document** (`str`) - Relationships, shared history, plot hooks

The party document serves dual purposes:
- Injected into DM and player prompts during gameplay
- Viewer-readable artifact for audience/logs

## During Gameplay: Housekeeping

DM has access to `update_party_document()` tool during gameplay:
- Updates relationships, plot threads, notable events
- Tool description encourages use after major events
- Keeps party document current as living artifact

Future enhancement: Generic nudging system for multiple housekeeping tasks if DM forgets.

## Implementation

### New Class: SessionZero

Location: `src/dndbots/session_zero.py`

```python
@dataclass
class SessionZeroResult:
    scenario: str
    characters: list[Character]
    party_document: str
    transcript: list[Message]


class SessionZero:
    def __init__(
        self,
        num_players: int = 3,
        dm_model: str = "gpt-4o",
        player_model: str = "gpt-4o",
    ):
        # Creates DM agent + N player agents
        # All have access to rules tools
        # DM has campaign/encounter guides in prompt
        # Players have character guide in prompt

    async def run(self) -> SessionZeroResult:
        # Runs all three phases
        # Detects phase markers in DM messages
        # Parses structured outputs after SESSION ZERO LOCKED
        # Returns result for game loop
```

### Agent Prompts

**DM System Prompt (Session Zero)**:
```
You are the Dungeon Master for a Session Zero - collaborative campaign creation.

Your job is to FACILITATE, not dominate. Guide the players to create a cohesive party.

PHASE 1 (Pitch): Share your campaign concept, then ask each player for their character pitch.
PHASE 2 (Converge): Help players find connections between characters and to your campaign.
PHASE 3 (Lock): Get final mechanical details, then produce the scenario and party document.

Use these tools to look up rules and guides:
- lookup_rules("guides/interesting-campaigns", detail="full") - for your campaign
- lookup_rules("guides/interesting-encounters", detail="full") - for planning
- lookup_rules("classes/X", detail="full") - for player questions

When a phase is complete, say the marker phrase exactly:
- "PITCH COMPLETE"
- "CONVERGENCE COMPLETE"
- "SESSION ZERO LOCKED"

After SESSION ZERO LOCKED, output:
[SCENARIO]
<your scenario text>
[/SCENARIO]

[PARTY_DOCUMENT]
<relationships, hooks, shared history>
[/PARTY_DOCUMENT]
```

**Player System Prompt (Session Zero)**:
```
You are a player in Session Zero - collaborative character creation.

Follow the DM's lead through each phase. When asked:
- Pitch a character concept (use guides/interesting-characters)
- Find connections to other players and the campaign
- Finalize mechanical details (use classes/X for your class)

After SESSION ZERO LOCKED, output your final character:
[CHARACTER]
Name:
Class:
Stats: STR/INT/WIS/DEX/CON/CHA
HP:
AC:
Equipment:
Background:
[/CHARACTER]
```

### Parsing

After `SESSION ZERO LOCKED`, parse structured blocks from final messages:
- DM message: `[SCENARIO]...[/SCENARIO]` and `[PARTY_DOCUMENT]...[/PARTY_DOCUMENT]`
- Player messages: `[CHARACTER]...[/CHARACTER]` parsed into Character dataclass

### Integration

**Handoff to game loop**:
```python
session_zero = SessionZero(num_players=3)
result = await session_zero.run()

game = DnDGame(
    scenario=result.scenario,
    characters=result.characters,
    party_document=result.party_document,
    campaign=campaign,
)
await game.run()
```

**Prompt injection**: Modify `build_dm_prompt()` and `build_player_prompt()` to accept optional `party_document` parameter and include it in the prompt.

**DnDGame changes**: Accept optional `party_document` in `__init__`, pass to prompt builders.

## Example Flow

```
=== PHASE 1: PITCH ===

DM: "Welcome to Session Zero. I'll share my campaign concept, then each of you pitch your character."

DM: [Looks up guides/interesting-campaigns]
    "I'm thinking a frontier town threatened by an ancient evil awakening in nearby ruins.
     The town of Thornwall sits at the edge of civilized lands..."

DM: "Player 1, what character are you thinking?"

Player1: [Looks up guides/interesting-characters]
    "I'm playing Kira, a former soldier who deserted after her unit was ordered to
     massacre villagers. She's seeking redemption and fears becoming a monster..."

DM: "Player 2, your turn."

Player2: "I'm playing Brother Marcus, a cynical priest who lost his faith after his
    temple was destroyed. He's searching for proof the gods still care..."

DM: "Player 3?"

Player3: "I'm playing Whisper, a halfling thief who talks to her daggers and collects
    teeth from interesting people she meets. She's running from a debt..."

DM: "Great concepts. We have redemption, lost faith, and running from the past.
     PITCH COMPLETE"

=== PHASE 2: CONVERGE ===

DM: "Let's find connections. Kira, looking at Marcus's background - any shared history?"

Player1: "What if Marcus was the priest who gave last rites to the villagers Kira's
    unit killed? She recognized him and has been working up courage to confess."

DM: "Marcus, does that work for you?"

Player2: "Yes - and that massacre was what broke my faith. I don't know Kira was there,
    but I've been haunted by not being able to save them."

DM: "Powerful. Whisper, how do you fit in?"

Player3: "The debt I'm running from? I stole from the cult that's awakening the ancient
    evil. They're hunting me, which is why I'm in Thornwall - hiding at the edge of nowhere."

DM: "Perfect - you've unknowingly brought the danger to their doorstep. The cult followed
     you here, and their ritual is what's awakening the evil in the ruins.
     CONVERGENCE COMPLETE"

=== PHASE 3: LOCK ===

DM: "Time to finalize. Player 1, confirm Kira's mechanical details."

Player1: [Looks up classes/fighter]
    "[CHARACTER]
     Name: Kira Ashford
     Class: Fighter
     Stats: STR 15, INT 10, WIS 12, DEX 13, CON 14, CHA 8
     HP: 7
     AC: 4 (chain mail + shield)
     Equipment: longsword, shield, chain mail, backpack, rope, torches
     Background: Deserted soldier seeking redemption
     [/CHARACTER]"

[Players 2 and 3 similarly lock in]

DM: "SESSION ZERO LOCKED

[SCENARIO]
The frontier town of Thornwall has seen strange lights in the ruins north of town.
Livestock have gone missing. Last night, a farmer saw robed figures chanting in the
old cemetery. The mayor offers 100 gold to investigate.

Unknown to most, a cult of the Sleeper has followed a halfling thief to this remote
town. Their ritual to awaken an ancient evil is nearly complete. The party has three
days before the Sleeper rises.
[/SCENARIO]

[PARTY_DOCUMENT]
## Party: The Thornwall Three

### Relationships
- Kira and Marcus share a dark history: Kira's unit massacred villagers that Marcus
  tried to save. Neither knows the other was there. This secret binds them.
- Whisper is unknowingly responsible for bringing danger to Thornwall - she stole
  from the cult, and they followed her here.

### Character Hooks
- Kira: Seeking redemption for following orders she knew were wrong
- Marcus: Searching for proof the gods haven't abandoned the world
- Whisper: Running from a debt to dangerous people (the cult)

### Shared Goals
- Stop the cult's ritual before the Sleeper awakens
- Protect Thornwall from the threat Whisper accidentally brought

### Potential Tensions
- When Kira's role in the massacre is revealed, how will Marcus react?
- When the party learns Whisper brought the cult here, will they protect her or hand her over?
[/PARTY_DOCUMENT]"
```

## Future Enhancements

- **Nudging system**: Generic housekeeping reminders for multiple tasks if DM forgets
- **Viewer artifacts**: Export party document as formatted HTML/PDF for audience
- **Multi-session continuity**: Party document evolves across sessions, persisted to database
