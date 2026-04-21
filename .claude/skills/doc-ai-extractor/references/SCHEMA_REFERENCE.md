# Schema Reference Guide

This document provides detailed information about the extraction schema format.

## Complete Schema Structure

```json
{
  "keys": [
    {
      "name": "string",
      "key_type": "field | list",
      "data_type": "string | number",
      "description": "string"
    }
  ],
  "mandatory_keys": ["key_name_1", "key_name_2"]
}
```

## Field Definitions

### `keys` (required)

An array of key definitions. Each key represents a piece of data to extract.

### `keys[].name` (required)

- **Type**: string
- **Format**: lowercase letters, numbers, and underscores
- **Example**: `"invoice_number"`, `"total_amount"`, `"line_items"`

### `keys[].key_type` (required)

Determines whether to extract a single value or multiple values.

| Value | Description | Output Type |
|-------|-------------|-------------|
| `field` | Extract a single value | Scalar (string or number) |
| `list` | Extract multiple values | Array of values |

### `keys[].data_type` (required)

Specifies the expected data type.

| Value | Description | Examples |
|-------|-------------|----------|
| `string` | Text values | `"INV-001"`, `"John Doe"`, `"2024-01-15"` |
| `number` | Numeric values | `1250.00`, `42`, `0.15` |

### `keys[].description` (required)

A human-readable description that helps the AI understand what to extract. Be specific and include context clues.

**Good descriptions:**
- `"The unique invoice identifier, usually starting with INV-"`
- `"Total amount due including tax, found near bottom of document"`
- `"Customer's full name as appears on the document"`

**Poor descriptions:**
- `"Invoice number"` (too vague)
- `"Amount"` (ambiguous - which amount?)

### `mandatory_keys` (optional)

An array of key names that **must** be successfully extracted. If any mandatory key cannot be found, the extraction fails with an error response.

```json
{
  "mandatory_keys": ["invoice_number", "total_amount", "vendor_name"]
}
```

## Common Schema Patterns

### Invoice Schema

```json
{
  "keys": [
    {"name": "vendor_name", "key_type": "field", "data_type": "string", "description": "Name of the company issuing the invoice"},
    {"name": "vendor_address", "key_type": "field", "data_type": "string", "description": "Full address of the vendor"},
    {"name": "invoice_number", "key_type": "field", "data_type": "string", "description": "Unique invoice reference number"},
    {"name": "invoice_date", "key_type": "field", "data_type": "string", "description": "Date the invoice was issued"},
    {"name": "due_date", "key_type": "field", "data_type": "string", "description": "Payment due date"},
    {"name": "customer_name", "key_type": "field", "data_type": "string", "description": "Name of the customer being billed"},
    {"name": "subtotal", "key_type": "field", "data_type": "number", "description": "Sum before tax"},
    {"name": "tax_rate", "key_type": "field", "data_type": "number", "description": "Tax percentage applied"},
    {"name": "tax_amount", "key_type": "field", "data_type": "number", "description": "Total tax amount"},
    {"name": "total_amount", "key_type": "field", "data_type": "number", "description": "Grand total including tax"},
    {"name": "line_items", "key_type": "list", "data_type": "string", "description": "Individual items or services billed"}
  ],
  "mandatory_keys": ["vendor_name", "invoice_number", "total_amount"]
}
```

### Resume/CV Schema

```json
{
  "keys": [
    {"name": "full_name", "key_type": "field", "data_type": "string", "description": "Candidate's full name"},
    {"name": "email", "key_type": "field", "data_type": "string", "description": "Email address"},
    {"name": "phone", "key_type": "field", "data_type": "string", "description": "Phone number"},
    {"name": "location", "key_type": "field", "data_type": "string", "description": "City, state/country"},
    {"name": "summary", "key_type": "field", "data_type": "string", "description": "Professional summary or objective"},
    {"name": "skills", "key_type": "list", "data_type": "string", "description": "Technical and soft skills"},
    {"name": "work_experience", "key_type": "list", "data_type": "string", "description": "Previous job titles and companies"},
    {"name": "education", "key_type": "list", "data_type": "string", "description": "Degrees and institutions"},
    {"name": "years_experience", "key_type": "field", "data_type": "number", "description": "Total years of professional experience"}
  ],
  "mandatory_keys": ["full_name", "email"]
}
```

### Receipt Schema

```json
{
  "keys": [
    {"name": "store_name", "key_type": "field", "data_type": "string", "description": "Name of the store or merchant"},
    {"name": "store_address", "key_type": "field", "data_type": "string", "description": "Store location"},
    {"name": "transaction_date", "key_type": "field", "data_type": "string", "description": "Date of purchase"},
    {"name": "transaction_time", "key_type": "field", "data_type": "string", "description": "Time of purchase"},
    {"name": "items_purchased", "key_type": "list", "data_type": "string", "description": "List of items bought"},
    {"name": "payment_method", "key_type": "field", "data_type": "string", "description": "How payment was made (cash, card, etc.)"},
    {"name": "subtotal", "key_type": "field", "data_type": "number", "description": "Total before tax"},
    {"name": "tax", "key_type": "field", "data_type": "number", "description": "Tax amount"},
    {"name": "total", "key_type": "field", "data_type": "number", "description": "Final total paid"}
  ],
  "mandatory_keys": ["store_name", "total"]
}
```

## Validation Rules

1. **All keys must have unique names** within the same schema
2. **Mandatory keys must exist** in the keys array
3. **key_type must be** either `"field"` or `"list"`
4. **data_type must be** either `"string"` or `"number"`
5. **description cannot be empty**
