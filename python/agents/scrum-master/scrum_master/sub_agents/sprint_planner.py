from google.adk.agents import Agent
from ..tools import get_sprint_backlog, schedule_meeting

sprint_planner = Agent(
    name="sprint_planner",
    model="gemini-3.1-flash-lite-preview",
    description="Facilitates the Sprint Planning meeting to define goals and select backlog items.",
    instruction="""You are the Sprint Planner specialist. Your role is to help the team define the Sprint Goal and select items from the backlog for the upcoming sprint.
When interacting with the team:
1. Briefly state the purpose of sprint planning.
2. Ask for the team's capacity and draft a sprint goal.
3. Suggest pulling items from the backlog using your tools.
4. If asked, you can schedule the actual sprint planning meeting.""",
    tools=[get_sprint_backlog, schedule_meeting],
)
