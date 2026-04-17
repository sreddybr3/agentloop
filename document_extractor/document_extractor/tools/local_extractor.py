"""Local document extractor tool that uses Ollama (Gemma4) instead of Google GenAI.

This module mirrors the interface of extractor.py but sends requests to a
locally-running Ollama server for fully offline / on-prem extraction.

Environment variables:
    OLLAMA_BASE_URL   – Ollama API base URL  (default: http://localhost:11434)
    OLLAMA_MODEL      – Model name to use    (default: gemma4:latest)
"""

import json
import logging
import os
import traceback
from typing import Dict

import httpx

logger = logging.getLogger(__name__)

_OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma4:latest")

# Timeout for Ollama requests (generation can be slow on CPU)
_REQUEST_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "120"))


def _build_extraction_prompt(document_text: str, schema_definition: Dict[str, str]) -> str:
    """Build a prompt that instructs the model to return valid JSON matching the schema."""
    field_descriptions = "\n".join(
        f'  - "{key}": {description}' for key, description in schema_definition.items()
    )
    return f"""You are a precise document data extractor. Extract the requested fields from the document below.

Return ONLY a valid JSON object with the following fields:
{field_descriptions}

Rules:
- Return raw JSON only — no markdown fences, no explanation, no extra text.
- If a field is not found in the document, use an empty string "".
- For numeric fields, return the value as a string.

Document:
{document_text}

JSON:"""


def _build_json_schema(schema_definition: Dict[str, str]) -> dict:
    """Build a JSON Schema object for Ollama structured output (format parameter)."""
    properties = {}
    for key, description in schema_definition.items():
        properties[key] = {"type": "string", "description": description}
    return {
        "type": "object",
        "properties": properties,
        "required": list(schema_definition.keys()),
    }


def extract_document_data_local(document_text: str, schema_json_str: str) -> dict:
    """Extracts structured data from a document using a local Ollama model.

    Args:
        document_text: The text content of the document to extract data from.
        schema_json_str: A JSON string containing key-value pairs where the key
            is the desired field name and the value is the description of the field.

    Returns:
        dict: The extracted data matching the requested schema, or an error status.
    """
    logger.info(
        "extract_document_data_local called — document length=%d, schema length=%d",
        len(document_text),
        len(schema_json_str),
    )
    logger.debug("schema_json_str: %s", schema_json_str)
    logger.debug("document_text (first 500 chars): %s", document_text[:500])

    try:
        schema_definition = json.loads(schema_json_str)
        if not isinstance(schema_definition, dict):
            logger.error("Schema is not a dict: %s", type(schema_definition))
            return {
                "status": "error",
                "error_message": "Schema definition must be a JSON object (dictionary).",
            }

        prompt = _build_extraction_prompt(document_text, schema_definition)
        json_schema = _build_json_schema(schema_definition)

        ollama_url = os.environ.get("OLLAMA_BASE_URL", _OLLAMA_BASE_URL)
        ollama_model = os.environ.get("OLLAMA_MODEL", _OLLAMA_MODEL)
        api_url = f"{ollama_url.rstrip('/')}/api/chat"

        logger.info("Calling Ollama model=%s at %s", ollama_model, api_url)
        logger.debug("JSON schema for structured output: %s", json.dumps(json_schema, indent=2))

        # Use Ollama's /api/chat endpoint with structured output (format param)
        payload = {
            "model": ollama_model,
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "format": json_schema,
            "stream": False,
            "options": {
                "temperature": 0.0,
            },
        }

        logger.debug("Ollama request payload (without prompt): model=%s, stream=False, temperature=0.0", ollama_model)

        with httpx.Client(timeout=_REQUEST_TIMEOUT) as client:
            response = client.post(api_url, json=payload)
            response.raise_for_status()

        response_json = response.json()
        raw_text = response_json.get("message", {}).get("content", "")
        logger.debug("Raw Ollama response text: %s", raw_text)

        if not raw_text:
            logger.warning("Ollama returned an empty response")
            return {"status": "error", "error_message": "Model returned an empty response."}

        # Parse the JSON from the model response
        parsed_data = json.loads(raw_text)
        logger.info("Extraction succeeded — %d fields returned", len(parsed_data))
        logger.debug("Extracted data: %s", json.dumps(parsed_data, indent=2))
        return {"status": "success", "data": parsed_data}

    except httpx.ConnectError:
        msg = f"Cannot connect to Ollama at {_OLLAMA_BASE_URL}. Is Ollama running?"
        logger.error(msg)
        return {"status": "error", "error_message": msg}
    except httpx.HTTPStatusError as e:
        msg = f"Ollama HTTP error {e.response.status_code}: {e.response.text[:300]}"
        logger.error(msg)
        return {"status": "error", "error_message": msg}
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in response or schema: %s", e)
        return {"status": "error", "error_message": f"Invalid JSON: {e}"}
    except Exception as e:
        tb = traceback.format_exc()
        logger.error("extract_document_data_local failed: %s\n%s", e, tb)
        return {"status": "error", "error_message": f"{type(e).__name__}: {e}"}