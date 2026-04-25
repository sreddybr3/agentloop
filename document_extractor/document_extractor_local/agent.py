"""Document Extractor Agent using Docling (Parse) + Qwen3.5:4B (Extract).

Architecture:
  - Docling handles PARSE: PDF/DOCX/images -> structured Markdown, tables, chunks
  - Qwen3.5:4B handles EXTRACT: schema-driven JSON extraction from parsed content
  - Agent (Qwen3.5 via LiteLlm) orchestrates the tools

This is an ADE-like (Agentic Document Extraction) pipeline:
  1. Parse: Document -> structured Markdown + metadata (Docling)
  2. Extract: Markdown + schema -> structured JSON (Qwen3.5)
"""
import base64
import io
import logging
import os

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.genai import types
from dotenv import load_dotenv

from .tools.local_extractor import (
    extract_document_data_local,
    extract_from_pdf_local,
    extract_from_base64_pdf_local,
    parse_document_local,
)

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Agent LLM config - Qwen3.5:4B via Ollama (OpenAI-compatible endpoint)
LLM_MODEL = os.getenv("LM_MODEL", "ollama/qwen3.5:4b")
LLM_BASE_URL = os.getenv("LM_BASE_URL", "http://localhost:11434")

logger = logging.getLogger(__name__)

SHORT_CONFIG = types.GenerateContentConfig(
    temperature=0.3,
    top_p=1.0,
    max_output_tokens=512,
)


# ============================================================================
# PDF TEXT EXTRACTION TOOL (for base64 uploads via ADK web UI)
# ============================================================================

def extract_text_from_pdf(pdf_data_base64: str) -> dict:
    """Parse a base64-encoded PDF using Docling and return structured Markdown.

    This tool uses Docling for document parsing, which provides:
    - Layout analysis (headers, paragraphs, lists)
    - Table structure recognition
    - OCR for scanned documents
    - Element detection (text, tables, figures)

    Args:
        pdf_data_base64: Base64-encoded PDF file content from upload.

    Returns:
        A dict with 'status' and 'text' (Markdown) if successful, or 'error_message'.
    """
    try:
        result = extract_from_base64_pdf_local(
            pdf_data_base64,
            '{}',  # Empty schema - just parse, no extraction
        )

        # If the tool was called with empty schema, fall back to parse-only
        parse_result = parse_document_local_from_base64(pdf_data_base64)
        if parse_result["status"] == "success":
            text = parse_result["markdown"]
            # Truncate if excessively long
            max_chars = 15000
            if len(text) > max_chars:
                text = text[:max_chars] + "\n\n[... truncated ...]"
            logger.info("Docling parsed %d chars from PDF", len(text))
            return {"status": "success", "text": text}
        else:
            return parse_result

    except Exception as e:
        logger.error("PDF parsing failed: %s", e)
        # Fallback to PyPDF2 if Docling fails
        return _fallback_pdf_extract(pdf_data_base64)


def parse_document_local_from_base64(pdf_data_base64: str) -> dict:
    """Parse base64 PDF with Docling (helper for extract_text_from_pdf)."""
    import tempfile
    try:
        pdf_bytes = base64.b64decode(pdf_data_base64)
    except Exception as e:
        return {"status": "error", "error_message": "Bad base64: " + str(e)}

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name
    try:
        return parse_document_local(tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _fallback_pdf_extract(pdf_data_base64: str) -> dict:
    """Fallback PDF text extraction using PyPDF2 when Docling is unavailable."""
    try:
        from PyPDF2 import PdfReader
        pdf_bytes = base64.b64decode(pdf_data_base64)
        pdf_file = io.BytesIO(pdf_bytes)
        reader = PdfReader(pdf_file)
        max_pages = min(len(reader.pages), 50)
        text_parts = []
        for i in range(max_pages):
            page_text = reader.pages[i].extract_text()
            if page_text:
                text_parts.append(page_text.strip())
        if not text_parts:
            return {"status": "error", "error_message": "No extractable text in PDF."}
        full_text = "\n\n".join(text_parts)
        if len(full_text) > 15000:
            full_text = full_text[:15000] + "\n\n[... truncated ...]"
        return {"status": "success", "text": full_text}
    except ImportError:
        return {"status": "error", "error_message": "Neither Docling nor PyPDF2 installed."}
    except Exception as e:
        return {"status": "error", "error_message": "PDF fallback failed: " + str(e)}


# ============================================================================
# AGENT DEFINITION
# ============================================================================
_model = os.environ.get("MODEL_NAME", "gemini-3.1-flash-lite-preview")
_model = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")
_model = LiteLlm(model="ollama_chat/qwen3.5:4b")
_model = os.environ.get("MODEL_NAME", "gemini-3.1-flash-lite-preview")

root_agent = Agent(
    name="document_extractor_coordinator",
    model=_model,
    generate_content_config=SHORT_CONFIG,
    description="Agent that extracts structured data from documents using Docling + Qwen3.5.",
    instruction="""You are a document extraction coordinator using a two-stage pipeline:
  1. PARSE: Docling converts documents into structured Markdown with layout analysis
  2. EXTRACT: Qwen3.5 extracts specific fields based on a schema

You have these tools:
- `extract_text_from_pdf` - Parses a base64-encoded PDF using Docling into Markdown.
- `extract_document_data_local` - Extracts schema-driven fields from plain text via Qwen3.5.
- `extract_from_pdf_local` - Full pipeline: Docling parses PDF + Qwen3.5 extracts fields.
- `parse_document_local` - Parse a document file into Markdown, tables, and chunks (Docling only).

Follow these rules:
1. If the user uploads a PDF (base64-encoded):
   a. If they want specific fields extracted, call `extract_from_pdf_local` with the file path
      and the schema. This runs both PARSE and EXTRACT stages automatically.
   b. If they just want to see the document content, call `extract_text_from_pdf` to get Markdown.
   c. If the PDF is base64 and they want fields, first call `extract_text_from_pdf` to parse it,
      then call `extract_document_data_local` with the parsed text and the schema.

2. If the user provides raw document text and wants fields extracted:
   a. Call `extract_document_data_local` with the text and schema.

3. If the user provides a file path to a document:
   a. For extraction: call `extract_from_pdf_local` with the path and schema.
   b. For parsing only: call `parse_document_local` with the path.

After the tool returns:
- If status is "success", format the "data" as pretty-printed JSON and return it.
- If status is "error", report the error_message to the user.

The Docling parser handles complex layouts including:
- Tables with merged cells
- Multi-column layouts
- Headers, footers, page numbers
- Form fields and checkboxes
- Mixed text and image content
""",
    tools=[
        extract_text_from_pdf,
        extract_document_data_local,
        extract_from_pdf_local,
        parse_document_local,
    ],
)