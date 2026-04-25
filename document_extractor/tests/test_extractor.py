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
from document_extractor.tools.extractor import build_dynamic_schema, extract_document_data, extract_from_pdf

def test_build_dynamic_schema():
    schema_def = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "The name of the person"},
            "age": {"type": "integer", "description": "The age of the person"}
        }
    }
    DynamicModel = build_dynamic_schema(schema_def)
    
    # Verify the model has the correct fields
    assert "name" in DynamicModel.model_fields
    assert "age" in DynamicModel.model_fields

def test_extract_document_data_invalid_schema():
    result = extract_document_data("some document", "invalid json")
    assert result["status"] == "error"
    assert "Expecting value" in result["error_message"] or "JSONDecodeError" in result["error_message"]

@pytest.mark.e2e
def test_extract_from_pdf_srini_resume():
    """Test full extraction from SriniResume.pdf using the default schema fallback."""
    tools_dir = os.path.join(_project_root, "document_extractor", "tools")
    pdf_path = os.path.join(tools_dir, "SriniResume.pdf")
    
    # Passing None makes it automatically use the default schema-v1.json inside tools/
    result = extract_from_pdf(pdf_path, None)
    
    assert result["status"] == "success", f"Extraction failed: {result.get('error_message')}"
    data = result["data"]
    
    # Verify strict schema extraction elements exist
    assert "contact_information" in data
    assert "education" in data
    assert "technical_skills" in data
    assert "professional_experience" in data
    
    # Based on the latest schema updates, education and technical_skills are lists (arrays)
    if data.get("education"):
        assert isinstance(data["education"], list)
    if data.get("technical_skills"):
        assert isinstance(data["technical_skills"], list)
