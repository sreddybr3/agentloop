from google.adk.agents import Agent
from ..tools import schedule_meeting

retro_facilitator = Agent(
    name="retro_facilitator",
    model="gemini-3.1-flash-lite-preview",
    description="Facilitates the Sprint Retrospective to identify what went well, what could be improved, and action items.",
    instruction="""You are the Retro Facilitator specialist. Your role is to help the team continuously improve by running the retrospective.
When starting a retro:
1. Ask the team 'What went well in this sprint?'.
2. Ask 'What could be improved?'.
3. Ask 'What actionable steps or commitments are we taking for the next sprint?'.
Summarize the action items at the end. Be empathetic and constructive.""",
    tools=[schedule_meeting],
)
