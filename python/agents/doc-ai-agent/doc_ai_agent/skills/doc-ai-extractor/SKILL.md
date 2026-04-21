---
name: doc-ai-extractor
description: Extract structured key-value pairs in JSON format from unstructured PDF documents using AI. Use when you need to parse invoices, contracts, forms, or any PDF document to extract specific fields based on a provided schema.
license: Apache-2.0
compatibility: Requires Python 3.10+ and PDF processing capabilities
metadata:
  author: agentloop
  version: "1.0"
---

# Document AI Extractor

Extract structured data from unstructured PDF documents using AI-powered extraction.

## Overview

This skill accepts a PDF document and an extraction schema, then returns structured JSON output containing the extracted key-value pairs.

## Input Requirements

### 1. Input Document
- **Format**: PDF file
- **Provided as**: File path or base64-encoded content

### 2. Extraction Schema

The extraction schema is a JSON object that defines what data to extract:

```json
{
  "keys": [
    {
      "name": "invoice_number",
      "key_type": "field",
      "data_type": "string",
      "description": "The unique invoice identifier"
    },
    {
      "name": "total_amount",
      "key_type": "field",
      "data_type": "number",
      "description": "The total invoice amount"
    },
    {
      "name": "line_items",
      "key_type": "list",
      "data_type": "string",
      "description": "List of items on the invoice"
    }
  ],
  "mandatory_keys": ["invoice_number", "total_amount"]
}
```

#### Schema Field Definitions

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | The key name for the extracted value |
| `key_type` | Yes | Either `field` (single value) or `list` (array of values) |
| `data_type` | Yes | Either `string` or `number` |
| `description` | Yes | Description to help AI understand what to extract |

#### Key Type Values
- **`field`**: Extract a single value (e.g., invoice number, date, name)
- **`list`**: Extract multiple values as an array (e.g., line items, addresses)

#### Data Type Values
- **`string`**: Text values (names, identifiers, descriptions)
- **`number`**: Numeric values (amounts, quantities, percentages)

## Processing Rules

1. **Parse the PDF** document to extract text content
2. **Analyze content** against the provided schema
3. **Extract values** for each key defined in the schema
4. **Validate mandatory keys** - if any mandatory key cannot be extracted, return an error response instead of partial data
5. **Return structured JSON** output

## Output Format

### Successful Extraction

```json
{
  "status": "success",
  "extracted_data": {
    "invoice_number": "INV-2024-001",
    "total_amount": 1250.00,
    "line_items": ["Widget A", "Widget B", "Service Fee"]
  },
  "metadata": {
    "document_pages": 2,
    "extraction_confidence": "high"
  }
}
```

### Failed Extraction (Missing Mandatory Keys)

```json
{
  "status": "error",
  "error_code": "MANDATORY_KEYS_MISSING",
  "message": "Could not extract required mandatory keys",
  "missing_keys": ["invoice_number"],
  "extracted_data": null
}
```

## Usage Instructions

### Step 1: Prepare the Extraction Schema

Define the keys you want to extract from the document:

```python
extraction_schema = {
    "keys": [
        {
            "name": "company_name",
            "key_type": "field",
            "data_type": "string",
            "description": "Name of the company or organization"
        },
        {
            "name": "invoice_date",
            "key_type": "field", 
            "data_type": "string",
            "description": "Date of the invoice in any format"
        },
        {
            "name": "amount_due",
            "key_type": "field",
            "data_type": "number",
            "description": "Total amount due or payable"
        }
    ],
    "mandatory_keys": ["company_name", "amount_due"]
}
```

### Step 2: Invoke the Extractor

Provide the PDF document path and schema to the extraction function.

### Step 3: Handle the Response

- If `status` is `"success"`, use the `extracted_data` object
- If `status` is `"error"`, check `missing_keys` and handle accordingly

## Example Scenarios

### Invoice Extraction

**Schema:**
```json
{
  "keys": [
    {"name": "vendor_name", "key_type": "field", "data_type": "string", "description": "Name of the vendor or seller"},
    {"name": "invoice_number", "key_type": "field", "data_type": "string", "description": "Invoice reference number"},
    {"name": "invoice_date", "key_type": "field", "data_type": "string", "description": "Date of invoice"},
    {"name": "due_date", "key_type": "field", "data_type": "string", "description": "Payment due date"},
    {"name": "subtotal", "key_type": "field", "data_type": "number", "description": "Subtotal before tax"},
    {"name": "tax_amount", "key_type": "field", "data_type": "number", "description": "Tax amount"},
    {"name": "total_amount", "key_type": "field", "data_type": "number", "description": "Total amount due"},
    {"name": "line_items", "key_type": "list", "data_type": "string", "description": "List of items/services"}
  ],
  "mandatory_keys": ["vendor_name", "invoice_number", "total_amount"]
}
```

### Contract Extraction

**Schema:**
```json
{
  "keys": [
    {"name": "party_a", "key_type": "field", "data_type": "string", "description": "First party name"},
    {"name": "party_b", "key_type": "field", "data_type": "string", "description": "Second party name"},
    {"name": "effective_date", "key_type": "field", "data_type": "string", "description": "Contract start date"},
    {"name": "termination_date", "key_type": "field", "data_type": "string", "description": "Contract end date"},
    {"name": "contract_value", "key_type": "field", "data_type": "number", "description": "Total contract value"},
    {"name": "key_terms", "key_type": "list", "data_type": "string", "description": "Important contract terms"}
  ],
  "mandatory_keys": ["party_a", "party_b", "effective_date"]
}
```

## Edge Cases

- **Empty PDF**: Return error with code `EMPTY_DOCUMENT`
- **Corrupted PDF**: Return error with code `INVALID_DOCUMENT`
- **No matching data**: Return success with `null` values for non-mandatory fields
- **Ambiguous data**: Use AI confidence scoring to select best match
- **Multiple matches for field type**: Return the most relevant/prominent value
