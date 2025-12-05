# DnDBots

Multi-AI D&D campaign system using AutoGen 0.4.

## Phase 1: Minimal Viable Game Loop

Basic D&D game with one DM and one player agent, console output only.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

```bash
cp .env.example .env
# Add your OPENAI_API_KEY to .env
dndbots
```
