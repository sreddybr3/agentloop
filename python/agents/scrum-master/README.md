# Scrum Master AI Agent

A Multi-Agent system built using the Google Python ADK that acts as an Agile Scrum Master. 
It orchestrates different Scrum events by routing user requests to specialized sub-agents.

## Agents

- **scrum_master** (Coordinator): Routes to correct sub-agents.
- **sprint_planner**: Facilitates the Sprint Planning meeting.
- **standup_facilitator**: Assists in running the Daily Standup.
- **sprint_reviewer**: Helps orchestrate the Sprint Review.
- **retro_facilitator**: Facilitates the Sprint Retrospective.

## Mock Tools

Currently, the agents use mock tools defined in `tools.py` for dealing with sprint systems (e.g., Jira logging, ticketing):
- `get_sprint_backlog`
- `update_ticket_status`
- `log_blocker`
- `schedule_meeting`

## Prerequisites

- Python >= 3.10
- Google GenAI Key or Vertex AI configured.

## Setup

1. From the `scrum-master` directory, install dependencies:
   ```bash
   pip install -e .
   ```

2. Copy the template and add your environment variables:
   ```bash
   cp .env.example .env
   # Ensure you set GOOGLE_CLOUD_PROJECT or have application-default credentials
   ```

## Running the Agent

You can run the agent locally using the ADK CLI:

```bash
# Run interactively in the terminal
adk run scrum_master

# Run with a local web interface
adk web .
```
