# Document AI Extractor Agent

This agent uses a skill to extract structured key-value pairs from PDF documents based on a provided JSON schema.

## Prerequisites

- Python 3.10+
- Google Cloud SDK authenticated (if using Vertex AI)

## Setup

1.  **Install Dependencies**:
    ```bash
    cd python/agents/doc-ai-agent
    pip install -e .
    ```

2.  **Configure Environment**:
    - Copy the example environment file:
      ```bash
      cp .env.example .env
      ```
    - Edit the `.env` file to add your Google Cloud Project ID or API key.

## Running the Agent

You can run the agent in several modes:

-   **Interactive CLI**:
    ```bash
    adk run doc_ai_agent
    ```

-   **Web UI**:
    ```bash
    adk web .
    ```

-   **API Server**:
    ```bash
    adk api_server .
    ```

## Example Interaction

Once the agent is running, you can provide it with a path to a PDF file and an extraction schema.

**User**:
```
Extract data from the document at '/path/to/invoice.pdf' using the following schema:
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
    }
  ],
  "mandatory_keys": ["invoice_number", "total_amount"]
}