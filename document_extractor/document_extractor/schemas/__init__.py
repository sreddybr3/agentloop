"""Schema definitions for document extraction.

This module provides:
  - ``DEFAULT_RESUME_SCHEMA``  – rich schema (array of objects with name, description,
    entity_type, data_type) loaded from ``resume_schema.json``
  - ``DEFAULT_RESUME_EXTRACTION_SCHEMA`` – flat extraction schema (key → description)
    loaded from ``resume_extraction_schema.json``
  - ``resume_schema_to_extraction_format()`` – converts the rich schema into the flat
    extraction format used by the extractor tools
  - ``load_extraction_schema()`` – loads the flat extraction schema directly
"""

import json
import os
from typing import Dict, List

_SCHEMA_DIR = os.path.dirname(__file__)


def _load_json(filename: str):
    """Load a JSON file from the schemas directory."""
    path = os.path.join(_SCHEMA_DIR, filename)
    with open(path, "r") as f:
        return json.load(f)


# Rich schema: array of {name, description, entity_type, data_type}
DEFAULT_RESUME_SCHEMA: List[dict] = _load_json("resume_schema.json")

# Flat extraction schema: {field_name: description}
DEFAULT_RESUME_EXTRACTION_SCHEMA: Dict[str, str] = _load_json("resume_extraction_schema.json")


def resume_schema_to_extraction_format() -> Dict[str, str]:
    """Convert the rich resume schema into a flat {key: description} dict.

    Only top-level fields (no dots in the name) are included.
    This is the format expected by ``extract_document_data`` and
    ``extract_document_data_local``.
    """
    return {
        entry["name"]: entry["description"]
        for entry in DEFAULT_RESUME_SCHEMA
        if "." not in entry["name"]
    }


def load_extraction_schema() -> Dict[str, str]:
    """Return the flat extraction schema loaded from resume_extraction_schema.json.

    This is a convenience function that returns the pre-loaded
    ``DEFAULT_RESUME_EXTRACTION_SCHEMA``.
    """
    return dict(DEFAULT_RESUME_EXTRACTION_SCHEMA)