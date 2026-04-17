# Google Agent Development Kit (ADK) - Python Agent Development Reference

The Google Agent Development Kit (ADK) is an open-source, code-first Python framework for building, evaluating, and deploying AI agents. ADK provides a modular architecture optimized for Gemini models while remaining model-agnostic. Agents are built using Python classes and decorators, with tools defined as plain Python functions. The framework supports single agents, multi-agent orchestration (sequential, parallel, loop, hierarchical), session/state management, callbacks, MCP integration, and deployment to Google Cloud Run and Vertex AI Agent Engine.

This reference is derived from production-ready agent samples in the ADK Samples repository, covering patterns for customer service, data science, financial analysis, content creation, RAG, real-time conversation, workflow automation, and more. All agents follow a consistent project structure with `pyproject.toml` for dependency management, a package directory containing `agent.py` (with `root_agent`), optional `tools/` and `sub_agents/` directories, and `.env` for configuration.

## Project Structure and Setup

Every ADK Python agent follows a standard directory layout. The agent package must export a `root_agent` variable from `agent.py`. Tools are plain Python functions with docstrings. Sub-agents go in a `sub_agents/` directory.

```
my_agent/
├── pyproject.toml              # Dependencies (google-adk, etc.)
├── .env                        # Environment variables (API keys, project config)
├── .env.example                # Template for environment variables
├── README.md                   # Agent documentation
├── my_agent/                   # Python package (name matches agent)
│   ├── __init__.py             # Exports root_agent: from .agent import root_agent
│   ├── agent.py                # Main agent definition with root_agent
│   ├── tools/                  # Custom tool functions
│   │   ├── __init__.py
│   │   └── my_tools.py
│   ├── sub_agents/             # Sub-agent definitions (for multi-agent)
│   │   ├── __init__.py
│   │   └── specialist/
│   │       ├── __init__.py
│   │       └── agent.py
│   ├── entities/               # Data models and mock data
│   │   ├── __init__.py
│   │   └── models.py
│   └── prompts.py              # Instruction strings (optional)
├── tests/                      # Unit tests
│   └── test_agent.py
├── eval/                       # Evaluation test sets
│   ├── test_eval.py
│   └── conversation.test.json
└── deployment/                 # Deployment scripts for Vertex AI
    └── deploy.py
```

```toml
# pyproject.toml - typical dependencies
[project]
name = "my-agent"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "google-adk>=1.5.0",
    "google-genai>=1.14.0",
]

[build-system]
requires = ["setuptools>=75.0"]
build-backend = "setuptools.backends._legacy:_Backend"
```

```python
# my_agent/__init__.py
from . import agent
```

```bash
# .env - environment configuration
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
# Or for API key mode:
# GOOGLE_GENAI_USE_VERTEXAI=0
# GOOGLE_API_KEY=your-api-key
```

```bash
# Running the agent
cd my_agent
adk run my_agent         # CLI interactive mode
adk web .                # Web UI mode
adk api_server .         # REST API mode
```

## Single Agent with Custom Tools

The simplest pattern: one LLM agent with Python functions as tools. Tools are plain functions with type hints and docstrings. ADK auto-extracts the function signature for the LLM tool declaration.

```python
# agent.py
import datetime
from zoneinfo import ZoneInfo
from google.adk.agents import Agent


def get_weather(city: str) -> dict:
    """Retrieves the current weather report for a specified city.

    Args:
        city: The name of the city for the weather report.

    Returns:
        dict: status and result or error msg.
    """
    if city.lower() == "new york":
        return {
            "status": "success",
            "report": (
                "The weather in New York is sunny with a temperature of "
                "25 degrees Celsius (77 degrees Fahrenheit)."
            ),
        }
    else:
        return {
            "status": "error",
            "error_message": f"Weather information for '{city}' is not available.",
        }


def get_current_time(city: str) -> dict:
    """Returns the current time in a specified city.

    Args:
        city: The name of the city for the current time.

    Returns:
        dict: status and result or error msg.
    """
    if city.lower() == "new york":
        tz = ZoneInfo("America/New_York")
    else:
        return {
            "status": "error",
            "error_message": (
                f"Sorry, I don't have timezone information for {city}."
            ),
        }
    now = datetime.datetime.now(tz)
    report = (
        f'The current time in {city} is '
        f'{now.strftime("%Y-%m-%d %H:%M:%S %Z%z")}'
    )
    return {"status": "success", "report": report}


root_agent = Agent(
    name="weather_time_agent",
    model="gemini-3.1-flash-lite-preview",
    description="Agent to answer questions about the time and weather in a city.",
    instruction=(
        "You are a helpful agent who can answer user questions "
        "about the time and weather in a city."
    ),
    tools=[get_weather, get_current_time],
)
```

## Multi-Agent Coordinator Pattern (Agent Transfer)

A coordinator agent routes user requests to specialized sub-agents. The LLM decides which sub-agent to transfer to based on descriptions. Sub-agents are passed via `sub_agents` parameter. This is the most common multi-agent pattern in ADK samples.

```python
# agent.py
from google.adk.agents import Agent

# Specialized sub-agents
billing_agent = Agent(
    name="billing",
    model="gemini-3.1-flash-lite-preview",
    description="Handles billing inquiries, payment issues, and invoice questions.",
    instruction=(
        "You are a billing specialist. Help users with payment issues, "
        "invoices, refunds, and account balance questions."
    ),
)

support_agent = Agent(
    name="support",
    model="gemini-3.1-flash-lite-preview",
    description="Handles technical support, troubleshooting, and product issues.",
    instruction=(
        "You are a technical support specialist. Help users troubleshoot "
        "technical problems, resolve bugs, and answer product questions."
    ),
)

sales_agent = Agent(
    name="sales",
    model="gemini-3.1-flash-lite-preview",
    description="Handles product inquiries, pricing, and purchase assistance.",
    instruction=(
        "You are a sales specialist. Help users find the right product, "
        "understand pricing, and complete purchases."
    ),
)

# Coordinator routes to appropriate specialist
root_agent = Agent(
    name="customer_service_coordinator",
    model="gemini-3.1-flash-lite-preview",
    description="Main customer service coordinator.",
    instruction="""You are a customer service coordinator. Analyze the user's
request and transfer to the most appropriate specialist:
- billing: for payment, invoice, refund, account balance questions
- support: for technical problems, bugs, troubleshooting
- sales: for product info, pricing, purchasing

Always greet the user first, then transfer to the right agent.""",
    sub_agents=[billing_agent, support_agent, sales_agent],
)
```

## Sequential Agent Pipeline

SequentialAgent executes sub-agents in order. Each agent can save output to session state via `output_key`, and downstream agents read it via `{variable_name}` in their instructions.

```python
# agent.py
from google.adk.agents import SequentialAgent, Agent

# Step 1: Research and gather information
researcher = Agent(
    name="researcher",
    model="gemini-3.1-flash-lite-preview",
    instruction=(
        "Research the user's topic thoroughly. "
        "Provide detailed findings and key data points."
    ),
    output_key="research_findings",
)

# Step 2: Analyze the research
analyst = Agent(
    name="analyst",
    model="gemini-3.1-flash-lite-preview",
    instruction=(
        "Analyze the following research findings: {research_findings}. "
        "Identify key trends, insights, and actionable recommendations."
    ),
    output_key="analysis_report",
)

# Step 3: Write the final report
writer = Agent(
    name="writer",
    model="gemini-3.1-flash-lite-preview",
    instruction=(
        "Based on this analysis: {analysis_report}, write a professional "
        "report with executive summary, key findings, and recommendations."
    ),
)

root_agent = SequentialAgent(
    name="research_pipeline",
    description="Research, analyze, and report pipeline.",
    sub_agents=[researcher, analyst, writer],
)
```

## Parallel Agent Execution

ParallelAgent runs multiple sub-agents concurrently. Useful when gathering independent data from multiple sources simultaneously. Combine with SequentialAgent to process gathered results.

```python
# agent.py
from google.adk.agents import SequentialAgent, ParallelAgent, Agent

# Parallel research agents
market_researcher = Agent(
    name="market_researcher",
    model="gemini-3.1-flash-lite-preview",
    instruction="Research current market trends and competitive landscape.",
    output_key="market_data",
)

financial_researcher = Agent(
    name="financial_researcher",
    model="gemini-3.1-flash-lite-preview",
    instruction="Research financial metrics, revenue data, and growth trends.",
    output_key="financial_data",
)

sentiment_researcher = Agent(
    name="sentiment_researcher",
    model="gemini-3.1-flash-lite-preview",
    instruction="Research public sentiment, reviews, and social media trends.",
    output_key="sentiment_data",
)

# Run all research in parallel
parallel_research = ParallelAgent(
    name="parallel_research",
    description="Runs market, financial, and sentiment research concurrently.",
    sub_agents=[market_researcher, financial_researcher, sentiment_researcher],
)

# Synthesize all research results
synthesizer = Agent(
    name="synthesizer",
    model="gemini-3.1-flash-lite-preview",
    instruction="""Synthesize these research findings into a comprehensive report:
- Market Data: {market_data}
- Financial Data: {financial_data}
- Sentiment Data: {sentiment_data}

Provide a unified analysis with cross-cutting insights.""",
)

root_agent = SequentialAgent(
    name="comprehensive_research",
    description="Parallel research followed by synthesis.",
    sub_agents=[parallel_research, synthesizer],
)
```

## Loop Agent for Iterative Refinement

LoopAgent repeatedly executes sub-agents until an exit condition or `max_iterations`. Use `exit_loop` tool or `EventActions(escalate=True)` to break out.

```python
# agent.py
from google.adk.agents import LoopAgent, Agent
from google.adk.tools import exit_loop

# Draft content
drafter = Agent(
    name="drafter",
    model="gemini-3.1-flash-lite-preview",
    instruction=(
        "Write or improve content based on the original request and any "
        "feedback: {feedback}. Save the current draft."
    ),
    output_key="current_draft",
)

# Review and decide whether to iterate
reviewer = Agent(
    name="reviewer",
    model="gemini-3.1-flash-lite-preview",
    instruction="""Review this draft: {current_draft}

If the draft meets quality standards (clear, accurate, well-structured),
call the exit_loop tool to finish.

Otherwise, provide specific, actionable feedback for improvement.""",
    tools=[exit_loop],
    output_key="feedback",
)

root_agent = LoopAgent(
    name="content_refinement_loop",
    description="Iteratively refines content until quality standards are met.",
    max_iterations=5,
    sub_agents=[drafter, reviewer],
)
```

## Agent-as-Tool Pattern (AgentTool)

AgentTool lets one agent invoke another as a tool, maintaining control flow. The calling agent sends a request, gets the result back, and can continue processing. Different from sub-agent transfer where control passes entirely.

```python
# agent.py
from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import google_search

# Specialist agents used as tools
web_researcher = Agent(
    name="web_researcher",
    model="gemini-3.1-flash-lite-preview",
    instruction="Search the web and provide detailed findings on the topic.",
    tools=[google_search],
    output_key="web_findings",
)

data_analyst = Agent(
    name="data_analyst",
    model="gemini-3.1-flash-lite-preview",
    instruction=(
        "Analyze the provided data and generate insights with "
        "statistics and visualizations descriptions."
    ),
)

# Main agent uses specialists as tools
root_agent = Agent(
    name="research_coordinator",
    model="gemini-3.1-flash-lite-preview",
    instruction="""You are a research coordinator. Use these tools:
- web_researcher: for finding information online
- data_analyst: for analyzing data and generating insights

Gather information first, then analyze it to provide comprehensive answers.""",
    tools=[
        AgentTool(agent=web_researcher),
        AgentTool(agent=data_analyst),
    ],
)
```

## Hierarchical Multi-Agent with Sub-Agent Directories

For complex agents, organize sub-agents in separate files/directories. Each sub-agent has its own `agent.py`. The root agent imports and composes them.

```python
# sub_agents/research_agent/agent.py
from google.adk.agents import Agent
from google.adk.tools import google_search

research_agent = Agent(
    name="research_agent",
    model="gemini-3.1-flash-lite-preview",
    description="Conducts web research on topics.",
    instruction=(
        "You are a research specialist. Use Google Search to find "
        "relevant, accurate information on the given topic. "
        "Provide well-sourced findings."
    ),
    tools=[google_search],
)
```

```python
# sub_agents/analyst_agent/agent.py
from google.adk.agents import Agent

analyst_agent = Agent(
    name="analyst_agent",
    model="gemini-3.1-flash-lite-preview",
    description="Analyzes research data and provides insights.",
    instruction=(
        "You are a data analyst. Analyze the information provided, "
        "identify patterns and trends, and provide actionable insights "
        "with supporting evidence."
    ),
)
```

```python
# sub_agents/__init__.py
from .research_agent.agent import research_agent
from .analyst_agent.agent import analyst_agent
```

```python
# agent.py
from google.adk.agents import Agent
from .sub_agents import research_agent, analyst_agent

root_agent = Agent(
    name="hierarchical_coordinator",
    model="gemini-3.1-flash-lite-preview",
    description="Coordinates research and analysis workflows.",
    instruction="""You are a project coordinator managing a team:
- research_agent: for gathering information via web search
- analyst_agent: for analyzing data and generating insights

Delegate tasks to the appropriate team member based on the user's request.
For complex requests, first delegate to research, then to analysis.""",
    sub_agents=[research_agent, analyst_agent],
)
```

## Custom Tools with ToolContext for State Access

Tools can access and modify session state via `ToolContext`. The `tool_context` parameter is automatically injected by ADK. This enables tools to read/write shared state, access artifacts, and interact with the session.

```python
# tools/customer_tools.py
from google.adk.tools import ToolContext


def lookup_customer(customer_id: str, tool_context: ToolContext) -> dict:
    """Look up customer information by ID.

    Args:
        customer_id: The unique customer identifier.
        tool_context: Automatically injected ADK tool context.

    Returns:
        dict: Customer information or error.
    """
    # Read from session state
    customers_db = tool_context.state.get("customers_db", {})

    if customer_id in customers_db:
        customer = customers_db[customer_id]
        # Write to session state for downstream use
        tool_context.state["current_customer"] = customer
        return {"status": "success", "customer": customer}
    else:
        return {
            "status": "error",
            "error_message": f"Customer {customer_id} not found.",
        }


def update_customer_preference(
    customer_id: str,
    preference_key: str,
    preference_value: str,
    tool_context: ToolContext,
) -> dict:
    """Update a customer's preference.

    Args:
        customer_id: The unique customer identifier.
        preference_key: The preference to update.
        preference_value: The new value for the preference.
        tool_context: Automatically injected ADK tool context.

    Returns:
        dict: Update confirmation or error.
    """
    customers_db = tool_context.state.get("customers_db", {})
    if customer_id in customers_db:
        if "preferences" not in customers_db[customer_id]:
            customers_db[customer_id]["preferences"] = {}
        customers_db[customer_id]["preferences"][preference_key] = (
            preference_value
        )
        tool_context.state["customers_db"] = customers_db
        return {"status": "success", "message": "Preference updated."}
    return {"status": "error", "error_message": "Customer not found."}
```

```python
# agent.py
from google.adk.agents import Agent
from .tools.customer_tools import lookup_customer, update_customer_preference

root_agent = Agent(
    name="customer_assistant",
    model="gemini-3.1-flash-lite-preview",
    instruction="""You are a customer service assistant.
Use lookup_customer to find customer information.
Use update_customer_preference to modify customer preferences.
The current customer context is: {current_customer}""",
    tools=[lookup_customer, update_customer_preference],
)
```

## Callbacks for Agent Lifecycle Control

Callbacks intercept agent execution at various points: before/after agent runs, before/after model calls, and before/after tool calls. Return `None` to continue normally, or return a value to short-circuit.

```python
# agent.py
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.adk.tools import BaseTool
from google.genai import types
from typing import Any


def before_agent_callback(callback_context: CallbackContext):
    """Called before the agent starts processing. Return Content to skip."""
    # Initialize state
    if "request_count" not in callback_context.state:
        callback_context.state["request_count"] = 0
    callback_context.state["request_count"] += 1

    # Rate limiting example
    if callback_context.state["request_count"] > 100:
        return types.Content(
            role="model",
            parts=[types.Part(text="Rate limit exceeded. Please try later.")],
        )
    return None  # Continue normally


def after_agent_callback(callback_context: CallbackContext):
    """Called after the agent completes. Return Content to append."""
    callback_context.state["last_completed"] = True
    return None


def before_model_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> LlmResponse | None:
    """Called before LLM call. Return LlmResponse to skip the LLM."""
    # Content filtering / guardrails
    last_message = llm_request.contents[-1].parts[0].text
    if "forbidden" in last_message.lower():
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part(text="I cannot process that request.")],
            )
        )
    return None


def after_model_callback(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> LlmResponse | None:
    """Called after LLM response. Return LlmResponse to replace it."""
    return None  # Use original response


def before_tool_callback(
    callback_context: CallbackContext,
    tool: BaseTool,
    args: dict[str, Any],
) -> dict[str, Any] | None:
    """Called before tool execution. Return dict to skip tool."""
    print(f"Tool '{tool.name}' called with: {args}")
    return None  # Execute tool normally


def after_tool_callback(
    callback_context: CallbackContext,
    tool: BaseTool,
    args: dict[str, Any],
    tool_response: dict[str, Any],
) -> dict[str, Any] | None:
    """Called after tool execution. Return dict to replace result."""
    print(f"Tool '{tool.name}' returned: {tool_response}")
    return None


root_agent = Agent(
    name="guarded_agent",
    model="gemini-3.1-flash-lite-preview",
    instruction="You are a helpful assistant with safety guardrails.",
    before_agent_callback=before_agent_callback,
    after_agent_callback=after_agent_callback,
    before_model_callback=before_model_callback,
    after_model_callback=after_model_callback,
    before_tool_callback=before_tool_callback,
    after_tool_callback=after_tool_callback,
)
```

## RAG Agent with Vertex AI Retrieval

Use `VertexAiRagRetrieval` to connect agents to a Vertex AI RAG corpus for knowledge-grounded responses.

```python
# agent.py
import os
from google.adk.agents import Agent
from google.adk.tools.retrieval.vertex_ai_rag_retrieval import (
    VertexAiRagRetrieval,
)
from vertexai.preview import rag

rag_retrieval_tool = VertexAiRagRetrieval(
    name="retrieve_documentation",
    description=(
        "Use this tool to retrieve relevant documentation and "
        "reference materials from the knowledge base."
    ),
    rag_resources=[
        rag.RagResource(
            rag_corpus=os.environ.get("RAG_CORPUS"),
        )
    ],
    similarity_top_k=10,
    vector_distance_threshold=0.6,
)

root_agent = Agent(
    model="gemini-3.1-flash-lite-preview-001",
    name="rag_assistant",
    instruction="""You are a documentation assistant powered by a knowledge base.
Use the retrieve_documentation tool to find relevant information before answering.
Always cite your sources and indicate when information is not available in the knowledge base.""",
    tools=[rag_retrieval_tool],
)
```

## MCP (Model Context Protocol) Integration

Connect to external MCP servers to use their tools. Supports both HTTP (StreamableHTTP) and stdio connection types.

```python
# agent.py
import os
from google.adk.agents import Agent
from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPConnectionParams

root_agent = Agent(
    model="gemini-3.1-flash-lite-preview",
    name="mcp_agent",
    description="Agent that uses external MCP tools.",
    instruction="""You are a helpful assistant with access to external tools
via MCP servers. Use the available tools to help answer user questions.""",
    tools=[
        MCPToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=os.getenv("MCP_SERVER_URL", "http://localhost:8080/mcp"),
            ),
        ),
    ],
)
```

```python
# agent.py - stdio MCP connection
import os
from google.adk.agents import Agent
from google.adk.tools.mcp_tool import MCPToolset, StdioConnectionParams
from mcp import StdioServerParameters

root_agent = Agent(
    model="gemini-3.1-flash-lite-preview",
    name="mcp_stdio_agent",
    instruction="You are a helpful assistant using MCP tools.",
    tools=[
        MCPToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="npx",
                    args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                ),
            ),
        ),
    ],
)
```

## Structured Output with Pydantic Schema

Define output schemas using Pydantic models to enforce structured LLM responses.

```python
# agent.py
from google.adk.agents import Agent
from pydantic import BaseModel, Field


class AnalysisResult(BaseModel):
    summary: str = Field(description="Brief summary of the analysis")
    key_findings: list[str] = Field(description="List of key findings")
    sentiment: str = Field(description="Overall sentiment: positive/negative/neutral")
    confidence: float = Field(description="Confidence score from 0.0 to 1.0")
    recommendations: list[str] = Field(description="Actionable recommendations")


root_agent = Agent(
    name="structured_analyst",
    model="gemini-3.1-flash-lite-preview",
    instruction="""Analyze the user's input and provide a structured analysis.
Include a summary, key findings, sentiment assessment, confidence score,
and actionable recommendations.""",
    output_schema=AnalysisResult,
    output_key="analysis_result",
)
```

## LLM Configuration (Temperature, Safety Settings)

Fine-tune LLM behavior with `GenerateContentConfig` for temperature, token limits, and safety settings.

```python
# agent.py
from google.adk.agents import Agent
from google.genai import types

root_agent = Agent(
    name="precise_agent",
    model="gemini-3.1-flash-lite-preview",
    instruction="You are a precise, factual assistant.",
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,
        max_output_tokens=1000,
        top_p=0.8,
        top_k=40,
        safety_settings=[
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            ),
        ],
    ),
)
```

## Running Agents Programmatically with Runner

Use `Runner` and `InMemorySessionService` to execute agents in Python code, outside the CLI.

```python
from google.genai import types
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

APP_NAME = "my_app"
USER_ID = "user_123"
SESSION_ID = "session_456"

agent = Agent(
    name="my_agent",
    model="gemini-3.1-flash-lite-preview",
    instruction="You are a helpful assistant.",
    tools=[],
)

session_service = InMemorySessionService()
session = session_service.create_session(
    app_name=APP_NAME,
    user_id=USER_ID,
    session_id=SESSION_ID,
)

runner = Runner(
    agent=agent,
    app_name=APP_NAME,
    session_service=session_service,
)


def call_agent(query: str) -> str:
    """Send a query to the agent and return the final response."""
    content = types.Content(
        role="user",
        parts=[types.Part(text=query)],
    )
    events = runner.run(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=content,
    )
    for event in events:
        if event.is_final_response() and event.content:
            return event.content.parts[0].text
    return ""


response = call_agent("Hello, what can you help me with?")
print(response)
```

## State Management and Dynamic Instructions

Agent instructions can reference session state variables with `{variable_name}`. Tools and callbacks can read/write state. The `output_key` parameter saves agent output to state.

```python
# agent.py
from google.adk.agents import Agent, SequentialAgent


def get_user_profile(user_id: str) -> dict:
    """Fetch user profile information.

    Args:
        user_id: The user's unique identifier.

    Returns:
        dict: User profile data.
    """
    return {
        "name": "Alice",
        "role": "Premium Member",
        "interests": ["technology", "finance", "travel"],
    }


profile_fetcher = Agent(
    name="profile_fetcher",
    model="gemini-3.1-flash-lite-preview",
    instruction="Use get_user_profile to fetch the user's profile. Pass 'current_user' as user_id.",
    tools=[get_user_profile],
    output_key="user_profile",
)

personalized_responder = Agent(
    name="personalized_responder",
    model="gemini-3.1-flash-lite-preview",
    instruction="""You are a personalized assistant.
The user's profile is: {user_profile}
Tailor your responses based on their role, interests, and preferences.""",
)

root_agent = SequentialAgent(
    name="personalized_pipeline",
    sub_agents=[profile_fetcher, personalized_responder],
)
```

## Google Search Integration

Use the built-in `google_search` tool for web search capabilities.

```python
# agent.py
from google.adk.agents import Agent
from google.adk.tools import google_search

root_agent = Agent(
    name="search_agent",
    model="gemini-3.1-flash-lite-preview",
    description="An assistant that can search the web.",
    instruction="""You are a helpful research assistant. Use Google Search to find
current, accurate information to answer user questions.
Always provide sources for your information.""",
    tools=[google_search],
)
```

## Real-Time Conversational Agent

Use live/streaming models for real-time audio and conversational interactions.

```python
# agent.py
from google.adk.agents import Agent

root_agent = Agent(
    name="realtime_assistant",
    model="gemini-live-2.5-flash-preview-native-audio",
    description="A helpful AI assistant with real-time audio capabilities.",
    instruction="""You are a real-time conversational assistant.
Respond naturally to user queries with appropriate tone and context.
Handle audio input and output for seamless voice interactions.""",
)
```

## Deployment to Cloud Run

Deploy agents to Google Cloud Run for production use.

```bash
# Set environment
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"
export SERVICE_NAME="my-agent-service"

# Deploy with ADK CLI
adk deploy cloud_run \
    --project=$GOOGLE_CLOUD_PROJECT \
    --region=$GOOGLE_CLOUD_LOCATION \
    --service_name=$SERVICE_NAME \
    --with_ui \
    ./my_agent

# Test deployed service
export APP_URL="https://your-service-url.run.app"
export TOKEN=$(gcloud auth print-identity-token)

curl -X POST -H "Authorization: Bearer $TOKEN" \
    "$APP_URL/apps/my_agent/users/u_123/sessions/s_456" \
    -H "Content-Type: application/json" -d '{}'

curl -X POST -H "Authorization: Bearer $TOKEN" \
    "$APP_URL/run" \
    -H "Content-Type: application/json" \
    -d '{
        "appName": "my_agent",
        "userId": "u_123",
        "sessionId": "s_456",
        "newMessage": {
            "role": "user",
            "parts": [{"text": "Hello!"}]
        }
    }'
```

## Deployment to Vertex AI Agent Engine

Deploy agents to Vertex AI for enterprise-grade production.

```bash
# Build the wheel
poetry build --format=wheel --out-dir deployment
# or: uv build --wheel --out-dir deployment

# Deploy
cd deployment/
python deploy.py --create

# Test
python test_deployment.py --resource_id=$RESOURCE_ID --user_id=$USER_ID

# Delete
python deploy.py --delete --resource_id=$RESOURCE_ID
```

## Evaluation and Testing

ADK provides evaluation tools for testing agent behavior against expected outcomes.

```bash
# Run evaluations
adk eval my_agent eval/conversation.test.json --print_detailed_results

# Run unit tests
pytest tests/ -v
```

```json
{
    "test_cases": [
        {
            "user_query": "What is the weather in New York?",
            "expected_tools": ["get_weather"],
            "expected_tool_args": {"city": "New York"},
            "reference_answer": "The weather in New York is sunny with a temperature of 25 degrees Celsius."
        }
    ]
}
```

## Summary

ADK Python agents follow consistent patterns: a root agent defined in `agent.py`, tools as plain Python functions with docstrings, and multi-agent orchestration via sub-agents (transfer), SequentialAgent (pipeline), ParallelAgent (concurrent), LoopAgent (iterative), or AgentTool (agent-as-tool). Session state flows between agents through `output_key` and `{variable_name}` substitution in instructions. Callbacks enable lifecycle interception for guardrails, logging, and caching. The framework integrates with Google Search, Vertex AI RAG, MCP servers, and BigQuery. Deployment targets include local dev (CLI/web UI), Cloud Run, and Vertex AI Agent Engine. All agents use `pyproject.toml` for dependencies and `.env` for configuration.