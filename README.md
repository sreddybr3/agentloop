# doc_search_with_reranking_validation — Multi-Agent Document Matching & Validation System

A Google ADK (Agent Development Kit) multi-agent system that matches user input paragraphs against a document corpus using a two-pass strategy (semantic search + LLM reranking), with an independent LLM Judge for result validation.

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Root Agent                      │
│  (Orchestrates matching → validation pipeline)   │
├─────────────────────┬───────────────────────────┤
│                     │                           │
│  ┌─────────────────────────┐  ┌──────────────────────────┐
│  │    Matching Agent       │  │   Validation Agent       │
│  │                         │  │   (LLM Judge)            │
│  │  Pass 1: Semantic       │  │                          │
│  │    Search (Weaviate)    │  │  Evaluates:              │
│  │                         │  │  • Relevance             │
│  │  Pass 2: LLM Reranking │  │  • Ranking quality       │
│  │    (Gemini)             │  │  • Coverage              │
│  │                         │  │  • Diversity             │
│  │  Output: Top 10 docs    │  │  • Per-doc assessment    │
│  └─────────────────────────┘  └──────────────────────────┘
│         │                              │
│    ┌────┴────┐                    ┌────┴────┐
│    │Weaviate │                    │ Gemini  │
│    │Vector DB│                    │   LLM   │
│    └─────────┘                    └─────────┘
└─────────────────────────────────────────────────┘
```

## Components

### Root Agent
Orchestrates the workflow: delegates to the Matching Agent first, then passes results to the Validation Agent, and presents the combined output.

### Matching Agent (Two-Pass Strategy)
1. **Pass 1 — Semantic Search**: Embeds the user's input using Gemini embeddings and queries the Weaviate vector store for the top 30 most similar documents.
2. **Pass 2 — LLM Reranking**: Uses Gemini LLM to rerank the candidates with nuanced relevance assessment, producing the top 10 results with scores and explanations.

### Validation Agent (LLM Judge)
Independently evaluates matching quality across dimensions: relevance, ranking quality, topic coverage, result diversity, and explanation quality. Outputs a detailed validation report.

## Prerequisites

- Python 3.11+
- [Docker](https://www.docker.com/) (for Weaviate)
- Google API Key with Gemini access

## Setup

### 1. Install Dependencies

We recommend using a virtual environment. Install the package in editable mode to ensure all dependencies are installed and the `doc_search_with_reranking_validation` module is properly discoverable by the ADK CLI:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and set your GOOGLE_API_KEY
```

### 3. Start Weaviate

```bash
docker-compose up -d
```

This starts a local Weaviate instance at `http://localhost:8080`.

### 4. Ingest Sample Documents

```bash
python scripts/ingest_sample_documents.py
```

This creates 30 sample documents covering topics like AI/ML, databases, cloud computing, DevOps, and more. Each document is embedded using Gemini and stored in Weaviate.

## Running the Agent

### Interactive Mode (ADK Web UI)

Ensure you are in the project root directory and your virtual environment is activated, then run:

```bash
adk web .
```

### CLI Mode

```bash
adk run .
```

### Example Query

```
Find documents related to: "I'm building a system that needs to process 
and understand large volumes of text documents. The system should be able 
to find semantically similar content, support real-time queries, and 
integrate with a language model for more accurate results. I'm considering 
using vector databases and RAG patterns."
```

The system will:
1. **Matching Agent** performs semantic search → finds 30 candidates → reranks to top 10
2. **Validation Agent** evaluates the matching quality and produces a validation report
3. **Root Agent** presents both outputs together

## Project Structure

```
doc_search_with_reranking_validation/
├── __init__.py
├── agent.py                    # ADK entry point (exposes root_agent)
├── config.py                   # Configuration settings
├── vector_store.py             # Weaviate vector store operations
├── root_agent.py               # Root orchestrator agent
├── matching_agent.py           # Two-pass matching agent
├── validation_agent.py         # LLM judge validation agent
└── tools/
    ├── __init__.py
    ├── matching_tools.py       # search_documents, rerank_documents, format_matching_results
    └── validation_tools.py     # validate_matching_results, format_validation_report
scripts/
    └── ingest_sample_documents.py  # Sample document ingestion
docker-compose.yml              # Weaviate container
pyproject.toml                  # Project dependencies
.env.example                    # Environment variable template
```

## Customization

### Adding Your Own Documents

Documents should be dictionaries with:
```python
{
    "doc_id": "unique-id",
    "title": "Document Title",
    "content": "Full document text content...",
    "source": "Source reference",
    "metadata": {"key": "value"}  # Optional
}
```

Use `doc_search_with_reranking_validation.vector_store.ingest_documents(docs)` to add them.

### Configuration

Edit `doc_search_with_reranking_validation/config.py` or set environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_API_KEY` | — | Google AI API key (required) |
| `GEMINI_MODEL` | `gemini-1.5-flash` | LLM model for reranking and validation |
| `EMBEDDING_MODEL` | `text-embedding-004` | Model for document embeddings |
| `WEAVIATE_URL` | `http://localhost:8080` | Weaviate server URL |
| `TOP_K_FIRST_PASS` | `30` | Candidates from semantic search |
| `TOP_K_FINAL` | `10` | Final results after reranking |