import json
import logging
import os
import traceback
from typing import Dict, Optional
from pydantic import BaseModel, create_model, Field
from google.genai import types
from google.genai import Client

logger = logging.getLogger(__name__)

# Module-level client cache to avoid re-creating on every call
_client: Optional[Client] = None


def _get_client() -> Client:
    """Return a cached GenAI Client, creating one if needed."""
    global _client
    if _client is None:
        _client = Client(
            vertexai=True
        )
    return _client


def build_dynamic_schema(schema_definition: Dict[str, str]) -> type[BaseModel]:
    """
    Builds a dynamic Pydantic model from a dictionary of keys and descriptions.
    """
    logger.debug("Building dynamic schema with %d fields: %s", len(schema_definition), list(schema_definition.keys()))
    fields = {}
    for key, description in schema_definition.items():
        # For simplicity, treating all fields as string fields.
        # Advanced versions could parse the description to infer types.
        fields[key] = (str, Field(description=description))
    
    DynamicModel = create_model("DynamicDocumentModel", **fields)
    logger.debug("Dynamic Pydantic model created: %s", DynamicModel.model_json_schema())
    return DynamicModel


def extract_document_data(document_text: str, schema_json_str: str) -> dict:
    """Extracts structured data from a document based on a provided JSON schema definition.

    Args:
        document_text: The text content of the document to extract data from.
        schema_json_str: A JSON string containing key-value pairs where the key is the desired field name and the value is the description of the field.

    Returns:
        dict: The extracted data matching the requested schema, or an error status.
    """
    logger.info("extract_document_data called — document length=%d, schema length=%d", len(document_text), len(schema_json_str))
    logger.debug("schema_json_str: %s", schema_json_str)
    logger.debug("document_text (first 500 chars): %s", document_text[:500])

    try:
        schema_definition = json.loads(schema_json_str)
        if not isinstance(schema_definition, dict):
            logger.error("Schema is not a dict: %s", type(schema_definition))
            return {"status": "error", "error_message": "Schema definition must be a JSON object (dictionary)."}
        
        DynamicModel = build_dynamic_schema(schema_definition)
        
        # Make a GenAI API call directly to enforce the dynamic schema.
        client = _get_client()
        model_name = os.environ.get("EXTRACTION_MODEL", "gemini-3.1-flash-lite-preview")
        
        prompt = f"Extract the requested information from the following document.\n\nDocument:\n{document_text}"
        
        logger.info("Calling GenAI model=%s with response_schema enforcement", model_name)
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=DynamicModel,
                temperature=0.0,
            ),
        )
        
        logger.debug("Raw model response text: %s", response.text)
        extracted_json = response.text
        if extracted_json:
            parsed_data = json.loads(extracted_json)
            logger.info("Extraction succeeded — %d fields returned", len(parsed_data))
            logger.debug("Extracted data: %s", json.dumps(parsed_data, indent=2))
            return {"status": "success", "data": parsed_data}
        else:
            logger.warning("Model returned an empty response")
            return {"status": "error", "error_message": "Model returned an empty response."}
            
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in schema: %s", e)
        return {"status": "error", "error_message": f"Invalid JSON in schema: {e}"}
    except Exception as e:
        tb = traceback.format_exc()
        logger.error("extract_document_data failed: %s\n%s", e, tb)
        return {"status": "error", "error_message": f"{type(e).__name__}: {e}"}
