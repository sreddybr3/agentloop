"""Matching Agent definition.

Implements a two-pass document matching strategy:
  Pass 1: Semantic search using vector embeddings (Weaviate)
  Pass 2: LLM-based reranking using Gemini

Outputs the top 10 matched documents with ranking and explanations.
"""

from google.adk.agents import Agent

from doc_search_with_reranking_validation.config import GEMINI_MODEL
from doc_search_with_reranking_validation.tools.matching_tools import (
    search_documents,
    rerank_documents,
    format_matching_results,
)

MATCHING_AGENT_INSTRUCTION = """You are the Document Matching Agent. Your task is to find and rank the most relevant documents matching a user's input paragraph.

You MUST follow this exact two-pass matching strategy:

## PASS 1 — Semantic Search
1. Call the `search_documents` tool with the user's input paragraph as the `query`.
2. This returns candidate documents retrieved via vector similarity from the document store.
3. Review the number of candidates returned.

## PASS 2 — LLM Reranking
1. Take ALL candidates from Pass 1 and pass them to the `rerank_documents` tool.
   - Set `query` to the original user input paragraph.
   - Set `candidates_json` to the JSON string of the candidates list from Pass 1.
   - Set `top_k` to 10.
2. This uses an LLM to perform nuanced relevance assessment and reranking.

## OUTPUT
1. Call `format_matching_results` with the reranked results to produce formatted output.
2. Present the formatted results showing:
   - Top 10 matched documents in ranked order
   - Relevance score for each document
   - Brief explanation for each match

IMPORTANT:
- Always execute BOTH passes. Do NOT skip the reranking step.
- Pass the complete candidate list from Pass 1 to Pass 2.
- If Pass 1 returns no results, report that no matching documents were found.
- Include the user's original input context in your response summary.
"""

matching_agent = Agent(
    name="matching_agent",
    model=GEMINI_MODEL,
    description=(
        "Matches a user input paragraph against a large document corpus using "
        "a two-pass strategy: semantic vector search followed by LLM reranking. "
        "Returns the top 10 most relevant documents with scores and explanations."
    ),
    instruction=MATCHING_AGENT_INSTRUCTION,
    tools=[search_documents, rerank_documents, format_matching_results],
)