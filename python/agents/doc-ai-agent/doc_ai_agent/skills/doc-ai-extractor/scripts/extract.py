#!/usr/bin/env python3
"""
Document AI Extractor - Extract structured data from PDF documents.

Usage:
    python extract.py <pdf_path> <schema_json>
"""

import json
import sys
from pathlib import Path
from typing import Any


def validate_schema(schema: dict) -> tuple[bool, str]:
    """Validate the extraction schema format."""
    if "keys" not in schema:
        return False, "Schema must contain 'keys' array"

    if not isinstance(schema["keys"], list) or len(schema["keys"]) == 0:
        return False, "Schema 'keys' must be a non-empty array"

    valid_key_types = {"field", "list"}
    valid_data_types = {"string", "number"}

    key_names = set()
    for i, key in enumerate(schema["keys"]):
        required_fields = ["name", "key_type", "data_type", "description"]
        for field in required_fields:
            if field not in key:
                return False, f"Key at index {i} missing required field: {field}"

        if key["key_type"] not in valid_key_types:
            return False, f"Invalid key_type '{key['key_type']}' at index {i}. Must be 'field' or 'list'"

        if key["data_type"] not in valid_data_types:
            return False, f"Invalid data_type '{key['data_type']}' at index {i}. Must be 'string' or 'number'"

        key_names.add(key["name"])

    if "mandatory_keys" in schema:
        for mandatory_key in schema["mandatory_keys"]:
            if mandatory_key not in key_names:
                return False, f"Mandatory key '{mandatory_key}' not found in keys definition"

    return True, "Schema is valid"


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text content from a PDF file."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except ImportError:
        try:
            from pypdf import PdfReader
            reader = PdfReader(pdf_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
        except ImportError:
            raise ImportError("No PDF library available. Install PyMuPDF or pypdf.")


def build_extraction_prompt(text: str, schema: dict) -> str:
    """Build the prompt for AI extraction."""
    keys_description = []
    for key in schema["keys"]:
        key_desc = f"- {key['name']} ({key['key_type']}, {key['data_type']}): {key['description']}"
        keys_description.append(key_desc)

    mandatory = schema.get("mandatory_keys", [])
    mandatory_note = f"\n\nMANDATORY KEYS (must be extracted): {', '.join(mandatory)}" if mandatory else ""

    prompt = f"""Extract the following information from the document text below.

KEYS TO EXTRACT:
{chr(10).join(keys_description)}
{mandatory_note}

RULES:
1. For 'field' key_type: extract a single value
2. For 'list' key_type: extract as an array of values
3. For 'string' data_type: return text values
4. For 'number' data_type: return numeric values (no currency symbols)
5. If a value cannot be found, use null
6. Return ONLY valid JSON, no additional text

DOCUMENT TEXT:
{text}

OUTPUT FORMAT:
Return a JSON object with the extracted values. Example:
{{"key_name": "value", "list_key": ["item1", "item2"]}}
"""
    return prompt


def format_output(extracted_data: dict, schema: dict, page_count: int) -> dict:
    """Format the extraction output."""
    mandatory_keys = schema.get("mandatory_keys", [])
    missing_keys = []

    for key in mandatory_keys:
        if key not in extracted_data or extracted_data[key] is None:
            missing_keys.append(key)

    if missing_keys:
        return {
            "status": "error",
            "error_code": "MANDATORY_KEYS_MISSING",
            "message": "Could not extract required mandatory keys",
            "missing_keys": missing_keys,
            "extracted_data": None
        }

    return {
        "status": "success",
        "extracted_data": extracted_data,
        "metadata": {
            "document_pages": page_count,
            "extraction_confidence": "high"
        }
    }


def main():
    if len(sys.argv) < 3:
        print("Usage: python extract.py <pdf_path> <schema_json>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    schema_json = sys.argv[2]

    if not Path(pdf_path).exists():
        print(json.dumps({
            "status": "error",
            "error_code": "FILE_NOT_FOUND",
            "message": f"PDF file not found: {pdf_path}"
        }))
        sys.exit(1)

    try:
        schema = json.loads(schema_json)
    except json.JSONDecodeError as e:
        print(json.dumps({
            "status": "error",
            "error_code": "INVALID_SCHEMA",
            "message": f"Invalid JSON schema: {str(e)}"
        }))
        sys.exit(1)

    valid, message = validate_schema(schema)
    if not valid:
        print(json.dumps({
            "status": "error",
            "error_code": "SCHEMA_VALIDATION_ERROR",
            "message": message
        }))
        sys.exit(1)

    print(f"Schema validated. Ready to extract from: {pdf_path}")
    print(f"Keys to extract: {[k['name'] for k in schema['keys']]}")
    print(f"Mandatory keys: {schema.get('mandatory_keys', [])}")


if __name__ == "__main__":
    main()
