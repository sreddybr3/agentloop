"""Tests for document_extractor_local/tools/local_extractor.py"""
import base64, json, os, sys, tempfile
from unittest.mock import MagicMock, Mock, patch
import pytest

_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

_env_path = os.path.join(_project_root, ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())

from document_extractor_local.tools.local_extractor import (
    _build_extraction_prompt, _build_json_schema, _call_qwen_extraction,
    extract_document_data_local, extract_from_base64_pdf_local,
    extract_from_pdf_local, parse_document_local,
)

SCHEMA = {"name": "Full name", "email": "Email address"}
SCHEMA_JSON = json.dumps(SCHEMA)
DOC = "John Doe\njohn@example.com\nEngineer"
PARSED = {
    "markdown": "# Resume\nJohn Doe\njohn@example.com",
    "tables": [],
    "metadata": {"num_pages": 1, "num_tables": 0, "source": "/tmp/t.pdf"},
    "chunks": [{"type": "TextItem", "text": "John Doe"}],
}
EXT = {"name": "John Doe", "email": "john@example.com"}
M = "document_extractor_local.tools.local_extractor"


def _resp(data):
    r = Mock(status_code=200)
    r.json.return_value = {"message": {"content": json.dumps(data)}}
    r.raise_for_status = Mock()
    return r


def _ctx(resp):
    ci = MagicMock()
    ci.post.return_value = resp
    c = MagicMock()
    c.__enter__ = Mock(return_value=ci)
    c.__exit__ = Mock(return_value=False)
    return c


class TestBuildExtractionPrompt:
    def test_fields(self):
        p = _build_extraction_prompt("doc", SCHEMA)
        assert '"name"' in p and "Full name" in p

    def test_document(self):
        assert "content" in _build_extraction_prompt("content", SCHEMA)

    def test_json(self):
        assert "JSON" in _build_extraction_prompt("d", SCHEMA)


class TestBuildJsonSchema:
    def test_structure(self):
        s = _build_json_schema(SCHEMA)
        assert s["type"] == "object"
        assert set(s["properties"]) == {"name", "email"}
        assert set(s["required"]) == {"name", "email"}

    def test_types(self):
        s = _build_json_schema(SCHEMA)
        assert s["properties"]["name"]["type"] == "string"

    def test_empty(self):
        s = _build_json_schema({})
        assert s["properties"] == {} and s["required"] == []


class TestCallQwenExtraction:
    @patch(f"{M}.httpx.Client")
    def test_ok(self, mc):
        mc.return_value = _ctx(_resp(EXT))
        assert _call_qwen_extraction("t", SCHEMA) == EXT

    @patch(f"{M}.httpx.Client")
    def test_empty(self, mc):
        r = Mock()
        r.json.return_value = {"message": {"content": ""}}
        r.raise_for_status = Mock()
        mc.return_value = _ctx(r)
        with pytest.raises(ValueError):
            _call_qwen_extraction("t", SCHEMA)

    @patch(f"{M}.httpx.Client")
    def test_bad_json(self, mc):
        r = Mock()
        r.json.return_value = {"message": {"content": "{x"}}
        r.raise_for_status = Mock()
        mc.return_value = _ctx(r)
        with pytest.raises(json.JSONDecodeError):
            _call_qwen_extraction("t", SCHEMA)


class TestExtractDocumentDataLocal:
    @patch(f"{M}._call_qwen_extraction", return_value=EXT)
    def test_ok(self, mq):
        r = extract_document_data_local(DOC, SCHEMA_JSON)
        assert r["status"] == "success" and r["data"] == EXT

    def test_bad_schema(self):
        r = extract_document_data_local(DOC, "bad")
        assert r["status"] == "error"

    def test_list_schema(self):
        r = extract_document_data_local(DOC, "[1]")
        assert r["status"] == "error"

    @patch(f"{M}._call_qwen_extraction")
    def test_conn_err(self, mq):
        import httpx as h
        mq.side_effect = h.ConnectError("x")
        r = extract_document_data_local(DOC, SCHEMA_JSON)
        assert r["status"] == "error" and "connect" in r["error_message"].lower()

    @patch(f"{M}._call_qwen_extraction")
    def test_http_err(self, mq):
        import httpx as h
        req = h.Request("POST", "http://x")
        mq.side_effect = h.HTTPStatusError("e", request=req, response=h.Response(500, request=req))
        r = extract_document_data_local(DOC, SCHEMA_JSON)
        assert r["status"] == "error" and "500" in r["error_message"]

    @patch(f"{M}._call_qwen_extraction", side_effect=ValueError("empty"))
    def test_val_err(self, mq):
        r = extract_document_data_local(DOC, SCHEMA_JSON)
        assert r["status"] == "error"


class TestParseDocumentLocal:
    def test_not_found(self):
        r = parse_document_local("/no/doc.pdf")
        assert r["status"] == "error"

    @patch(f"{M}._parse_document_with_docling", return_value=PARSED)
    @patch(f"{M}.os.path.isfile", return_value=True)
    def test_ok(self, _f, _p):
        r = parse_document_local("/tmp/t.pdf")
        assert r["status"] == "success" and r["markdown"] == PARSED["markdown"]

    @patch(f"{M}._parse_document_with_docling", side_effect=ImportError("no docling"))
    @patch(f"{M}.os.path.isfile", return_value=True)
    def test_import_err(self, _f, _p):
        r = parse_document_local("/tmp/t.pdf")
        assert r["status"] == "error"

    @patch(f"{M}._parse_document_with_docling", side_effect=RuntimeError("boom"))
    @patch(f"{M}.os.path.isfile", return_value=True)
    def test_runtime_err(self, _f, _p):
        r = parse_document_local("/tmp/t.pdf")
        assert r["status"] == "error" and "boom" in r["error_message"]


class TestExtractFromPdfLocal:
    def test_not_found(self):
        r = extract_from_pdf_local("/no.pdf", SCHEMA_JSON)
        assert r["status"] == "error"

    def test_bad_schema(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"fake")
            p = f.name
        try:
            assert extract_from_pdf_local(p, "bad")["status"] == "error"
        finally:
            os.unlink(p)

    def test_list_schema(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"fake")
            p = f.name
        try:
            assert extract_from_pdf_local(p, "[1]")["status"] == "error"
        finally:
            os.unlink(p)

    @patch(f"{M}._call_qwen_extraction", return_value=EXT)
    @patch(f"{M}._parse_document_with_docling", return_value=PARSED)
    @patch(f"{M}.os.path.isfile", return_value=True)
    def test_ok(self, _f, _p, _q):
        r = extract_from_pdf_local("/tmp/t.pdf", SCHEMA_JSON)
        assert r["status"] == "success" and r["data"] == EXT

    @patch(f"{M}._parse_document_with_docling")
    @patch(f"{M}.os.path.isfile", return_value=True)
    def test_empty_md(self, _f, mp):
        mp.return_value = {**PARSED, "markdown": ""}
        r = extract_from_pdf_local("/tmp/t.pdf", SCHEMA_JSON)
        assert r["status"] == "error"

    @patch(f"{M}._parse_document_with_docling")
    @patch(f"{M}.os.path.isfile", return_value=True)
    def test_ws_only(self, _f, mp):
        mp.return_value = {**PARSED, "markdown": "  \n "}
        r = extract_from_pdf_local("/tmp/t.pdf", SCHEMA_JSON)
        assert r["status"] == "error"

    @patch(f"{M}._call_qwen_extraction", return_value=EXT)
    @patch(f"{M}._parse_document_with_docling")
    @patch(f"{M}.os.path.isfile", return_value=True)
    def test_truncation(self, _f, mp, mq):
        mp.return_value = {**PARSED, "markdown": "x" * 20000}
        r = extract_from_pdf_local("/tmp/t.pdf", SCHEMA_JSON)
        assert r["status"] == "success"
        assert len(mq.call_args[0][0]) < 20000

    @patch(f"{M}._call_qwen_extraction")
    @patch(f"{M}._parse_document_with_docling", return_value=PARSED)
    @patch(f"{M}.os.path.isfile", return_value=True)
    def test_conn_err(self, _f, _p, mq):
        import httpx as h
        mq.side_effect = h.ConnectError("x")
        assert extract_from_pdf_local("/tmp/t.pdf", SCHEMA_JSON)["status"] == "error"

    @patch(f"{M}._call_qwen_extraction")
    @patch(f"{M}._parse_document_with_docling", return_value=PARSED)
    @patch(f"{M}.os.path.isfile", return_value=True)
    def test_http_err(self, _f, _p, mq):
        import httpx as h
        req = h.Request("POST", "http://x")
        mq.side_effect = h.HTTPStatusError("e", request=req, response=h.Response(503, request=req))
        assert extract_from_pdf_local("/tmp/t.pdf", SCHEMA_JSON)["status"] == "error"


class TestExtractFromBase64PdfLocal:
    B64 = base64.b64encode(b"%PDF fake").decode()

    def test_bad_schema(self):
        assert extract_from_base64_pdf_local(self.B64, "bad")["status"] == "error"

    def test_list_schema(self):
        assert extract_from_base64_pdf_local(self.B64, "[1]")["status"] == "error"

    @patch(f"{M}._call_qwen_extraction", return_value=EXT)
    @patch(f"{M}._parse_base64_pdf_with_docling", return_value=PARSED)
    def test_ok(self, _p, _q):
        r = extract_from_base64_pdf_local(self.B64, SCHEMA_JSON)
        assert r["status"] == "success" and r["data"] == EXT

    @patch(f"{M}._parse_base64_pdf_with_docling")
    def test_empty_md(self, mp):
        mp.return_value = {**PARSED, "markdown": ""}
        assert extract_from_base64_pdf_local(self.B64, SCHEMA_JSON)["status"] == "error"

    @patch(f"{M}._call_qwen_extraction")
    @patch(f"{M}._parse_base64_pdf_with_docling", return_value=PARSED)
    def test_conn_err(self, _p, mq):
        import httpx as h
        mq.side_effect = h.ConnectError("x")
        assert extract_from_base64_pdf_local(self.B64, SCHEMA_JSON)["status"] == "error"

    @patch(f"{M}._call_qwen_extraction", return_value=EXT)
    @patch(f"{M}._parse_base64_pdf_with_docling")
    def test_truncation(self, mp, mq):
        mp.return_value = {**PARSED, "markdown": "y" * 20000}
        r = extract_from_base64_pdf_local(self.B64, SCHEMA_JSON)
        assert r["status"] == "success"
        assert len(mq.call_args[0][0]) < 20000


# == E2E tests (require Ollama running) =======================================

@pytest.mark.e2e
class TestE2EExtractDocumentDataLocal:
    """Requires Ollama with the configured model running."""

    def test_text_extraction(self):
        schema = json.dumps({"name": "person name", "role": "job title"})
        doc = "Jane Smith is a Senior Data Scientist at Acme Corp."
        r = extract_document_data_local(doc, schema)
        assert r["status"] == "success"
        assert "name" in r["data"]


@pytest.mark.e2e
class TestE2EParseAndExtractPdf:
    """Requires Docling + Ollama. Uses sample PDF if available."""

    def test_pdf_pipeline(self):
        pdf = os.path.join(os.path.dirname(__file__), "..", "..", "python", "samples", "SriniResume.pdf")
        pdf = os.path.abspath(pdf)
        if not os.path.isfile(pdf):
            pytest.skip("Sample PDF not found")
        schema = json.dumps({"name": "candidate name", "email": "email"})
        r = extract_from_pdf_local(pdf, schema)
        assert r["status"] == "success"
        assert "name" in r["data"]