# Dynamic Document Extractor

An AI-powered document data extraction agent built with the **Google Agent Development Kit (ADK)**. The agent accepts text or PDF documents and extracts structured, schema-defined data using Google Gemini models — with strict JSON output enforced via dynamically generated Pydantic models.

---

## Use Case

Extract structured fields from any document (resume, invoice, contract, report) based on a JSON schema. The system:

- Accepts **PDF binary uploads** or **plain text string** input
- Uses the provided **extraction schema** to control what fields to extract
- Falls back to a **built-in default schema** (`schema-v1.json`) if none is provided
- Returns a **deterministic, structured JSON response** every time using `response_schema` enforcement in the Gemini API

Typical usage: resume parsing, invoice data extraction, form digitization, contract analysis.

---

## Architecture

```
HTTP Request (PDF or text + optional schema)
        │
        ▼
  FastAPI /extract endpoint  (api.py)
        │
        ▼
  ADK Runner + InMemorySessionService
        │
        ▼
  document_extractor_coordinator (Agent — agent.py)
    ├─ extract_from_pdf()     ← for PDF binary uploads
    └─ extract_document_data() ← for text string input
        │
        ▼
  build_dynamic_schema()      ← parses JSON schema → Pydantic model
        │
        ▼
  Gemini API (response_schema=<PydanticModel>) → strict JSON output
        │
        ▼
  HTTP Response: { "extraction": { ... } }
```

---

## Project Structure

```
document_extractor/
├── document_extractor/
│   ├── __init__.py
│   ├── agent.py              # ADK Agent coordinator
│   ├── api.py                # FastAPI server
│   ├── .env                  # Environment configuration
│   └── tools/
│       ├── extractor.py      # Core extraction tools + Pydantic schema builder
│       ├── schema-v1.json    # Default extraction schema (resume fields)
│       └── extraction-schema.md  # Schema format reference
├── tests/
│   └── test_extractor.py     # Unit + E2E tests
├── bruno/
│   ├── Extract_PDF.bru       # Bruno API request (PDF)
│   └── Extract_Text.bru      # Bruno API request (text)
├── pyproject.toml
└── README.md
```

---

## Prerequisites

- Python >= 3.10
- A Google Cloud project with Vertex AI enabled **OR** a Gemini API key
- `uvicorn` for running the API server

---

## Installation

```bash
# From the document_extractor/ directory
pip install -e .
```

---

## Configuration

Copy `.env.example` (or create `.env`) inside `document_extractor/document_extractor/`:

```bash
# .env
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
MODEL_NAME=gemini-3.1-flash-lite-preview
EXTRACTION_MODEL=gemini-3.1-flash-lite-preview
LOG_LEVEL=INFO
```

> Alternatively, for Gemini API key mode, set `GOOGLE_GENAI_USE_VERTEXAI=0` and `GOOGLE_API_KEY=<your-key>`.

---

## Running the Agent

### Option 1 — ADK Web UI (interactive testing)

```bash
cd document_extractor
adk web .
```

Opens the ADK web interface at `http://localhost:8000`.

### Option 2 — FastAPI REST Server

```bash
cd document_extractor
uvicorn document_extractor.api:app --host 0.0.0.0 --port 8001 --reload
```

API server starts at `http://localhost:8001`. Interactive docs available at `http://localhost:8001/docs`.

---

## API Reference

### `POST /extract`

Extract structured data from a document.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `document` | File (binary) | One of these two | PDF or binary document file upload |
| `document_str` | string (form) | One of these two | Raw text content of the document |
| `extraction_schema` | string (form) | Optional | JSON schema string to control extraction fields. Defaults to `schema-v1.json` if omitted |

**Response:**
```json
{
  "extraction": {
    "contact_information": { ... },
    "education": [ ... ],
    "professional_experience": [ ... ],
    "technical_skills": [ ... ]
  }
}
```

---

## Testing the API with cURL

### 1. Extract data from a PDF file (using default schema)

```bash
curl -X POST "http://localhost:8001/extract" \
  -H "accept: application/json" \
  -F "document=@document_extractor/tools/SriniResume.pdf;type=application/pdf"
```

### 2. Extract data from plain text (using default schema)

```bash
curl -X POST "http://localhost:8001/extract" \
  -H "accept: application/json" \
  -F "document_str=John Doe is a software engineer with 10 years of experience in Python. He graduated from Stanford University in 2014 with a B.S. in Computer Science."
```

### 3. Extract data with a custom schema override

```bash
curl -X POST "http://localhost:8001/extract" \
  -H "accept: application/json" \
  -F "document_str=Invoice INV-2024-001. Date: 2024-04-25. Total: USD 4500. Vendor: Acme Corp." \
  -F 'extraction_schema={
    "type": "object",
    "properties": {
      "invoice_number": { "type": "string", "description": "The invoice number" },
      "date": { "type": "string", "description": "Invoice date in YYYY-MM-DD format" },
      "total_amount": { "type": "string", "description": "Total amount without currency symbol" },
      "vendor_name": { "type": "string", "description": "Name of the vendor" }
    }
  }'
```

### 4. Extract from PDF with custom schema

```bash
curl -X POST "http://localhost:8001/extract" \
  -H "accept: application/json" \
  -F "document=@document_extractor/tools/SriniResume.pdf;type=application/pdf" \
  -F 'extraction_schema={
    "type": "object",
    "properties": {
      "full_name": { "type": "string", "description": "Full name of the candidate" },
      "email": { "type": "string", "description": "Email address" },
      "skills": { "type": "array", "items": { "type": "string" }, "description": "List of technical skills" }
    }
  }'
```

---

## Running Tests

```bash
# Unit tests
pytest tests/ -v

# E2E test (calls Gemini API — requires valid credentials)
pytest tests/test_extractor.py -m e2e -v -s
```

---

## Default Schema

The built-in `schema-v1.json` extracts the following fields from resumes:

- **contact_information** — name, email, phone, LinkedIn, location
- **profile_summary_points** — list of summary bullet points
- **professional_experience** — array of job roles with company, title, dates, responsibilities
- **education** — array of degrees with institution, dates, GPA, percentage
- **technical_skills** — array of skills with name, description, and category
