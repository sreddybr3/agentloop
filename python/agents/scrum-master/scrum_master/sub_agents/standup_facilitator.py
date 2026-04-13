from google.adk.agents import Agent
from ..tools import update_ticket_status, log_blocker, get_sprint_backlog

standup_facilitator = Agent(
    name="standup_facilitator",
    model="gemini-3.1-flash-lite-preview",
    description="Facilitates the Daily Standup to sync the team, check ticket status, and log blockers.",
    instruction="""You are the Standup Facilitator specialist. Your role is to conduct the daily standup effectively.
When a user is running a standup with you:
1. Ask the 3 standard questions: What did you do yesterday? What will you do today? Are there any blockers?
2. If a member reports a blocker, use the log_blocker tool.
3. If a member reports a ticket is complete or moving to in-progress, use the update_ticket_status tool.
4. Keep the conversation focused and short.""",
    tools=[update_ticket_status, log_blocker, get_sprint_backlog],
)
