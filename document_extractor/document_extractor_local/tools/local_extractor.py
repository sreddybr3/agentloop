"""Local document extractor: Docling (Parse) + Qwen3.5:4B (Extract).

Architecture:
  PARSE:   Docling converts PDF/DOCX/images to Markdown, tables, chunks
  EXTRACT: Qwen3.5:4B (Ollama) performs schema-driven JSON extraction

Environment variables:
    OLLAMA_BASE_URL  (default: http://localhost:11434)
    OLLAMA_MODEL     (default: qwen3.5:4b)
    OLLAMA_TIMEOUT   (default: 180)
"""
import base64, json, logging, os, tempfile, traceback
from typing import Any, Dict, List
import httpx
from docling.document_converter import DocumentConverter

logger = logging.getLogger(__name__)
_OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3.5:4b")
_REQUEST_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "180"))

def _parse_document_with_docling(source: str) -> Dict[str, Any]:
    """Use Docling to parse a document into Markdown, tables, metadata."""
    logger.info("Docling PARSE: %s", source)
    converter = DocumentConverter()
    result = converter.convert(source)
    doc = result.document
    markdown_output = doc.export_to_markdown()
    tables_data = []
    if hasattr(doc, "tables") and doc.tables:
        for i, table in enumerate(doc.tables):
            try:
                tmd = table.export_to_markdown() if hasattr(table, "export_to_markdown") else str(table)
                tables_data.append({"table_index": i, "markdown": tmd})
            except Exception as te:
                logger.warning("Table %d failed: %s", i, te)
                tables_data.append({"table_index": i, "markdown": "[failed]"})
    metadata = {
        "num_pages": len(doc.pages) if hasattr(doc, "pages") else 0,
        "num_tables": len(tables_data),
        "source": source,
    }
    chunks = []
    try:
        for item_tuple in doc.iterate_items():
            # iterate_items() yields (NodeItem, level) tuples
            item, _level = item_tuple
            ci: Dict[str, Any] = {"type": type(item).__name__}
            text_val = getattr(item, "text", None)
            export_fn = getattr(item, "export_to_markdown", None)
            if text_val is not None:
                ci["text"] = text_val
            elif callable(export_fn):
                ci["text"] = export_fn()
            else:
                ci["text"] = str(item)
            chunks.append(ci)
    except Exception as ce:
        logger.warning("Chunk iteration failed: %s", ce)
        for para in markdown_output.split("\n\n"):
            s = para.strip()
            if s:
                chunks.append({"type": "text", "text": s})
    logger.info("PARSE done: %d chars, %d tables, %d chunks", len(markdown_output), len(tables_data), len(chunks))
    return {"markdown": markdown_output, "tables": tables_data, "metadata": metadata, "chunks": chunks}


def _parse_base64_pdf_with_docling(pdf_data_base64: str) -> Dict[str, Any]:
    """Parse a base64-encoded PDF using Docling via temp file."""
    pdf_bytes = base64.b64decode(pdf_data_base64)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name
    try:
        return _parse_document_with_docling(tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

def _build_extraction_prompt(doc_md: str, schema_def: Dict[str, str]) -> str:
    """Build prompt for Qwen3.5 to return JSON matching the schema."""
    lines = []
    for k, v in schema_def.items():
        lines.append('  - "' + k + '": ' + v)
    fields = "\n".join(lines)
    p = "You are a precise document data extractor. Extract fields from the document below.\n\n"
    p += "The document was pre-parsed with layout analysis (Markdown format).\n\n"
    p += "Return ONLY a valid JSON object with these fields:\n" + fields + "\n\n"
    p += "Rules:\n- Raw JSON only, no markdown fences, no explanation.\n"
    p += "- Missing fields: empty string. Numeric fields: string. Arrays: JSON array.\n"
    p += "- Extract table cell data accurately.\n\n"
    p += "Document:\n---\n" + doc_md + "\n---\n\nJSON:"
    return p


def _build_json_schema(schema_def: Dict[str, str]) -> dict:
    """Build JSON Schema for Ollama structured output."""
    props = {k: {"type": "string", "description": v} for k, v in schema_def.items()}
    return {"type": "object", "properties": props, "required": list(schema_def.keys())}


def _call_qwen_extraction(doc_md: str, schema_def: Dict[str, str]) -> dict:
    """Call Qwen3.5:4B via Ollama for schema-driven extraction."""
    prompt = _build_extraction_prompt(doc_md, schema_def)
    jschema = _build_json_schema(schema_def)
    url = os.environ.get("OLLAMA_BASE_URL", _OLLAMA_BASE_URL).rstrip("/") + "/api/chat"
    model = os.environ.get("OLLAMA_MODEL", _OLLAMA_MODEL)
    model = os.environ.get("MODEL_NAME", "gemini-3.1-flash-lite-preview")
    logger.info("EXTRACT: model=%s doc=%d chars", model, len(doc_md))
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "format": jschema, "stream": False,
        "options": {"temperature": 0.0, "num_ctx": 4096, "max_tokens": 4096},
    }
    with httpx.Client(timeout=_REQUEST_TIMEOUT) as c:
        r = c.post(url, json=payload)
        r.raise_for_status()
    raw = r.json().get("message", {}).get("content", "")
    if not raw:
        raise ValueError("Qwen3.5 returned empty response.")
    return json.loads(raw)

def extract_document_data_local(document_text: str, schema_json_str: str) -> dict:
    """Extract structured data from text using Qwen3.5 (skip Docling parse).

    Args:
        document_text: Document text content.
        schema_json_str: JSON string of {field_name: description} pairs.
    Returns:
        dict with status and data or error_message.
    """
    logger.info("extract_document_data_local: doc=%d, schema=%d", len(document_text), len(schema_json_str))
    try:
        sd = json.loads(schema_json_str)
        if not isinstance(sd, dict):
            return {"status": "error", "error_message": "Schema must be a JSON object."}
        data = _call_qwen_extraction(document_text, sd)
        return {"status": "success", "data": data}
    except httpx.ConnectError:
        return {"status": "error", "error_message": "Cannot connect to Ollama at " + _OLLAMA_BASE_URL}
    except httpx.HTTPStatusError as e:
        return {"status": "error", "error_message": "Ollama HTTP " + str(e.response.status_code)}
    except json.JSONDecodeError as e:
        return {"status": "error", "error_message": "Invalid JSON: " + str(e)}
    except Exception as e:
        logger.error("Failed: %s\n%s", e, traceback.format_exc())
        return {"status": "error", "error_message": str(e)}


def parse_document_local(file_path: str) -> dict:
    """Parse a document with Docling (PARSE stage only).

    Args:
        file_path: Path to document (PDF, DOCX, PPTX, image).
    Returns:
        dict with markdown, tables, metadata, chunks.
    """
    logger.info("parse_document_local: %s", file_path)
    try:
        if not os.path.isfile(file_path):
            return {"status": "error", "error_message": "Not found: " + file_path}
        p = _parse_document_with_docling(file_path)
        return {"status": "success", "markdown": p["markdown"], "tables": p["tables"],
                "metadata": p["metadata"], "chunks": p["chunks"]}
    except ImportError as e:
        return {"status": "error", "error_message": str(e)}
    except Exception as e:
        logger.error("Failed: %s\n%s", e, traceback.format_exc())
        return {"status": "error", "error_message": str(e)}


def extract_from_pdf_local(pdf_file_path: str, schema_json_str: str) -> dict:
    """Extract from PDF: Docling (Parse) + Qwen3.5 (Extract).

    Args:
        pdf_file_path: Path to PDF file.
        schema_json_str: JSON string of {field_name: description} pairs.
    Returns:
        dict with status, data, parse_metadata.
    """
    logger.info("extract_from_pdf_local: %s", pdf_file_path)
    try:
        if not os.path.isfile(pdf_file_path):
            return {"status": "error", "error_message": "Not found: " + pdf_file_path}
        sd = json.loads(schema_json_str)
        if not isinstance(sd, dict):
            return {"status": "error", "error_message": "Schema must be a JSON object."}
        # STAGE 1: PARSE
        parsed = _parse_document_with_docling(pdf_file_path)
        md = parsed["markdown"]
        if not md or not md.strip():
            return {"status": "error", "error_message": "Docling extracted no content."}
        if len(md) > 15000:
            md = md[:15000] + "\n\n[... truncated ...]"
        # STAGE 2: EXTRACT
        data = _call_qwen_extraction(md, sd)
        return {"status": "success", "data": data, "parse_metadata": parsed.get("metadata", {})}
    except ImportError as e:
        return {"status": "error", "error_message": str(e)}
    except httpx.ConnectError:
        return {"status": "error", "error_message": "Cannot connect to Ollama at " + _OLLAMA_BASE_URL}
    except httpx.HTTPStatusError as e:
        return {"status": "error", "error_message": "Ollama HTTP " + str(e.response.status_code)}
    except json.JSONDecodeError as e:
        return {"status": "error", "error_message": "Invalid JSON: " + str(e)}
    except Exception as e:
        logger.error("Failed: %s\n%s", e, traceback.format_exc())
        return {"status": "error", "error_message": str(e)}


def extract_from_base64_pdf_local(pdf_data_base64: str, schema_json_str: str) -> dict:
    """Extract from base64 PDF: Docling (Parse) + Qwen3.5 (Extract).

    Args:
        pdf_data_base64: Base64-encoded PDF.
        schema_json_str: JSON string of {field_name: description} pairs.
    Returns:
        dict with status, data, parse_metadata.
    """
    logger.info("extract_from_base64_pdf_local called")
    try:
        sd = json.loads(schema_json_str)
        if not isinstance(sd, dict):
            return {"status": "error", "error_message": "Schema must be a JSON object."}
        parsed = _parse_base64_pdf_with_docling(pdf_data_base64)
        md = parsed["markdown"]
        if not md or not md.strip():
            return {"status": "error", "error_message": "Docling extracted no content."}
        if len(md) > 15000:
            md = md[:15000] + "\n\n[... truncated ...]"
        data = _call_qwen_extraction(md, sd)
        return {"status": "success", "data": data, "parse_metadata": parsed.get("metadata", {})}
    except (ValueError, ImportError) as e:
        return {"status": "error", "error_message": str(e)}
    except httpx.ConnectError:
        return {"status": "error", "error_message": "Cannot connect to Ollama."}
    except Exception as e:
        logger.error("Failed: %s\n%s", e, traceback.format_exc())
        return {"status": "error", "error_message": str(e)}