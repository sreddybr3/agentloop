"""Configuration module for the doc_search_with_reranking_validation multi-agent system."""

import os
from dotenv import load_dotenv

load_dotenv()

# Google AI
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-004")

# Weaviate
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY", "")

# Collection name in Weaviate
WEAVIATE_COLLECTION = "Documents"

# Matching parameters
TOP_K_FIRST_PASS = 10  # Number of candidates from semantic search
TOP_K_FINAL = 3       # Final number of results after reranking