"""Default extraction schemas."""

import json
from pathlib import Path

SCHEMA_DIR = Path(__file__).parent


def load_resume_schema() -> list[dict]:
    """Load the default candidate resume extraction schema."""
    schema_path = SCHEMA_DIR / "resume_schema.json"
    with open(schema_path, "r") as f:
        return json.load(f)


def resume_schema_to_extraction_format() -> dict[str, str]:
    """Convert the resume schema into the flat {field_name: description} format
    expected by the extract_document_data tool.

    Only top-level fields (no dot notation) are included since the dynamic
    Pydantic model builder creates flat string fields.
    """
    schema = load_resume_schema()
    return {
        entry["name"]: entry["description"]
        for entry in schema
        if "." not in entry["name"]
    }