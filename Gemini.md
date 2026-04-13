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
    model="gemini-2.0-flash",
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
    model="gemini-2.0-flash",
    description="Handles billing inquiries, payment issues, and invoice questions.",
    instruction=(
        "You are a billing specialist. Help users with payment issues, "
        "invoices, refunds, and account balance questions."
    ),
)

support_agent = Agent(
    name="support",
    model="gemini-2.0-flash",
    description="Handles technical support, troubleshooting, and product issues.",
    instruction=(
        "You are a technical support specialist. Help users troubleshoot "
        "technical problems, resolve bugs, and answer product questions."
    ),
)

sales_agent = Agent(
    name="sales",
    model="gemini-2.0-flash",
    description="Handles product inquiries, pricing, and purchase assistance.",
    instruction=(
        "You are a sales specialist. Help users find the right product, "
        "understand pricing, and complete purchases."
    ),
)

# Coordinator routes to appropriate specialist
root_agent = Agent(
    name="customer_service_coordinator",
    model="gemini-2.0-flash",
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
    model="gemini-2.0-flash",
    instruction=(
        "Research the user's topic thoroughly. "
        "Provide detailed findings and key data points."
    ),
    output_key="research_findings",
)

# Step 2: Analyze the research
analyst = Agent(
    name="analyst",
    model="gemini-2.0-flash",
    instruction=(
        "Analyze the following research findings: {research_findings}. "
        "Identify key trends, insights, and actionable recommendations."
    ),
    output_key="analysis_report",
)

# Step 3: Write the final report
writer = Agent(
    name="writer",
    model="gemini-2.0-flash",
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
    model="gemini-2.0-flash",
    instruction="Research current market trends and competitive landscape.",
    output_key="market_data",
)

financial_researcher = Agent(
    name="financial_researcher",
    model="gemini-2.0-flash",
    instruction="Research financial metrics, revenue data, and growth trends.",
    output_key="financial_data",
)

sentiment_researcher = Agent(
    name="sentiment_researcher",
    model="gemini-2.0-flash",
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
    model="gemini-2.0-flash",
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
    model="gemini-2.0-flash",
    instruction=(
        "Write or improve content based on the original request and any "
        "feedback: {feedback}. Save the current draft."
    ),
    output_key="current_draft",
)

# Review and decide whether to iterate
reviewer = Agent(
    name="reviewer",
    model="gemini-2.0-flash",
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

