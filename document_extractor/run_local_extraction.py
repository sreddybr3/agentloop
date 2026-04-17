"""Demo script that extracts structured data using the LOCAL Ollama model (Gemma4).

This script bypasses the ADK agent entirely and calls the local extractor tool
directly — useful for testing Ollama connectivity and extraction quality without
needing Google Cloud credentials.

Usage:
    python run_local_extraction.py
"""

import os
import json
import logging


def _load_env():
    """Load environment variables from .env file if present."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())


def _configure_logging():
    """Set up detailed debug logging."""
    log_level = os.environ.get("LOG_LEVEL", "DEBUG").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.DEBUG),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


_load_env()
_configure_logging()

logger = logging.getLogger(__name__)

from document_extractor.tools.local_extractor import extract_document_data_local  # noqa: E402
from document_extractor.schemas import resume_schema_to_extraction_format  # noqa: E402


# ── Invoice extraction demo ─────────────────────────────────────────────────

def demo_invoice():
    """Extract data from a simple invoice."""
    document = (
        "Invoice INV-001\n"
        "Date: 2026-04-17\n"
        "Total Amount: $1,250.00\n"
        "Vendor: Acme Corp\n"
    )
    schema = json.dumps({
        "invoice_number": "The invoice number",
        "date": "The date of the invoice",
        "total_amount": "The total amount of the invoice, without the currency symbol",
        "vendor_name": "The name of the vendor",
    })

    print("=" * 60)
    print("INVOICE EXTRACTION (Ollama local)")
    print("=" * 60)
    result = extract_document_data_local(document, schema)
    print(json.dumps(result, indent=2))
    print()


# ── Resume extraction demo ──────────────────────────────────────────────────

SAMPLE_RESUME = """\
JOHN DOE
Email: john.doe@email.com | Phone: +1-555-123-4567 | Location: San Francisco, CA

PROFESSIONAL SUMMARY
Results-driven software engineer with 8 years of experience in full-stack
development specializing in cloud-native applications and distributed systems.

SKILLS
Python, Java, TypeScript, React, Node.js, AWS, Kubernetes, Docker, PostgreSQL,
MongoDB, CI/CD, Agile, Team Leadership

WORK EXPERIENCE

Senior Software Engineer | Acme Technologies | Jan 2021 - Present
- Led a team of 5 engineers to deliver a microservices platform serving 2M+ users
- Reduced API response times by 40% through caching and query optimization
- Designed event-driven architecture using Kafka and AWS Lambda

Software Engineer | Beta Corp | Jun 2017 - Dec 2020
- Developed RESTful APIs in Python/Flask and Java/Spring Boot
- Built CI/CD pipelines using Jenkins and GitHub Actions
- Mentored 3 junior developers

EDUCATION
M.S. Computer Science | Stanford University | 2017
B.S. Computer Science | UC Berkeley | 2015

CERTIFICATIONS
AWS Certified Solutions Architect - Associate | Amazon Web Services | 2022
Certified Kubernetes Administrator (CKA) | CNCF | 2023

LANGUAGES
English, Spanish, Mandarin
"""


def demo_resume():
    """Extract structured resume data using the default resume schema."""
    schema = json.dumps(resume_schema_to_extraction_format())

    print("=" * 60)
    print("RESUME EXTRACTION (Ollama local)")
    print("=" * 60)
    result = extract_document_data_local(SAMPLE_RESUME, schema)
    print(json.dumps(result, indent=2))
    print()


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info(
        "Using Ollama at %s with model %s",
        os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        os.environ.get("OLLAMA_MODEL", "gemma4:latest"),
    )
    demo_invoice()
    demo_resume()