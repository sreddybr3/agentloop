"""Demo script that extracts structured data using the LOCAL Ollama-based agent.

This uses the ADK Runner with ``local_agent.py`` which routes both:
  - Agent orchestration LLM → Ollama (via LiteLLM)
  - Extraction tool calls   → Ollama (via direct HTTP)

Prerequisites:
    pip install google-adk[extensions]   # adds litellm for Ollama agent support
    ollama pull gemma4:latest

Usage:
    python run_local_extraction.py
"""

import os
import json
import asyncio
import logging


def _load_env():
    """Load environment variables from .env file if present."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())


def _configure_logging():
    """Set up detailed debug logging."""
    log_level = os.environ.get("LOG_LEVEL", "DEBUG").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.DEBUG),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


# Load env BEFORE importing agent (so OLLAMA_MODEL etc. are available at import time)
_load_env()
_configure_logging()

logger = logging.getLogger(__name__)

from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402

from document_extractor.archive.agent import local_root_agent  # noqa: E402
from document_extractor.schemas import resume_schema_to_extraction_format  # noqa: E402


# ── Sample data ──────────────────────────────────────────────────────────────

SAMPLE_RESUME = """\
JOHN DOE
Email: john.doe@email.com | Phone: +1-555-123-4567 | Location: San Francisco, CA

PROFESSIONAL SUMMARY
Results-driven software engineer with 8 years of experience in full-stack
development specializing in cloud-native applications and distributed systems.

SKILLS
Python, Java, TypeScript, React, Node.js, AWS, Kubernetes, Docker, PostgreSQL,
MongoDB, CI/CD, Agile, Team Leadership

WORK EXPERIENCE

Senior Software Engineer | Acme Technologies | Jan 2021 - Present
- Led a team of 5 engineers to deliver a microservices platform serving 2M+ users
- Reduced API response times by 40% through caching and query optimization
- Designed event-driven architecture using Kafka and AWS Lambda

Software Engineer | Beta Corp | Jun 2017 - Dec 2020
- Developed RESTful APIs in Python/Flask and Java/Spring Boot
- Built CI/CD pipelines using Jenkins and GitHub Actions
- Mentored 3 junior developers

EDUCATION
M.S. Computer Science | Stanford University | 2017
B.S. Computer Science | UC Berkeley | 2015

CERTIFICATIONS
AWS Certified Solutions Architect - Associate | Amazon Web Services | 2022
Certified Kubernetes Administrator (CKA) | CNCF | 2023

LANGUAGES
English, Spanish, Mandarin
"""


async def main():
    logger.info("Starting LOCAL resume extraction demo (Ollama-based agent)")
    logger.info(
        "Ollama: base_url=%s, model=%s, agent_model=%s",
        os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        os.environ.get("OLLAMA_MODEL", "gemma4:latest"),
        os.environ.get("LOCAL_AGENT_MODEL", f"ollama/{os.environ.get('OLLAMA_MODEL', 'gemma4:latest')}"),
    )

    APP_NAME = "local_extractor_app"
    USER_ID = "user_1"
    SESSION_ID = "session_local"

    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
    )

    runner = Runner(
        agent=local_root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    # Use the default resume schema
    schema = resume_schema_to_extraction_format()

    query = f"""Please extract data from this candidate resume using the provided schema.

Document:
{SAMPLE_RESUME}

Schema:
{json.dumps(schema, indent=2)}
"""

    logger.info("Schema has %d top-level fields", len(schema))
    print("Sending resume to LOCAL agent for extraction...\n")

    content = types.Content(
        role="user",
        parts=[types.Part(text=query)],
    )

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=content,
    ):
        logger.debug(
            "Event: author=%s, is_final=%s, has_content=%s",
            getattr(event, "author", "?"),
            event.is_final_response(),
            bool(event.content and event.content.parts) if event.content else False,
        )
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.function_call:
                    logger.info(
                        "Function call: %s(%s)",
                        part.function_call.name,
                        json.dumps(dict(part.function_call.args) if part.function_call.args else {}),
                    )
                if part.function_response:
                    logger.info(
                        "Function response: %s -> %s",
                        part.function_response.name,
                        str(part.function_response.response)[:500],
                    )
        if event.is_final_response():
            if event.content and event.content.parts:
                print("\nExtracted Resume Data (Local Agent):")
                print(event.content.parts[0].text)
            else:
                logger.warning("Final response has no content")
                print("No content in final response.")


if __name__ == "__main__":
    asyncio.run(main())