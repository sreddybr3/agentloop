# Google Agent Development Kit (ADK)

Google Agent Development Kit (ADK) is an open-source, code-first Python framework for building, evaluating, and deploying sophisticated AI agents. It provides a flexible and modular architecture that applies software development principles to AI agent creation, enabling developers to build everything from simple task-oriented agents to complex multi-agent systems. While optimized for Gemini models, ADK is model-agnostic and deployment-agnostic, allowing integration with various LLM providers and deployment targets including Cloud Run and Vertex AI Agent Engine.

The framework centers around a hierarchical agent architecture where agents can be composed into trees with specialized sub-agents. ADK provides rich tooling capabilities including built-in tools (Google Search, URL context, memory tools), custom function tools, MCP (Model Context Protocol) integration, and OpenAPI-based toolsets. The framework includes comprehensive session management for stateful conversations, memory services for long-term context, artifact handling for file storage, and evaluation tools for testing agent behavior. The built-in CLI and web-based development UI enable rapid prototyping, debugging, and deployment.

## LlmAgent - Core LLM-Based Agent

The `LlmAgent` (aliased as `Agent`) is the primary building block for creating AI agents powered by large language models. It handles model interactions, tool execution, and supports dynamic instructions with state variable substitution.

```python
from google.adk.agents import Agent, LlmAgent
from google.adk.tools import google_search, FunctionTool

# Simple agent with built-in Google Search tool
search_agent = Agent(
    name="search_assistant",
    model="gemini-3.1-flash-lite-preview",
    instruction="You are a helpful assistant. Answer user questions using Google Search when needed.",
    description="An assistant that can search the web.",
    tools=[google_search]
)

# Agent with custom function tool
def get_weather(city: str) -> dict:
    """Get weather information for a city.

    Args:
        city: The name of the city to get weather for.

    Returns:
        Weather information dictionary.
    """
    return {"city": city, "temperature": "72F", "condition": "Sunny"}

weather_agent = LlmAgent(
    name="weather_bot",
    model="gemini-3.1-flash-lite-preview",
    instruction="Help users check the weather. Use the get_weather tool when asked about weather.",
    tools=[get_weather],
    output_key="last_weather_response"  # Store output in session state
)

# Agent with callbacks for custom behavior
async def log_before_model(callback_context, llm_request):
    """Log requests before sending to model."""
    print(f"Sending request with {len(llm_request.contents)} messages")
    return None  # Return None to continue, or LlmResponse to skip model call

async def validate_after_model(callback_context, llm_response):
    """Validate or modify model responses."""
    # Could filter or transform the response
    return None  # Return None to use original response

validated_agent = Agent(
    name="validated_agent",
    model="gemini-3.1-flash-lite-preview",
    instruction="You are a careful assistant that validates all responses.",
    before_model_callback=log_before_model,
    after_model_callback=validate_after_model,
    disallow_transfer_to_parent=True,  # Prevent transferring back to parent
    include_contents='default'  # 'default' or 'none' for history control
)
```

## Multi-Agent Systems with Sub-Agents

ADK supports hierarchical multi-agent systems where a coordinator agent can delegate tasks to specialized sub-agents. The framework automatically handles agent transfers based on descriptions and model decisions.

```python
from google.adk.agents import Agent, LlmAgent

# Define specialized sub-agents
greeter_agent = LlmAgent(
    name="greeter",
    model="gemini-3.1-flash-lite-preview",
    instruction="You handle greetings and introductions warmly.",
    description="Handles greetings and welcomes users."
)

task_agent = LlmAgent(
    name="task_executor",
    model="gemini-3.1-flash-lite-preview",
    instruction="You help users complete specific tasks efficiently.",
    description="Handles task execution and follow-through."
)

researcher_agent = LlmAgent(
    name="researcher",
    model="gemini-3.1-flash-lite-preview",
    instruction="You research topics and provide detailed information.",
    description="Conducts research and provides information."
)

# Create coordinator with sub-agents
coordinator = Agent(
    name="coordinator",
    model="gemini-3.1-flash-lite-preview",
    description="I coordinate between greeting, research, and task execution.",
    instruction="""You are a coordinator agent. Analyze user requests and delegate to:
    - greeter: for greetings and introductions
    - researcher: for information lookup and research
    - task_executor: for completing specific tasks
    Transfer control appropriately based on user needs.""",
    sub_agents=[greeter_agent, task_agent, researcher_agent]
)

# Clone an agent with modifications
cloned_greeter = greeter_agent.clone(update={
    "name": "formal_greeter",
    "instruction": "You handle formal business greetings professionally."
})
```

## SequentialAgent - Pipeline Execution

`SequentialAgent` executes its sub-agents in sequence, useful for creating processing pipelines where each agent builds on the previous one's work.

```python
from google.adk.agents import SequentialAgent, LlmAgent

# Define pipeline stages
analyzer = LlmAgent(
    name="analyzer",
    model="gemini-3.1-flash-lite-preview",
    instruction="Analyze the user's input and identify key requirements. Store analysis in output_key.",
    output_key="analysis_result"
)

planner = LlmAgent(
    name="planner",
    model="gemini-3.1-flash-lite-preview",
    instruction="Based on {analysis_result}, create a detailed action plan.",
    output_key="action_plan"
)

executor = LlmAgent(
    name="executor",
    model="gemini-3.1-flash-lite-preview",
    instruction="Execute the following plan: {action_plan}. Provide final results."
)

# Create sequential pipeline
pipeline_agent = SequentialAgent(
    name="processing_pipeline",
    description="Processes requests through analysis, planning, and execution stages.",
    sub_agents=[analyzer, planner, executor]
)
```

## ParallelAgent - Concurrent Execution

`ParallelAgent` runs all its sub-agents concurrently and merges their outputs, ideal for gathering information from multiple sources simultaneously.

```python
from google.adk.agents import ParallelAgent, LlmAgent

# Define parallel workers
news_agent = LlmAgent(
    name="news_researcher",
    model="gemini-3.1-flash-lite-preview",
    instruction="Research recent news on the topic.",
    output_key="news_findings"
)

academic_agent = LlmAgent(
    name="academic_researcher",
    model="gemini-3.1-flash-lite-preview",
    instruction="Find academic papers and research on the topic.",
    output_key="academic_findings"
)

social_agent = LlmAgent(
    name="social_researcher",
    model="gemini-3.1-flash-lite-preview",
    instruction="Research social media trends and discussions on the topic.",
    output_key="social_findings"
)

# Run all researchers in parallel
parallel_research = ParallelAgent(
    name="parallel_research",
    description="Runs multiple research streams concurrently.",
    sub_agents=[news_agent, academic_agent, social_agent]
)
```

## LoopAgent - Iterative Processing

`LoopAgent` repeatedly executes its sub-agents until an exit condition is met (via escalate action or max iterations).

```python
from google.adk.agents import LoopAgent, LlmAgent
from google.adk.tools import exit_loop

# Define iterative refinement agents
drafter = LlmAgent(
    name="drafter",
    model="gemini-3.1-flash-lite-preview",
    instruction="Draft or improve the current document based on feedback: {feedback}",
    output_key="current_draft"
)

reviewer = LlmAgent(
    name="reviewer",
    model="gemini-3.1-flash-lite-preview",
    instruction="""Review the draft: {current_draft}
    If satisfactory, use exit_loop tool.
    Otherwise, provide specific feedback for improvement.""",
    tools=[exit_loop],  # Allows breaking out of the loop
    output_key="feedback"
)

# Create iterative refinement loop
refinement_loop = LoopAgent(
    name="refinement_loop",
    description="Iteratively refines content until quality standards are met.",
    max_iterations=5,  # Safety limit
    sub_agents=[drafter, reviewer]
)
```

## FunctionTool - Custom Python Functions as Tools

`FunctionTool` wraps Python functions as tools that agents can call. It automatically extracts function signatures and docstrings to create tool declarations.

```python
from google.adk.agents import Agent
from google.adk.tools import FunctionTool, ToolContext
from pydantic import BaseModel
from typing import Optional

# Simple function tool
def calculate_price(base_price: float, quantity: int, discount_percent: float = 0) -> dict:
    """Calculate total price with optional discount.

    Args:
        base_price: The base price per unit.
        quantity: Number of units to purchase.
        discount_percent: Optional discount percentage (0-100).

    Returns:
        Dictionary with calculation breakdown and total.
    """
    subtotal = base_price * quantity
    discount = subtotal * (discount_percent / 100)
    total = subtotal - discount
    return {
        "subtotal": subtotal,
        "discount": discount,
        "total": total
    }

# Tool with context access for session state
async def save_note(content: str, tool_context: ToolContext) -> str:
    """Save a note to the session state.

    Args:
        content: The note content to save.
        tool_context: Automatically injected context for state access.

    Returns:
        Confirmation message.
    """
    notes = tool_context.state.get("notes", [])
    notes.append(content)
    tool_context.state["notes"] = notes
    return f"Note saved. Total notes: {len(notes)}"

# Tool with Pydantic model input
class OrderRequest(BaseModel):
    product_id: str
    quantity: int
    shipping_address: str

def place_order(order: OrderRequest) -> dict:
    """Place a product order.

    Args:
        order: Order details including product, quantity, and shipping info.

    Returns:
        Order confirmation with tracking number.
    """
    return {
        "order_id": f"ORD-{order.product_id}-001",
        "status": "confirmed",
        "estimated_delivery": "3-5 business days"
    }

# Tool requiring user confirmation
def delete_file(filename: str) -> str:
    """Delete a file from the system.

    Args:
        filename: Name of the file to delete.

    Returns:
        Deletion confirmation.
    """
    return f"File {filename} deleted successfully."

delete_tool = FunctionTool(
    func=delete_file,
    require_confirmation=True  # Requires user approval before execution
)

# Use tools in an agent
agent = Agent(
    name="tools_demo",
    model="gemini-3.1-flash-lite-preview",
    instruction="Help users with calculations, notes, orders, and file management.",
    tools=[calculate_price, save_note, place_order, delete_tool]
)
```

## MCPToolset - Model Context Protocol Integration

`MCPToolset` connects to MCP servers to expose their tools to ADK agents, enabling integration with external tool providers.

```python
from google.adk.agents import Agent
from google.adk.tools import MCPToolset
from mcp import StdioServerParameters

# Connect to a local filesystem MCP server
filesystem_toolset = MCPToolset(
    connection_params=StdioServerParameters(
        command='npx',
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    ),
    tool_filter=['read_file', 'list_directory', 'write_file'],  # Optional: filter specific tools
    tool_name_prefix="fs_"  # Optional: prefix tool names
)

# Connect to a remote SSE-based MCP server
from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams

remote_toolset = MCPToolset(
    connection_params=SseConnectionParams(
        url="https://my-mcp-server.example.com/sse",
        headers={"Authorization": "Bearer token123"}
    ),
    require_confirmation=True  # Require confirmation for all tools
)

# Use MCP toolsets in an agent
file_agent = Agent(
    name="file_manager",
    model="gemini-3.1-flash-lite-preview",
    instruction="Help users manage files using the available filesystem tools.",
    tools=[filesystem_toolset]
)

# McpToolset with custom header provider for dynamic auth
def get_auth_headers(readonly_context):
    """Provide dynamic authentication headers."""
    user_token = readonly_context.state.get("user_token", "")
    return {"Authorization": f"Bearer {user_token}"}

dynamic_auth_toolset = MCPToolset(
    connection_params=SseConnectionParams(url="https://api.example.com/mcp"),
    header_provider=get_auth_headers
)
```

## App - Application Container

The `App` class is the top-level container for an agentic application, managing the root agent and application-wide configurations.

```python
from google.adk.apps import App, ResumabilityConfig
from google.adk.agents import Agent

# Create the root agent
root_agent = Agent(
    name="assistant",
    model="gemini-3.1-flash-lite-preview",
    instruction="You are a helpful AI assistant."
)

# Create the application
app = App(
    name="my_assistant_app",
    root_agent=root_agent,
    resumability_config=ResumabilityConfig(
        is_resumable=True  # Enable session resumption for long-running tasks
    )
)

# App with event compaction for long conversations
from google.adk.apps.app import EventsCompactionConfig
from google.adk.apps.llm_event_summarizer import LlmEventSummarizer

compaction_app = App(
    name="long_conversation_app",
    root_agent=root_agent,
    events_compaction_config=EventsCompactionConfig(
        summarizer=LlmEventSummarizer(model="gemini-3.1-flash-lite-preview"),
        compaction_interval=10,  # Compact every 10 invocations
        overlap_size=2,  # Keep 2 invocations of context overlap
        token_threshold=50000,  # Trigger compaction when tokens exceed threshold
        event_retention_size=5  # Keep last 5 events uncompacted
    )
)
```

## Session Management

Sessions track conversations between users and agents, maintaining state and event history across interactions.

```python
from google.adk.sessions import InMemorySessionService, Session
from google.adk.agents import Agent
import asyncio

# Create session service
session_service = InMemorySessionService()

# Create a new session
async def create_and_use_session():
    session = await session_service.create_session(
        app_name="my_app",
        user_id="user123",
        state={"user_name": "Alice", "preferences": {"theme": "dark"}},
        session_id="optional-custom-id"  # Optional: auto-generated if not provided
    )

    print(f"Created session: {session.id}")
    print(f"Session state: {session.state}")

    # Retrieve an existing session
    retrieved_session = await session_service.get_session(
        app_name="my_app",
        user_id="user123",
        session_id=session.id
    )

    # List all sessions for a user
    sessions_response = await session_service.list_sessions(
        app_name="my_app",
        user_id="user123"
    )

    # Delete a session
    await session_service.delete_session(
        app_name="my_app",
        user_id="user123",
        session_id=session.id
    )

asyncio.run(create_and_use_session())

# Using DatabaseSessionService for persistence (requires sqlalchemy)
from google.adk.sessions import DatabaseSessionService

db_session_service = DatabaseSessionService(
    db_url="sqlite:///sessions.db"  # Or PostgreSQL, MySQL, etc.
)
```

## Memory Services

Memory services provide long-term storage and retrieval of information across sessions, enabling agents to remember past interactions.

```python
from google.adk.memory import InMemoryMemoryService, VertexAiMemoryBankService
from google.adk.agents import Agent
from google.adk.tools import load_memory, preload_memory
import asyncio

# In-memory service for development
memory_service = InMemoryMemoryService()

# Agent with memory tools
memory_agent = Agent(
    name="memory_agent",
    model="gemini-3.1-flash-lite-preview",
    instruction="""You have access to long-term memory.
    Use load_memory to recall past information.
    Use preload_memory to store important information for future reference.""",
    tools=[load_memory, preload_memory]
)

# Vertex AI Memory Bank for production (requires Vertex AI setup)
vertex_memory = VertexAiMemoryBankService(
    project="my-gcp-project",
    location="us-central1"
)

# Store memories programmatically
async def store_memory_example():
    await memory_service.add_session_to_memory(session)  # Store session events as memories

asyncio.run(store_memory_example())
```

## CLI Commands

ADK provides a comprehensive CLI for developing, testing, and deploying agents.

```bash
# Install ADK
pip install google-adk

# Create a new agent project
adk create my_agent_project
adk create my_agent_project --model gemini-3.1-flash-lite-preview --api_key YOUR_API_KEY

# Run an agent interactively in the terminal
adk run path/to/my_agent
adk run path/to/my_agent --session_service_uri "sqlite:///sessions.db"
adk run path/to/my_agent --save_session  # Save session on exit
adk run path/to/my_agent --resume saved_session.json  # Resume previous session

# Start the web development UI
adk web path/to/agents_directory
adk web path/to/agents_directory --port 8080 --host 0.0.0.0
adk web path/to/agents_directory --session_service_uri "sqlite:///sessions.db"

# Start an API server
adk api_server path/to/agents_directory
adk api_server path/to/agents_directory --port 8000 --with_ui

# Evaluate agents with test sets
adk eval path/to/my_agent path/to/eval_set.json
adk eval path/to/my_agent eval_set.json --print_detailed_results
adk eval path/to/my_agent eval_set.json --config_file_path eval_config.yaml

# Deploy to Cloud Run
adk deploy cloud_run path/to/my_agent \
    --project my-gcp-project \
    --region us-central1 \
    --service_name my-agent-service

# Deploy to Vertex AI Agent Engine
adk deploy agent_engine path/to/my_agent \
    --project my-gcp-project \
    --region us-central1 \
    --display_name "My Production Agent"

# Conformance testing
adk conformance test tests/
adk conformance test tests/ --mode replay --generate_report
adk conformance record tests/ SSE
```

## Agent Callbacks

Callbacks allow intercepting and modifying agent behavior at various lifecycle points.

```python
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

# Before agent callback - runs before agent starts
async def before_agent_check(callback_context: CallbackContext):
    """Check conditions before agent runs."""
    if callback_context.state.get("blocked_user"):
        return types.Content(
            parts=[types.Part(text="Access denied.")]
        )
    # Modify state before agent runs
    callback_context.state["agent_started_at"] = "2024-01-01T00:00:00Z"
    return None  # Continue with agent execution

# After agent callback - runs after agent completes
async def after_agent_log(callback_context: CallbackContext):
    """Log after agent completes."""
    callback_context.state["agent_completed"] = True
    return None  # Or return Content to append to response

# Before model callback - intercept LLM requests
async def before_model_inject_context(callback_context: CallbackContext, llm_request: LlmRequest):
    """Inject additional context before model call."""
    # Can modify llm_request in place
    print(f"Model request has {len(llm_request.contents)} messages")
    return None  # Continue, or return LlmResponse to skip model call

# After model callback - process LLM responses
async def after_model_filter(callback_context: CallbackContext, llm_response: LlmResponse):
    """Filter or modify model responses."""
    # Could redact sensitive information, add disclaimers, etc.
    return None  # Use original response

# Before tool callback - intercept tool calls
async def before_tool_auth(tool, args, tool_context):
    """Check authorization before tool execution."""
    if tool.name == "delete_file" and not tool_context.state.get("admin"):
        return {"error": "Unauthorized: admin access required"}
    return None  # Continue with tool execution

# After tool callback - process tool results
async def after_tool_log(tool, args, tool_context, tool_response):
    """Log tool execution results."""
    print(f"Tool {tool.name} returned: {tool_response}")
    return None  # Use original result, or return modified result

agent = Agent(
    name="callbacks_demo",
    model="gemini-3.1-flash-lite-preview",
    instruction="Demonstrate callback functionality.",
    before_agent_callback=before_agent_check,
    after_agent_callback=after_agent_log,
    before_model_callback=[before_model_inject_context],  # Can be list
    after_model_callback=after_model_filter,
    before_tool_callback=before_tool_auth,
    after_tool_callback=after_tool_log
)
```

## Output Schema and Structured Responses

Agents can be configured to return structured outputs conforming to a specific schema.

```python
from google.adk.agents import Agent
from pydantic import BaseModel
from typing import List

class TaskAnalysis(BaseModel):
    summary: str
    priority: str
    estimated_hours: float
    required_skills: List[str]
    risks: List[str]

analysis_agent = Agent(
    name="task_analyzer",
    model="gemini-3.1-flash-lite-preview",
    instruction="Analyze the given task and provide a structured assessment.",
    output_schema=TaskAnalysis,  # Enforces structured output
    output_key="task_analysis"  # Store result in session state
)

# With list output
class TodoItem(BaseModel):
    title: str
    done: bool

todo_agent = Agent(
    name="todo_generator",
    model="gemini-3.1-flash-lite-preview",
    instruction="Generate a todo list for the given project.",
    output_schema=list[TodoItem]  # List of structured items
)
```

## Running Agents Programmatically

Execute agents directly in Python code using the `run_async` method with proper context setup.

```python
import asyncio
from google.adk.agents import Agent, InvocationContext
from google.adk.sessions import InMemorySessionService, Session
from google.adk.artifacts import InMemoryArtifactService
from google.genai import types

async def run_agent_example():
    # Create services
    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()

    # Create agent
    agent = Agent(
        name="demo_agent",
        model="gemini-3.1-flash-lite-preview",
        instruction="You are a helpful assistant."
    )

    # Create session
    session = await session_service.create_session(
        app_name="demo_app",
        user_id="user123"
    )

    # Create user message
    user_content = types.Content(
        role="user",
        parts=[types.Part(text="What is the capital of France?")]
    )

    # Add user message as event
    from google.adk.events.event import Event
    user_event = Event(
        invocation_id="inv_001",
        author="user",
        content=user_content
    )
    session.events.append(user_event)

    # Create invocation context
    from google.adk.agents.invocation_context import InvocationContext

    ctx = InvocationContext(
        invocation_id="inv_001",
        agent=agent,
        session=session,
        artifact_service=artifact_service
    )

    # Run agent and collect responses
    responses = []
    async for event in agent.run_async(ctx):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    responses.append(part.text)

    print("Agent response:", " ".join(responses))

asyncio.run(run_agent_example())
```

## Summary

Google ADK provides a comprehensive framework for building production-grade AI agents with a focus on modularity, extensibility, and developer experience. The hierarchical agent architecture enables complex multi-agent systems where specialized agents collaborate through automatic task delegation. Key integration patterns include: using `LlmAgent` for single-purpose intelligent agents, composing `SequentialAgent` for pipeline workflows, leveraging `ParallelAgent` for concurrent processing, and implementing `LoopAgent` for iterative refinement tasks.

The framework excels in enterprise scenarios through its robust session management for stateful conversations, memory services for long-term context retention, and comprehensive authentication support for secure tool access. Production deployments benefit from the built-in CLI tools for local development and testing, seamless deployment options to Cloud Run and Vertex AI Agent Engine, and evaluation frameworks for continuous agent improvement. Integration with MCP servers extends functionality to external tool ecosystems, while callback hooks enable fine-grained control over agent behavior at every stage of execution.