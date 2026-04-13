from google.adk.agents import Agent
from ..tools import get_sprint_backlog, schedule_meeting

sprint_reviewer = Agent(
    name="sprint_reviewer",
    model="gemini-3.1-flash-lite-preview",
    description="Facilitates the Sprint Review to demo work and gather feedback from stakeholders.",
    instruction="""You are the Sprint Reviewer specialist. Your role is to help the team demonstrate what was achieved during the sprint.
When interacting:
1. Use get_sprint_backlog to identify tickets that are 'Done'.
2. Help the team summarize their accomplishments.
3. Ask the user for any stakeholder feedback they want to note.
4. If needed, schedule the sprint review meeting.""",
    tools=[get_sprint_backlog, schedule_meeting],
)
