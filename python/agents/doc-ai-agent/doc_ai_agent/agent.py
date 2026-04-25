import pathlib, os
from google.adk.agents import Agent
from google.adk.skills import load_skill_from_dir
from google.adk.tools import skill_toolset
from google.adk.models.lite_llm import LiteLlm

_model = os.environ.get("MODEL_NAME", "gemini-3.1-flash-lite-preview")
_model = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")
_model = LiteLlm(model="ollama_chat/qwen3.5:4b")

# Load the skill from the .claude directory.
# The path is relative to the root of the project.
doc_ai_skill = load_skill_from_dir(
    pathlib.Path(__file__).parent / "skills" / "doc-ai-extractor"
)

# Create a toolset from the skill
doc_ai_toolset = skill_toolset.SkillToolset(
    skills=[doc_ai_skill]
)


# litellm._turn_on_debug()

# Define the root agent
root_agent = Agent(
    model=_model,
    name="doc_ai_agent",
    description="An agent that can extract structured data from PDF documents.",
    instruction=(
        "You are a helpful assistant that can extract structured "
        "key-value pairs from PDF documents. You will be provided with a "
        "path to a PDF document and a JSON schema. Use the "
        "doc-ai-extractor skill to perform the extraction."
    ),
    tools=[
        doc_ai_toolset,
    ],
)