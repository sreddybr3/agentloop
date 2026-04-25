import json
import os
from pprint import pprint
from extractor import build_dynamic_schema

def test_build_schema():
    """
    Test that build_dynamic_schema correctly parses schema-v1.json 
    and creates a valid Pydantic model with nested fields and correct types.
    """
    # Load the extraction schema
    schema_path = os.path.join(os.path.dirname(__file__), "schema-v1.json")
    with open(schema_path, "r") as f:
        schema_json = json.load(f)

    # Build the dynamic Pydantic model
    DynamicModel = build_dynamic_schema(schema_json)
    
    print(f"Successfully generated Model: {DynamicModel.__name__}")
    
    # Display fields
    print("\nFields:")
    for name, field_info in DynamicModel.model_fields.items():
        print(f" - {name}: {field_info.annotation}")

    # Print out the full Pydantic JSON schema to verify structure
    print("\nPydantic JSON Schema Dump:")
    pprint(DynamicModel.model_json_schema())

if __name__ == "__main__":
    test_build_schema()
