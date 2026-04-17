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
