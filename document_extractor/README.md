# Dynamic Document Extractor

This project implements an ADK agent that uses the Google Gemini `gemini-3.1-flash-preview` model for deterministic structured document extraction.

The agent handles dynamic schemas by building a Pydantic model at runtime based on the user-provided JSON object containing keys and descriptions. This dynamically generated strict Pydantic model is then passed to the Google GenAI API to ensure deterministic JSON extraction.

## Prerequisites

- Python >= 3.10
- Set your Google Cloud or Gemini API credentials in the `.env` file (copy from `.env.example`).

## Installation

You can install the dependencies via `pip`:

```bash
pip install -e .
```

## Running the Agent

You can test the extraction script using:

```bash
python run_extraction.py
```

Alternatively, you can run the agent in the ADK interactive console:

```bash
adk run document_extractor
```

## Testing and Evaluation

Run the unit tests:

```bash
pytest tests/
```

Run the ADK evaluation dataset to test tool usage trajectory:

```bash
pytest eval/
```
