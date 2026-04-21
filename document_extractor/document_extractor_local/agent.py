import base64
import io
import logging
import os
from google.adk.agents import Agent
from .tools.local_extractor import extract_document_data_local, extract_from_pdf_local
from google.adk.models.lite_llm import LiteLlm
from dotenv import load_dotenv
from google.genai import types

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
LLM_MODEL = os.getenv("LM_MODEL", "lm_studio/gemma-4-e2b")
LLM_BASE_URL = os.getenv("LM_BASE_URL", "http://localhost:1234/v1")

logger = logging.getLogger(__name__)

SHORT_CONFIG = types.GenerateContentConfig(
    temperature=0.3,
    top_p=1.0,
    max_output_tokens=512,
)
# ══════════════════════════════════════════════════════════════════════════
# PDF EXTRACTION TOOL
# ══════════════════════════════════════════════════════════════════════════
# When the user uploads a PDF via ADK web UI, the file arrives as base64-
# encoded inline_data in the message. The LLM cannot parse PDF binary, so
# this tool extracts plain text using PyPDF2.
#
# The tool accepts base64-encoded PDF data and returns extracted text.
# It also handles direct file paths as a fallback for testing.

def extract_text_from_pdf(pdf_data_base64: str) -> dict:
    """Extract text content from a base64-encoded PDF document.

    Args:
        pdf_data_base64: Base64-encoded PDF file content. This is the raw
            base64 string from the uploaded PDF file.

    Returns:
        A dictionary with 'status' and 'text' if successful, or 'error_message'.
    """
    try:
        from PyPDF2 import PdfReader

        # Decode the base64 data
        try:
            pdf_bytes = base64.b64decode(pdf_data_base64)
        except Exception as decode_err:
            logger.error(f"Failed to decode base64 PDF data: {decode_err}")
            return {"status": "error", "error_message": f"Could not decode the PDF data: {decode_err}"}

        # Read the PDF
        pdf_file = io.BytesIO(pdf_bytes)
        reader = PdfReader(pdf_file)

        # Extract text from all pages (cap at 50 pages to avoid huge context)
        max_pages = min(len(reader.pages), 50)
        text_parts = []
        for i in range(max_pages):
            page_text = reader.pages[i].extract_text()
            if page_text:
                text_parts.append(page_text.strip())

        if not text_parts:
            return {"status": "error", "error_message": "The PDF appears to contain no extractable text. It may be a scanned image."}

        full_text = "\n\n".join(text_parts)

        # Truncate if excessively long (protect context window)
        max_chars = 15000
        if len(full_text) > max_chars:
            full_text = full_text[:max_chars] + "\n\n[... truncated — resume exceeds 15,000 characters ...]"
            logger.warning(f"PDF text truncated from {len(full_text)} to {max_chars} chars")

        logger.info(f"Successfully extracted {len(full_text)} chars from {max_pages} PDF pages")
        return {"status": "success", "text": full_text}

    except ImportError:
        logger.error("PyPDF2 not installed")
        return {"status": "error", "error_message": "PDF processing library (PyPDF2) is not installed. Please run: pip install PyPDF2>=3.0.0"}
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return {"status": "error", "error_message": f"Error extracting text from PDF: {str(e)}"}

root_agent = Agent(
    name="document_extractor_coordinator",
    model=LiteLlm(
        model=LLM_MODEL,
        base_url=LLM_BASE_URL,
    ),
    generate_content_config=SHORT_CONFIG,
    description="Agent that coordinates dynamic document extraction from text or PDF files.",
    instruction="""You are a dynamic document extraction coordinator.
Your goal is to help users extract structured data from documents.

When a user uploads a PDF, you must first extract the text from it, then you
can extract the data from the text.

You have the following tools available:
- `extract_text_from_pdf` - Extracts text from a base64-encoded PDF.
- `extract_document_data_local` - Extracts structured data from plain text.

Follow these rules to decide which tool to use:
1. If the user uploads a PDF, its content will be in a base64-encoded string.
   a. First, call `extract_text_from_pdf` to get the text.
   b. If the tool returns a "success" status, take the 'text' field from the
      result and call `extract_document_data_local` with that text.
2. If the user provides raw document text, call `extract_document_data_local`.

After the final tool returns, inspect its result:
- If status is "success", format the "data" object as pretty-printed JSON and
  return it.
- If status is "error", report the error_message to the user.
""",
    tools=[
        extract_text_from_pdf,
        extract_document_data_local,
    ],
)
