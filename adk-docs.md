# Agent Development Kit (ADK)

The Agent Development Kit (ADK) is an open-source, code-first toolkit for building, evaluating, and deploying sophisticated AI agents. Developed by Google, ADK provides a flexible and modular framework optimized for Gemini and the Google ecosystem while remaining model-agnostic and deployment-agnostic. The toolkit supports Python, TypeScript, Go, and Java, enabling developers to create agents that range from simple task automation to complex multi-agent workflows.

ADK's architecture centers around LLM-powered agents that can use custom tools, maintain conversational context through sessions and memory, and orchestrate complex workflows using specialized workflow agents. The framework provides built-in support for observability, evaluation, and seamless deployment to Google Cloud services like Cloud Run and Vertex AI Agent Engine, making it suitable for both rapid prototyping and production deployments.

## Creating a Basic Agent with Tools

The Agent class is the core building block for creating LLM-powered agents. Agents are configured with a name, model, description, instruction, and tools that define their capabilities and behavior.

```python
import datetime
from zoneinfo import ZoneInfo
from google.adk.agents import Agent

def get_weather(city: str) -> dict:
    """Retrieves the current weather report for a specified city.

    Args:
        city (str): The name of the city for which to retrieve the weather report.

    Returns:
        dict: status and result or error msg.
    """
    if city.lower() == "new york":
        return {
            "status": "success",
            "report": "The weather in New York is sunny with a temperature of 25 degrees Celsius (77 degrees Fahrenheit).",
        }
    else:
        return {
            "status": "error",
            "error_message": f"Weather information for '{city}' is not available.",
        }

def get_current_time(city: str) -> dict:
    """Returns the current time in a specified city.

    Args:
        city (str): The name of the city for which to retrieve the current time.

    Returns:
        dict: status and result or error msg.
    """
    if city.lower() == "new york":
        tz_identifier = "America/New_York"
    else:
        return {
            "status": "error",
            "error_message": f"Sorry, I don't have timezone information for {city}.",
        }
    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    report = f'The current time in {city} is {now.strftime("%Y-%m-%d %H:%M:%S %Z%z")}'
    return {"status": "success", "report": report}

root_agent = Agent(
    name="weather_time_agent",
    model="gemini-3.1-flash-lite-preview",
    description="Agent to answer questions about the time and weather in a city.",
    instruction="You are a helpful agent who can answer user questions about the time and weather in a city.",
    tools=[get_weather, get_current_time],
)
```

## Creating an Agent in TypeScript

TypeScript agents use the LlmAgent class with FunctionTool for defining tools. Tools are created with explicit schemas using Zod for parameter validation.

```typescript
import 'dotenv/config';
import { FunctionTool, LlmAgent } from '@google/adk';
import { z } from 'zod';

const getWeather = new FunctionTool({
  name: 'get_weather',
  description: 'Retrieves the current weather report for a specified city.',
  parameters: z.object({
    city: z.string().describe('The name of the city for which to retrieve the weather report.'),
  }),
  execute: ({ city }) => {
    if (city.toLowerCase() === 'new york') {
      return {
        status: 'success',
        report: 'The weather in New York is sunny with a temperature of 25 degrees Celsius (77 degrees Fahrenheit).',
      };
    } else {
      return {
        status: 'error',
        error_message: `Weather information for '${city}' is not available.`,
      };
    }
  },
});

const getCurrentTime = new FunctionTool({
  name: 'get_current_time',
  description: 'Returns the current time in a specified city.',
  parameters: z.object({
    city: z.string().describe("The name of the city for which to retrieve the current time."),
  }),
  execute: ({ city }) => {
    if (city.toLowerCase() === 'new york') {
      const now = new Date();
      return { status: 'success', report: `The current time in ${city} is ${now.toLocaleString('en-US', { timeZone: 'America/New_York' })}` };
    }
    return { status: 'error', error_message: `Sorry, I don't have timezone information for ${city}.` };
  },
});

export const rootAgent = new LlmAgent({
  name: 'weather_time_agent',
  model: 'gemini-3.1-flash-lite-preview',
  description: 'Agent to answer questions about the time and weather in a city.',
  instruction: 'You are a helpful agent who can answer user questions about the time and weather in a city.',
  tools: [getWeather, getCurrentTime],
});
```

## Running an Agent with the Runner

The Runner class executes agents within a session context, managing the conversation flow and producing events that capture all agent actions including tool calls and responses.

```python
from google.genai import types
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

APP_NAME = "weather_app"
USER_ID = "user_123"
SESSION_ID = "session_456"

# Create the agent
agent = Agent(
    name="weather_agent",
    model="gemini-3.1-flash-lite-preview",
    instruction="You are a helpful weather assistant.",
    tools=[get_weather],
)

# Set up session service and create session
session_service = InMemorySessionService()
session = session_service.create_session(
    app_name=APP_NAME,
    user_id=USER_ID,
    session_id=SESSION_ID
)

# Create runner
runner = Runner(
    agent=agent,
    app_name=APP_NAME,
    session_service=session_service
)

# Run the agent with a user message
def call_agent(query: str):
    content = types.Content(
        role='user',
        parts=[types.Part(text=query)]
    )
    events = runner.run(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=content
    )
    for event in events:
        if event.is_final_response() and event.content:
            return event.content.parts[0].text

response = call_agent("What is the weather in New York?")
print(response)
# Output: The weather in New York is sunny with a temperature of 25 degrees Celsius (77 degrees Fahrenheit).
```

## Sequential Agent Workflow

SequentialAgent executes sub-agents in order, passing context through shared session state using the output_key parameter to store results.

```python
from google.adk.agents import SequentialAgent, LlmAgent

# Step 1: Validate input
validator = LlmAgent(
    name="ValidateInput",
    model="gemini-3.1-flash-lite-preview",
    instruction="Validate the user input and confirm it's a valid request.",
    output_key="validation_status"
)

# Step 2: Process data based on validation
processor = LlmAgent(
    name="ProcessData",
    model="gemini-3.1-flash-lite-preview",
    instruction="Process the data if {validation_status} indicates valid input.",
    output_key="result"
)

# Step 3: Report the result
reporter = LlmAgent(
    name="ReportResult",
    model="gemini-3.1-flash-lite-preview",
    instruction="Generate a user-friendly report based on {result}."
)

# Create sequential pipeline
data_pipeline = SequentialAgent(
    name="DataPipeline",
    sub_agents=[validator, processor, reporter]
)
# validator runs -> saves to state['validation_status']
# processor runs -> reads state['validation_status'], saves to state['result']
# reporter runs -> reads state['result']
```

## Parallel Agent Workflow

ParallelAgent executes multiple sub-agents concurrently, useful for gathering independent data simultaneously.

```python
from google.adk.agents import SequentialAgent, ParallelAgent, LlmAgent

# Agents that fetch data in parallel
fetch_weather = LlmAgent(
    name="WeatherFetcher",
    model="gemini-3.1-flash-lite-preview",
    instruction="Fetch weather data for the user's location.",
    output_key="weather"
)

fetch_news = LlmAgent(
    name="NewsFetcher",
    model="gemini-3.1-flash-lite-preview",
    instruction="Fetch the latest news headlines.",
    output_key="news"
)

# Run both fetchers in parallel
gatherer = ParallelAgent(
    name="InfoGatherer",
    sub_agents=[fetch_weather, fetch_news]
)

# Synthesize results after parallel execution
synthesizer = LlmAgent(
    name="Synthesizer",
    model="gemini-3.1-flash-lite-preview",
    instruction="Create a morning briefing combining {weather} and {news}."
)

# Complete workflow: parallel fetch then synthesize
morning_briefing = SequentialAgent(
    name="MorningBriefing",
    sub_agents=[gatherer, synthesizer]
)
```

## Loop Agent for Iterative Workflows

LoopAgent repeatedly executes sub-agents until a condition is met or max_iterations is reached. Use EventActions with escalate=True to exit the loop.

```python
from google.adk.agents import LoopAgent, LlmAgent, BaseAgent
from google.adk.events import Event, EventActions
from google.adk.agents.invocation_context import InvocationContext
from typing import AsyncGenerator

# Agent that refines code each iteration
code_refiner = LlmAgent(
    name="CodeRefiner",
    model="gemini-3.1-flash-lite-preview",
    instruction="Read state['current_code'] and state['requirements']. Improve the code to better meet requirements.",
    output_key="current_code"
)

# Agent that evaluates code quality
quality_checker = LlmAgent(
    name="QualityChecker",
    model="gemini-3.1-flash-lite-preview",
    instruction="Evaluate the code in state['current_code']. Output 'pass' or 'fail'.",
    output_key="quality_status"
)

# Custom agent to check status and escalate when done
class CheckStatusAndEscalate(BaseAgent):
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        status = ctx.session.state.get("quality_status", "fail")
        should_stop = (status == "pass")
        yield Event(author=self.name, actions=EventActions(escalate=should_stop))

# Create the refinement loop
refinement_loop = LoopAgent(
    name="CodeRefinementLoop",
    max_iterations=5,
    sub_agents=[code_refiner, quality_checker, CheckStatusAndEscalate(name="StopChecker")]
)
# Loop continues until quality_status is 'pass' or 5 iterations complete
```

## Multi-Agent Coordinator Pattern

Create a coordinator agent that routes requests to specialized sub-agents using LLM-driven delegation via transfer_to_agent.

```python
from google.adk.agents import LlmAgent

# Specialized agents
billing_agent = LlmAgent(
    name="Billing",
    model="gemini-3.1-flash-lite-preview",
    description="Handles billing inquiries, payment issues, and invoice questions."
)

support_agent = LlmAgent(
    name="Support",
    model="gemini-3.1-flash-lite-preview",
    description="Handles technical support requests, troubleshooting, and product issues."
)

# Coordinator that routes to appropriate specialist
coordinator = LlmAgent(
    name="HelpDeskCoordinator",
    model="gemini-3.1-flash-lite-preview",
    instruction="""You are a help desk coordinator. Route user requests appropriately:
    - Payment/billing questions -> transfer to Billing agent
    - Technical problems/bugs -> transfer to Support agent
    Analyze the user's request and transfer to the most appropriate agent.""",
    description="Main help desk router.",
    sub_agents=[billing_agent, support_agent]
)
# When user asks "My payment failed", coordinator transfers to Billing agent
# When user asks "I can't log in", coordinator transfers to Support agent
```

## Using AgentTool for Agent-as-Tool Pattern

AgentTool allows one agent to invoke another as a tool, maintaining control and receiving the result back for further processing.

```python
from google.adk.agents import LlmAgent
from google.adk.tools import AgentTool

# Specialized research agent
researcher = LlmAgent(
    name="Researcher",
    model="gemini-3.1-flash-lite-preview",
    description="Performs detailed research on a topic and returns findings.",
    instruction="Research the given topic thoroughly and provide a comprehensive summary."
)

# Summarization agent
summarizer = LlmAgent(
    name="Summarizer",
    model="gemini-3.1-flash-lite-preview",
    description="Summarizes long text into concise bullet points.",
    instruction="Create a concise bullet-point summary of the provided text."
)

# Main agent that uses other agents as tools
main_agent = LlmAgent(
    name="ReportWriter",
    model="gemini-3.1-flash-lite-preview",
    instruction="""You write reports on topics. Use these tools:
    - Researcher: for gathering detailed information on a topic
    - Summarizer: for condensing long text into key points
    First research the topic, then summarize the findings.""",
    tools=[
        AgentTool(agent=researcher),
        AgentTool(agent=summarizer, skip_summarization=True)
    ]
)
```

## Callbacks for Agent Lifecycle

Callbacks allow intercepting agent execution at various points for logging, validation, or modifying behavior.

```python
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

def before_agent_callback(callback_context: CallbackContext) -> types.Content | None:
    """Called before agent runs. Return Content to skip agent execution."""
    if callback_context.state.get("skip_agent"):
        return types.Content(
            role="model",
            parts=[types.Part(text="Agent execution was skipped based on state.")]
        )
    print(f"Agent {callback_context.agent_name} starting...")
    return None  # Continue with normal execution

def after_agent_callback(callback_context: CallbackContext) -> types.Content | None:
    """Called after agent completes. Return Content to append to output."""
    print(f"Agent {callback_context.agent_name} completed.")
    if callback_context.state.get("add_footer"):
        return types.Content(
            role="model",
            parts=[types.Part(text="\n\n---\nGenerated by ADK Agent")]
        )
    return None

agent = LlmAgent(
    name="CallbackAgent",
    model="gemini-3.1-flash-lite-preview",
    instruction="You are a helpful assistant.",
    before_agent_callback=before_agent_callback,
    after_agent_callback=after_agent_callback,
)
```

## Before/After Model Callbacks

Model callbacks intercept LLM requests and responses for caching, logging, or implementing guardrails.

```python
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse

def before_model_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest
) -> LlmResponse | None:
    """Called before LLM request. Return LlmResponse to skip the LLM call."""
    # Check for cached response
    cache_key = str(llm_request.contents[-1].parts[0].text)
    cached = callback_context.state.get(f"cache:{cache_key}")
    if cached:
        return LlmResponse(content=cached)  # Return cached response

    # Implement guardrails - block certain content
    if "forbidden_word" in cache_key.lower():
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part(text="I cannot process that request.")]
            )
        )
    return None  # Continue with LLM call

def after_model_callback(
    callback_context: CallbackContext,
    llm_response: LlmResponse
) -> LlmResponse | None:
    """Called after LLM response. Return modified LlmResponse or None."""
    # Log the response
    print(f"LLM Response: {llm_response.content}")
    # Optionally modify or filter the response
    return None

agent = LlmAgent(
    name="GuardedAgent",
    model="gemini-3.1-flash-lite-preview",
    instruction="You are a helpful assistant.",
    before_model_callback=before_model_callback,
    after_model_callback=after_model_callback,
)
```

## Tool Callbacks

Tool callbacks intercept tool execution for authorization, logging, caching, or modifying results.

```python
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import BaseTool
from typing import Any

def before_tool_callback(
    callback_context: CallbackContext,
    tool: BaseTool,
    args: dict[str, Any]
) -> dict[str, Any] | None:
    """Called before tool execution. Return dict to skip tool and use as result."""
    print(f"Tool '{tool.name}' called with args: {args}")

    # Authorization check
    if tool.name == "admin_tool" and not callback_context.state.get("is_admin"):
        return {"error": "Unauthorized access to admin tool"}

    # Check cache
    cache_key = f"{tool.name}:{args}"
    cached = callback_context.state.get(f"tool_cache:{cache_key}")
    if cached:
        return cached

    return None  # Execute the tool normally

def after_tool_callback(
    callback_context: CallbackContext,
    tool: BaseTool,
    args: dict[str, Any],
    tool_response: dict[str, Any]
) -> dict[str, Any] | None:
    """Called after tool execution. Return dict to replace tool response."""
    print(f"Tool '{tool.name}' returned: {tool_response}")

    # Cache the result
    cache_key = f"{tool.name}:{args}"
    callback_context.state[f"tool_cache:{cache_key}"] = tool_response

    # Optionally modify the response
    return None

agent = LlmAgent(
    name="ToolCallbackAgent",
    model="gemini-3.1-flash-lite-preview",
    instruction="You are an assistant with tool access.",
    tools=[get_weather],
    before_tool_callback=before_tool_callback,
    after_tool_callback=after_tool_callback,
)
```

## LLM Generation Configuration

Fine-tune LLM behavior with GenerateContentConfig for controlling temperature, output length, and safety settings.

```python
from google.genai import types
from google.adk.agents import LlmAgent

agent = LlmAgent(
    name="ConfiguredAgent",
    model="gemini-3.1-flash-lite-preview",
    instruction="You are a precise and factual assistant.",
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2,  # Lower temperature for more deterministic output
        max_output_tokens=500,
        top_p=0.8,
        top_k=40,
        safety_settings=[
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
        ]
    )
)
```

## Structured Output with Schema

Define input and output schemas to enforce structured data exchange with the LLM.

```python
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent

class CapitalOutput(BaseModel):
    capital: str = Field(description="The capital city of the country")
    country: str = Field(description="The country name")
    population: int | None = Field(default=None, description="Population of the capital")

structured_agent = LlmAgent(
    name="CapitalInfoAgent",
    model="gemini-3.1-flash-lite-preview",
    instruction="""You are a geography expert. When asked about a country's capital,
    respond with accurate information in the required JSON format.
    Include population if known.""",
    output_schema=CapitalOutput,
    output_key="capital_info"  # Save to session state
)

# The agent will respond with structured JSON matching CapitalOutput schema
# Response example: {"capital": "Paris", "country": "France", "population": 2161000}
```

## Running the API Server

The ADK API server exposes agents via REST endpoints for programmatic testing and integration.

```bash
# Start the API server (Python)
adk api_server

# Start the API server (TypeScript)
npx adk api_server

# Create a session
curl -X POST http://localhost:8000/apps/my_agent/users/u_123/sessions/s_456 \
  -H "Content-Type: application/json" \
  -d '{"initial_key": "initial_value"}'

# Send a message to the agent
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "appName": "my_agent",
    "userId": "u_123",
    "sessionId": "s_456",
    "newMessage": {
      "role": "user",
      "parts": [{"text": "What is the weather in New York?"}]
    }
  }'

# Stream responses with Server-Sent Events
curl -X POST http://localhost:8000/run_sse \
  -H "Content-Type: application/json" \
  -d '{
    "appName": "my_agent",
    "userId": "u_123",
    "sessionId": "s_456",
    "newMessage": {
      "role": "user",
      "parts": [{"text": "What is the weather in New York?"}]
    },
    "streaming": true
  }'

# Get session details
curl -X GET http://localhost:8000/apps/my_agent/users/u_123/sessions/s_456

# List available agents
curl -X GET http://localhost:8000/list-apps
```

## Deploying to Cloud Run

Deploy ADK agents to Google Cloud Run for production use with the adk CLI or gcloud.

```bash
# Set environment variables
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"
export AGENT_PATH="./my_agent"
export SERVICE_NAME="my-agent-service"

# Deploy with adk CLI (Python)
adk deploy cloud_run \
  --project=$GOOGLE_CLOUD_PROJECT \
  --region=$GOOGLE_CLOUD_LOCATION \
  --service_name=$SERVICE_NAME \
  --with_ui \
  $AGENT_PATH

# Deploy with adk CLI (TypeScript) - run from agent directory
npx adk deploy cloud_run \
  --project=$GOOGLE_CLOUD_PROJECT \
  --region=$GOOGLE_CLOUD_LOCATION \
  --service_name=$SERVICE_NAME \
  --with_ui

# Test deployed agent
export APP_URL="https://your-service-url.run.app"
export TOKEN=$(gcloud auth print-identity-token)

# Create session on deployed service
curl -X POST -H "Authorization: Bearer $TOKEN" \
  $APP_URL/apps/my_agent/users/u_123/sessions/s_456 \
  -H "Content-Type: application/json" \
  -d '{}'

# Run agent on deployed service
curl -X POST -H "Authorization: Bearer $TOKEN" \
  $APP_URL/run \
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

## Session State Management

Sessions maintain conversation context and state across multiple interactions. State variables can be read and written by agents and tools.

```python
from google.adk.agents import LlmAgent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner

# Create agent that uses state
agent = LlmAgent(
    name="StatefulAgent",
    model="gemini-3.1-flash-lite-preview",
    instruction="""You are a shopping assistant.
    The user's cart is stored in {cart_items}.
    The user's name is {user_name}.
    Help them manage their shopping cart.""",
    output_key="last_response"  # Save response to state
)

# Initialize session with pre-populated state
session_service = InMemorySessionService()
session = session_service.create_session(
    app_name="shop_app",
    user_id="user_1",
    session_id="session_1",
    state={
        "user_name": "Alice",
        "cart_items": ["laptop", "mouse"],
        "total_visits": 5
    }
)

# State is available in agent instructions via {variable_name}
# Tools can access state via tool_context.state
# Output is saved to state['last_response'] due to output_key
```

## Long Running Function Tools

LongRunningFunctionTool handles async operations that require external processing or human intervention without blocking the agent.

```python
from google.adk.agents import LlmAgent
from google.adk.tools import LongRunningFunctionTool

def ask_for_approval(purpose: str, amount: float) -> dict:
    """Request human approval for a purchase.

    Args:
        purpose: The reason for the purchase
        amount: The purchase amount

    Returns:
        dict with ticket_id and initial status
    """
    # Create approval ticket (would integrate with external system)
    ticket_id = f"approval-{purpose.replace(' ', '-')}-{amount}"
    return {
        "status": "pending",
        "ticket_id": ticket_id,
        "message": f"Approval requested for ${amount} - {purpose}"
    }

# Wrap as long-running tool
approval_tool = LongRunningFunctionTool(func=ask_for_approval)

agent = LlmAgent(
    name="PurchaseAgent",
    model="gemini-3.1-flash-lite-preview",
    instruction="""You help users make purchases.
    For purchases over $100, use the approval tool to request manager approval.
    Wait for approval before confirming the purchase.""",
    tools=[approval_tool]
)

# When tool is called, agent run pauses
# Client can poll for approval status and send response back
# Agent continues when approval response is received
```

## Summary

ADK enables developers to build sophisticated AI agents using a code-first approach that emphasizes modularity, testability, and production readiness. The framework supports common patterns including single agents with custom tools, sequential and parallel workflows for complex pipelines, coordinator patterns for routing requests, and iterative refinement loops. Agents communicate through shared session state, LLM-driven delegation, or explicit AgentTool invocations, providing flexibility in designing multi-agent systems.

For integration, ADK provides multiple deployment options including local development servers, REST API endpoints for programmatic access, and production deployment to Google Cloud Run or Vertex AI Agent Engine. The callback system enables extensibility for logging, caching, guardrails, and custom authorization logic. Whether building simple chatbots or complex enterprise workflows, ADK provides the primitives and patterns needed to create reliable, observable, and scalable AI agent applications across Python, TypeScript, Go, and Java.