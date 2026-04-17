"""Local ADK agent that uses Ollama (Gemma4) for both orchestration and extraction.

This agent mirrors agent.py but:
  - Uses ``extract_document_data_local`` (Ollama-based) as its tool
  - Uses an Ollama model via LiteLLM for the agent's own LLM orchestration

Requirements:
    pip install google-adk[extensions]   # adds litellm support
    ollama pull gemma4:latest

Environment variables:
    OLLAMA_BASE_URL   – Ollama API URL         (default: http://localhost:11434)
    OLLAMA_MODEL      – Model for extraction   (default: gemma4:latest)
    LOCAL_AGENT_MODEL – Model for agent LLM    (default: ollama/gemma4:latest)
"""

import os
from google.adk.models.lite_llm import LiteLlm

from google.adk.agents import Agent
from ..document_extractor.tools.local_extractor import extract_document_data_local

# For the agent's own LLM (orchestration), we use LiteLLM's Ollama provider.
# Format: "ollama/<model_name>" — requires google-adk[extensions] (litellm).

root_agent = Agent(
    name="local_document_extractor_coordinator",
    model=LiteLlm(model="ollama_chat/gemma4:latest"),
    description="Local agent that coordinates document extraction using Ollama.",
    instruction="""You are a dynamic document extraction coordinator.
Your goal is to help users extract structured data from documents.

When a user provides a document and a JSON schema definition (keys and descriptions),
you MUST call the extract_document_data_local tool with two arguments:
  - document_text: the full document text exactly as provided
  - schema_json_str: the JSON schema string exactly as provided

After the tool returns, inspect the result:
  - If status is "success", format the "data" object as pretty-printed JSON and return it.
  - If status is "error", report the error_message to the user so they can troubleshoot.

Do NOT attempt to extract data yourself. Always delegate to the tool.
""",
    tools=[extract_document_data_local],
)