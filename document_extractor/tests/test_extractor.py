import os
import sys

import pytest

# Ensure the document_extractor package directory is on sys.path
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Load .env before importing agent so env vars (MODEL_NAME etc.) are available
_env_path = os.path.join(_project_root, ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())
                
import json
from document_extractor.tools.extractor import build_dynamic_schema, extract_document_data

def test_build_dynamic_schema():
    schema_def = {
        "name": "The name of the person",
        "age": "The age of the person"
    }
    DynamicModel = build_dynamic_schema(schema_def)
    
    # Verify the model has the correct fields
    assert "name" in DynamicModel.model_fields
    assert "age" in DynamicModel.model_fields

def test_extract_document_data_invalid_schema():
    result = extract_document_data("some document", "invalid json")
    assert result["status"] == "error"
    assert "Expecting value" in result["error_message"] or "JSONDecodeError" in result["error_message"]
