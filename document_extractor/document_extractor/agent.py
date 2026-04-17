import os
from google.adk.agents import Agent
from .tools.extractor import extract_document_data

_model = os.environ.get("MODEL_NAME", "gemini-3.1-flash-lite-preview")

root_agent = Agent(
    name="document_extractor_coordinator",
    model=_model,
    description="Agent that coordinates dynamic document extraction.",
    instruction="""You are a dynamic document extraction coordinator.
Your goal is to help users extract structured data from documents.

When a user provides a document and a JSON schema definition (keys and descriptions),
you MUST call the extract_document_data tool with two arguments:
  - document_text: the full document text exactly as provided
  - schema_json_str: the JSON schema string exactly as provided

After the tool returns, inspect the result:
  - If status is "success", format the "data" object as pretty-printed JSON and return it.
  - If status is "error", report the error_message to the user so they can troubleshoot.

Do NOT attempt to extract data yourself. Always delegate to the tool.
""",
    tools=[extract_document_data],
)
