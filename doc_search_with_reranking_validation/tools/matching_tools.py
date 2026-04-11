"""Tools for the Matching Agent.

Provides semantic search (first pass) and LLM-based reranking (second pass)
capabilities for document matching.
"""

import json
import logging
from typing import Any

from google import genai

from doc_search_with_reranking_validation.config import (
    GOOGLE_API_KEY,
    GEMINI_MODEL,
    TOP_K_FIRST_PASS,
    TOP_K_FINAL,
)
from doc_search_with_reranking_validation.vector_store import semantic_search, get_document_count

logger = logging.getLogger(__name__)


def search_documents(query: str, top_k: int = TOP_K_FIRST_PASS) -> dict[str, Any]:
    """First pass: Perform semantic search to find candidate documents.

    Uses vector embeddings to find the most semantically similar documents
    to the user's input paragraph.

    Args:
        query: The user input paragraph to match against documents.
        top_k: Number of candidate documents to retrieve (default: 30).

    Returns:
        A dictionary containing:
            - candidates: List of candidate documents with similarity scores.
            - total_documents: Total documents in the store.
            - query_preview: First 200 chars of the query.
    """
    total_docs = get_document_count()
    logger.info("Searching %d documents for matches", total_docs)

    candidates = semantic_search(query, top_k=top_k)

    return {
        "candidates": candidates,
        "total_documents": total_docs,
        "num_candidates": len(candidates),
        "query_preview": query[:200] + "..." if len(query) > 200 else query,
    }


def rerank_documents(
    query: str, candidates_json: str, top_k: int = TOP_K_FINAL
) -> dict[str, Any]:
    """Second pass: Rerank candidate documents using Gemini LLM.

    Takes the candidates from the first pass and uses the LLM to perform
    a more nuanced relevance assessment, producing final rankings with
    explanations.

    Args:
        query: The original user input paragraph.
        candidates_json: JSON string of candidate documents from first pass.
        top_k: Number of final results to return (default: 10).

    Returns:
        A dictionary containing the top ranked documents with scores and explanations.
    """
    try:
        candidates = json.loads(candidates_json)
    except (json.JSONDecodeError, TypeError):
        if isinstance(candidates_json, list):
            candidates = candidates_json
        else:
            return {"error": "Invalid candidates JSON", "ranked_results": []}

    if not candidates:
        return {"ranked_results": [], "message": "No candidates to rerank"}

    # Build the reranking prompt
    docs_text = ""
    for i, doc in enumerate(candidates):
        docs_text += (
            f"\n--- Document {i + 1} ---\n"
            f"ID: {doc.get('doc_id', 'N/A')}\n"
            f"Title: {doc.get('title', 'N/A')}\n"
            f"Content: {doc.get('content', 'N/A')[:500]}\n"
            f"Source: {doc.get('source', 'N/A')}\n"
            f"Semantic Similarity: {doc.get('similarity_score', 0):.4f}\n"
        )

    rerank_prompt = f"""You are a document relevance expert. Your task is to rerank the following candidate documents based on their relevance to the user's input paragraph.

USER INPUT PARAGRAPH:
{query}

CANDIDATE DOCUMENTS:
{docs_text}

INSTRUCTIONS:
1. Carefully analyze the semantic meaning and intent of the user's input paragraph.
2. Evaluate each candidate document for relevance considering:
   - Topical alignment and subject matter overlap
   - Contextual relevance and shared concepts
   - Specificity of the match (prefer precise matches over general ones)
   - Information completeness relative to the query
3. Assign a relevance score from 0.0 to 1.0 for each document.
4. Select the top {top_k} most relevant documents.
5. For each selected document, provide a brief explanation of why it matches.

Return your response as a JSON object with this exact structure:
{{
    "ranked_results": [
        {{
            "rank": 1,
            "doc_id": "document id",
            "title": "document title",
            "relevance_score": 0.95,
            "explanation": "Brief explanation of why this document matches the input",
            "source": "document source"
        }}
    ]
}}

Return ONLY the JSON object, no other text."""

    client = genai.Client(api_key=GOOGLE_API_KEY)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=rerank_prompt,
    )

    # Parse the LLM response
    response_text = response.text.strip()

    # Remove markdown code fences if present
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        # Remove first line (```json) and last line (```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        response_text = "\n".join(lines)

    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        logger.error("Failed to parse LLM reranking response: %s", response_text[:500])
        # Fallback: return candidates sorted by similarity
        sorted_candidates = sorted(
            candidates, key=lambda x: x.get("similarity_score", 0), reverse=True
        )[:top_k]
        result = {
            "ranked_results": [
                {
                    "rank": i + 1,
                    "doc_id": doc.get("doc_id", ""),
                    "title": doc.get("title", ""),
                    "relevance_score": doc.get("similarity_score", 0),
                    "explanation": "Ranked by semantic similarity (LLM reranking failed)",
                    "source": doc.get("source", ""),
                }
                for i, doc in enumerate(sorted_candidates)
            ],
            "fallback": True,
        }

    return result


def format_matching_results(reranked_json: str) -> str:
    """Format the reranked results into a readable output.

    Args:
        reranked_json: JSON string of reranked results.

    Returns:
        Formatted string with ranking, scores, and explanations.
    """
    try:
        data = json.loads(reranked_json)
    except (json.JSONDecodeError, TypeError):
        if isinstance(reranked_json, dict):
            data = reranked_json
        else:
            return "Error: Could not parse results"

    ranked = data.get("ranked_results", [])
    if not ranked:
        return "No matching documents found."

    output_lines = ["# Document Matching Results\n"]
    output_lines.append(f"**Top {len(ranked)} Matched Documents:**\n")

    for item in ranked:
        rank = item.get("rank", "?")
        doc_id = item.get("doc_id", "N/A")
        title = item.get("title", "N/A")
        score = item.get("relevance_score", 0)
        explanation = item.get("explanation", "No explanation provided")
        source = item.get("source", "N/A")

        output_lines.append(
            f"## Rank #{rank}: {title}\n"
            f"- **Document ID:** {doc_id}\n"
            f"- **Relevance Score:** {score:.4f}\n"
            f"- **Source:** {source}\n"
            f"- **Explanation:** {explanation}\n"
        )

    if data.get("fallback"):
        output_lines.append(
            "\n*Note: LLM reranking was unavailable; results are ranked by semantic similarity.*\n"
        )

    return "\n".join(output_lines)