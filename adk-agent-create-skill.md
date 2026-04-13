# Skill: adk-agent-create

## Description
Create production-ready Python ADK (Agent Development Kit) agents based on a use case description. This skill generates complete, runnable agent projects using Google's ADK framework with proper project structure, tools, sub-agents, configuration, and documentation.

## Trigger
WHEN: user asks to "create an agent", "build an ADK agent", "create a Python agent", "build an AI agent", "create agent for [use case]", "ADK agent for [domain]", "make me an agent that [does something]", "generate agent code", "scaffold an agent", "new ADK project".

## Instructions

When activated, follow these steps precisely to create a complete ADK Python agent project.

### Step 1: Analyze the Use Case

Read the user's request carefully and determine:

1. **Agent Name**: Derive a kebab-case project name and snake_case package name from the use case (e.g., "customer support" → project: `customer-support`, package: `customer_support`)
2. **Architecture Pattern**: Choose the best pattern:
   - **Single Agent**: Simple use cases with one responsibility and custom tools
   - **Multi-Agent Coordinator**: Multiple domains needing routing (e.g., customer service with billing + support + sales)
   - **Sequential Pipeline**: Step-by-step workflows (e.g., research → analyze → report)
   - **Parallel + Sequential**: Independent data gathering then synthesis (e.g., multi-source research)
   - **Loop Agent**: Iterative refinement (e.g., content drafting with review cycles)
   - **Agent-as-Tool (AgentTool)**: Main agent needs to call specialists as tools while maintaining control
   - **Hierarchical**: Complex systems with sub-agent directories
3. **Tools Needed**: Identify what custom tools the agent needs (API calls, database queries, file operations, calculations, etc.)
4. **Model**: Default to `gemini-2.0-flash` unless the user specifies otherwise or the task requires advanced reasoning (use `gemini-2.5-pro` for complex analysis)
5. **Special Features**: Determine if the agent needs:
   - Google Search (`google_search` tool)
   - RAG/retrieval (`VertexAiRagRetrieval`)
   - MCP integration (`MCPToolset`)
   - Structured output (`output_schema` with Pydantic)
   - Callbacks (guardrails, logging, state init)
   - State management (`output_key`, `ToolContext`)

### Step 2: Create Project Structure

Create files in this order under `python/agents/{project-name}/`:

#### 2.1 Create `pyproject.toml`

```toml
[project]
name = "{project-name}"
version = "0.1.0"
description = "{Brief description of the agent}"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "google-adk>=1.5.0",
    "google-genai>=1.14.0",
    # Add other dependencies based on tools needed
]

[build-system]
requires = ["setuptools>=75.0"]
build-backend = "setuptools.backends._legacy:_Backend"
```

#### 2.2 Create `.env.example`

```bash
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
# Add agent-specific env vars
```

#### 2.3 Create `{package_name}/__init__.py`

```python
from . import agent
```

#### 2.4 Create `{package_name}/agent.py`

This is the core file. Follow these rules strictly:

**CRITICAL RULES for `agent.py`:**

1. The file MUST export a variable named `root_agent` — this is what ADK CLI expects
2. Tools are plain Python functions with:
   - Full Google-style docstrings (description, Args, Returns)
   - Type hints on all parameters and return types
   - Return `dict` with `status` key for consistency
3. Use `Agent` (alias for `LlmAgent`) from `google.adk.agents`
4. Instructions should be clear, specific, and reference state variables with `{variable_name}` syntax
5. Sub-agents need a `description` field — the LLM uses this to decide routing
6. For tools that need session state access, add `tool_context: ToolContext` as a parameter (auto-injected)
7. Use `output_key` to save agent output to session state for downstream agents

**Template for Single Agent:**

```python
from google.adk.agents import Agent


def tool_function(param: str) -> dict:
    """Description of what the tool does.

    Args:
        param: Description of the parameter.

    Returns:
        dict: Status and result data.
    """
    # Implementation
    return {"status": "success", "result": "data"}


root_agent = Agent(
    name="{agent_name}",
    model="gemini-2.0-flash",
    description="{What this agent does - used for routing in multi-agent}",
    instruction="""{Detailed instruction for the agent behavior.
Reference state variables like {variable_name} if needed.}""",
    tools=[tool_function],
)
```

**Template for Multi-Agent Coordinator:**

```python
from google.adk.agents import Agent

specialist_a = Agent(
    name="specialist_a",
    model="gemini-2.0-flash",
    description="{When to route to this agent}",
    instruction="{Detailed specialist instructions}",
    tools=[],  # Specialist-specific tools
)

specialist_b = Agent(
    name="specialist_b",
    model="gemini-2.0-flash",
    description="{When to route to this agent}",
    instruction="{Detailed specialist instructions}",
    tools=[],
)

root_agent = Agent(
    name="{coordinator_name}",
    model="gemini-2.0-flash",
    description="{Coordinator description}",
    instruction="""{Routing logic instructions.
Explain when to transfer to each specialist.}""",
    sub_agents=[specialist_a, specialist_b],
)
```

**Template for Sequential Pipeline:**

```python
from google.adk.agents import SequentialAgent, Agent

step_one = Agent(
    name="step_one",
    model="gemini-2.0-flash",
    instruction="{Step 1 instructions}",
    output_key="step_one_result",
)

step_two = Agent(
    name="step_two",
    model="gemini-2.0-flash",
    instruction="{Step 2 instructions using {step_one_result}}",
    output_key="step_two_result",
)

step_three = Agent(
    name="step_three",
    model="gemini-2.0-flash",
    instruction="{Final step using {step_two_result}}",
)

root_agent = SequentialAgent(
    name="{pipeline_name}",
    description="{Pipeline description}",
    sub_agents=[step_one, step_two, step_three],
)
```

**Template for Parallel + Sequential:**

```python
from google.adk.agents import SequentialAgent, ParallelAgent, Agent

worker_a = Agent(
    name="worker_a",
    model="gemini-2.0-flash",
    instruction="{Worker A task}",
    output_key="result_a",
)

worker_b = Agent(
    name="worker_b",
    model="gemini-2.0-flash",
    instruction="{Worker B task}",
    output_key="result_b",
)

parallel_gather = ParallelAgent(
    name="parallel_gather",
    sub_agents=[worker_a, worker_b],
)

synthesizer = Agent(
    name="synthesizer",
    model="gemini-2.0-flash",
    instruction="{Combine {result_a} and {result_b} into final output}",
)

root_agent = SequentialAgent(
    name="{workflow_name}",
    description="{Workflow description}",
    sub_agents=[parallel_gather, synthesizer],
)
```

**Template for Loop Agent:**

```python
from google.adk.agents import LoopAgent, Agent
from google.adk.tools import exit_loop

drafter = Agent(
    name="drafter",
    model="gemini-2.0-flash",
    instruction="{Draft/improve based on {feedback}}",
    output_key="current_draft",
)

reviewer = Agent(
    name="reviewer",
    model="gemini-2.0-flash",
    instruction="""{Review {current_draft}.
If satisfactory, call exit_loop tool.
Otherwise provide feedback.}""",
    tools=[exit_loop],
    output_key="feedback",
)

root_agent = LoopAgent(
    name="{loop_name}",
    description="{Loop description}",
    max_iterations=5,
    sub_agents=[drafter, reviewer],
)
```

**Template for Agent-as-Tool:**

```python
from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

specialist = Agent(
    name="specialist",
    model="gemini-2.0-flash",
    instruction="{Specialist task instructions}",
)

root_agent = Agent(
    name="{coordinator_name}",
    model="gemini-2.0-flash",
    instruction="""{Instructions explaining when to use the specialist tool}""",
    tools=[AgentTool(agent=specialist)],
)
```

#### 2.5 Create Tools (if needed)

For complex agents, put tools in `{package_name}/tools/` directory:

```python
# {package_name}/tools/__init__.py
from .{tool_module} import tool_function_a, tool_function_b
```

```python
# {package_name}/tools/{tool_module}.py
from google.adk.tools import ToolContext


def tool_function_a(param: str, tool_context: ToolContext) -> dict:
    """Tool description.

    Args:
        param: Parameter description.
        tool_context: Automatically injected ADK tool context.

    Returns:
        dict: Result with status.
    """
    # Read/write state
    value = tool_context.state.get("key", "default")
    tool_context.state["new_key"] = "new_value"
    return {"status": "success", "data": value}
```

#### 2.6 Create Sub-Agents (if hierarchical)

For complex multi-agent systems, organize in `{package_name}/sub_agents/`:

```
{package_name}/sub_agents/
├── __init__.py
├── agent_a/
│   ├── __init__.py
│   └── agent.py
└── agent_b/
    ├── __init__.py
    └── agent.py
```

#### 2.7 Create `README.md`

Include:
- Agent name and description
- Architecture diagram (text-based)
- Prerequisites and setup instructions
- Environment variables needed
- How to run (`adk run`, `adk web`)
- Example interactions
- Deployment instructions

### Step 3: Validate the Generated Code

After creating all files, verify:

1. `root_agent` is defined and exported in `agent.py`
2. `__init__.py` imports the agent module: `from . import agent`
3. All tool functions have proper docstrings with Args and Returns
4. All type hints are present on tool parameters
5. `pyproject.toml` has `google-adk` as a dependency
6. `.env.example` has all required environment variables
7. Instructions are detailed and specific to the use case
8. Sub-agents have `description` fields for routing
9. `output_key` is used where state needs to flow between agents
10. No circular imports between modules

### Step 4: Provide Run Instructions

Tell the user how to run their agent:

```bash
cd python/agents/{project-name}

# Install dependencies
pip install -e .
# Or with poetry: poetry install
# Or with uv: uv sync

# Copy and configure environment
cp .env.example .env
# Edit .env with your actual values

# Run interactively
adk run {package_name}

# Run with web UI
adk web .

# Run as API server
adk api_server .
```

## Code Quality Rules

- Use `black` formatting (line length 88)
- Use `isort` for import sorting
- Follow `flake8` linting (max line length 88, ignore E501 for long strings in instructions)
- Use Google-style docstrings
- No unused imports
- Type hints on all function parameters and returns
- Constants in UPPER_CASE
- Agent names in snake_case
- Project directories in kebab-case
- Package directories in snake_case (matching agent name)

## Model Selection Guide

| Use Case | Recommended Model |
|---|---|
| General tasks, routing, simple tools | `gemini-2.0-flash` |
| Complex analysis, writing, reasoning | `gemini-2.5-pro` |
| Fast simple responses | `gemini-2.0-flash-lite` |
| Real-time audio conversation | `gemini-live-2.5-flash-preview-native-audio` |
| Code generation, technical tasks | `gemini-2.5-flash` |

## Common Patterns Reference

### Adding Google Search
```python
from google.adk.tools import google_search
# Add to tools=[google_search]
```

### Adding RAG Retrieval
```python
from google.adk.tools.retrieval.vertex_ai_rag_retrieval import VertexAiRagRetrieval
from vertexai.preview import rag
# Create VertexAiRagRetrieval tool and add to tools=[]
```

### Adding MCP Integration
```python
from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPConnectionParams
# Create MCPToolset and add to tools=[]
```

### Adding Structured Output
```python
from pydantic import BaseModel, Field
# Define Pydantic model and set output_schema=MyModel on agent
```

### Adding Callbacks
```python
from google.adk.agents.callback_context import CallbackContext
# Define callback functions and pass to agent constructor
```

### Adding State Initialization via Callback
```python
def init_state(callback_context: CallbackContext):
    if "key" not in callback_context.state:
        callback_context.state["key"] = "default_value"
# Pass as before_agent_callback=init_state
```

### Setting LLM Temperature
```python
from google.genai import types
# Set generate_content_config=types.GenerateContentConfig(temperature=0.1)