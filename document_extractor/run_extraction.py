import os
import json
import asyncio
import logging

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


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
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "1")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")


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
    logging.getLogger("google.auth").setLevel(logging.INFO)
    logging.getLogger("grpc").setLevel(logging.WARNING)


_load_env()
_configure_logging()

logger = logging.getLogger(__name__)

from document_extractor.agent import root_agent


async def main():

    APP_NAME = "doc_extractor_app"
    USER_ID = "user_1"
    SESSION_ID = "session_1"

    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
    )

    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    document = "Invoice INV-001\nDate: 2026-04-17\nTotal Amount: $1,250.00\nVendor: Acme Corp\n"
    schema = {
        "invoice_number": "The invoice number",
        "date": "The date of the invoice",
        "total_amount": "The total amount of the invoice, without the currency symbol",
        "vendor_name": "The name of the vendor"
    }

    query = f"""Please extract data from this document using the provided schema.

Document:
{document}

Schema:
{json.dumps(schema)}
"""

    logger.info("Starting invoice extraction demo")
    logger.debug("Environment: GOOGLE_GENAI_USE_VERTEXAI=%s, GOOGLE_CLOUD_PROJECT=%s, MODEL_NAME=%s, EXTRACTION_MODEL=%s",
                 os.environ.get("GOOGLE_GENAI_USE_VERTEXAI"),
                 os.environ.get("GOOGLE_CLOUD_PROJECT"),
                 os.environ.get("MODEL_NAME"),
                 os.environ.get("EXTRACTION_MODEL"))
    print("Sending request to agent...\n")
    content = types.Content(
        role="user",
        parts=[types.Part(text=query)],
    )

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=content,
    ):
        logger.debug("Event: author=%s, is_final=%s, has_content=%s",
                      getattr(event, 'author', '?'),
                      event.is_final_response(),
                      bool(event.content and event.content.parts) if event.content else False)
        if event.content and event.content.parts:
            for i, part in enumerate(event.content.parts):
                if part.function_call:
                    logger.info("Function call: %s(%s)", part.function_call.name, json.dumps(dict(part.function_call.args) if part.function_call.args else {}))
                if part.function_response:
                    logger.info("Function response: %s -> %s", part.function_response.name, str(part.function_response.response)[:500])
        if event.is_final_response():
            if event.content and event.content.parts:
                print("\nAgent Response:")
                print(event.content.parts[0].text)
            else:
                logger.warning("Final response has no content")
                print("No content in final response.")

if __name__ == "__main__":
    asyncio.run(main())
