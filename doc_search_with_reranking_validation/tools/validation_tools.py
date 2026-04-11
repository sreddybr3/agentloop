"""Tools for the Validation Agent (LLM Judge).

Provides validation capabilities to assess the quality and relevance
of matching results produced by the Matching Agent.
"""

import json
import logging
from typing import Any

from google import genai

from doc_search_with_reranking_validation.config import GOOGLE_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)


def validate_matching_results(
    user_input: str, matching_results_json: str
) -> dict[str, Any]:
    """Validate the matching results using LLM as a judge.

    Evaluates the quality of the document matching by assessing:
    - Relevance of matched documents to the user input
    - Appropriateness of ranking order
    - Whether any important aspects of the query are missed
    - Overall confidence in the matching quality

    Args:
        user_input: The original user input paragraph.
        matching_results_json: JSON string of the matching results to validate.

    Returns:
        A dictionary containing validation assessment.
    """
    try:
        matching_results = json.loads(matching_results_json)
    except (json.JSONDecodeError, TypeError):
        if isinstance(matching_results_json, (dict, list)):
            matching_results = matching_results_json
        else:
            return {
                "validation_status": "error",
                "message": "Could not parse matching results",
            }

    ranked = matching_results if isinstance(matching_results, list) else matching_results.get("ranked_results", [])

    if not ranked:
        return {
            "validation_status": "no_results",
            "message": "No matching results to validate",
            "overall_score": 0.0,
        }

    # Build the validation prompt
    results_text = ""
    for item in ranked:
        results_text += (
            f"\nRank #{item.get('rank', '?')}: {item.get('title', 'N/A')}\n"
            f"  Document ID: {item.get('doc_id', 'N/A')}\n"
            f"  Relevance Score: {item.get('relevance_score', 0):.4f}\n"
            f"  Explanation: {item.get('explanation', 'N/A')}\n"
            f"  Source: {item.get('source', 'N/A')}\n"
        )

    validation_prompt = f"""You are an expert validation judge for a document matching system. Your task is to evaluate the quality of document matching results.

USER INPUT PARAGRAPH:
{user_input}

MATCHING RESULTS (Top {len(ranked)} documents):
{results_text}

EVALUATION CRITERIA:
1. **Relevance Assessment**: Are the top-ranked documents truly relevant to the user's input? Rate each document's relevance.
2. **Ranking Quality**: Is the ranking order appropriate? Are the most relevant documents ranked highest?
3. **Coverage**: Does the result set cover the key topics and themes in the user's input?
4. **Diversity**: Do the results offer diverse perspectives or sources on the topic?
5. **Explanation Quality**: Are the matching explanations accurate and informative?

Provide your assessment as a JSON object with this exact structure:
{{
    "validation_status": "pass" or "partial_pass" or "fail",
    "overall_score": 0.0 to 1.0,
    "summary": "Brief summary of the validation assessment",
    "relevance_assessment": {{
        "score": 0.0 to 1.0,
        "comment": "Assessment of document relevance"
    }},
    "ranking_quality": {{
        "score": 0.0 to 1.0,
        "comment": "Assessment of ranking correctness"
    }},
    "coverage": {{
        "score": 0.0 to 1.0,
        "comment": "Assessment of topic coverage",
        "missing_aspects": ["list of aspects not covered"]
    }},
    "diversity": {{
        "score": 0.0 to 1.0,
        "comment": "Assessment of result diversity"
    }},
    "per_document_assessment": [
        {{
            "rank": 1,
            "doc_id": "id",
            "is_relevant": true or false,
            "comment": "Brief assessment"
        }}
    ],
    "recommendations": ["List of recommendations for improvement"]
}}

Return ONLY the JSON object, no other text."""

    client = genai.Client(api_key=GOOGLE_API_KEY)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=validation_prompt,
    )

    response_text = response.text.strip()

    # Remove markdown code fences if present
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        response_text = "\n".join(lines)

    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        logger.error("Failed to parse validation response: %s", response_text[:500])
        result = {
            "validation_status": "error",
            "overall_score": 0.0,
            "summary": "Validation LLM response could not be parsed",
            "raw_response": response_text[:1000],
        }

    return result


def format_validation_report(validation_json: str) -> str:
    """Format the validation results into a readable report.

    Args:
        validation_json: JSON string of the validation results.

    Returns:
        Formatted validation report string.
    """
    try:
        data = json.loads(validation_json)
    except (json.JSONDecodeError, TypeError):
        if isinstance(validation_json, dict):
            data = validation_json
        else:
            return "Error: Could not parse validation results"

    status = data.get("validation_status", "unknown")
    overall = data.get("overall_score", 0)
    summary = data.get("summary", "No summary available")

    status_emoji = {"pass": "✅", "partial_pass": "⚠️", "fail": "❌"}.get(status, "❓")

    lines = [
        "# Validation Report\n",
        f"**Status:** {status_emoji} {status.upper()}",
        f"**Overall Score:** {overall:.2f}/1.00",
        f"**Summary:** {summary}\n",
    ]

    # Dimension scores
    for dimension in ["relevance_assessment", "ranking_quality", "coverage", "diversity"]:
        dim_data = data.get(dimension, {})
        if dim_data:
            dim_name = dimension.replace("_", " ").title()
            score = dim_data.get("score", "N/A")
            comment = dim_data.get("comment", "")
            lines.append(f"### {dim_name}")
            lines.append(f"- **Score:** {score}")
            lines.append(f"- **Comment:** {comment}")

            if dimension == "coverage":
                missing = dim_data.get("missing_aspects", [])
                if missing:
                    lines.append(f"- **Missing Aspects:** {', '.join(missing)}")
            lines.append("")

    # Per-document assessments
    per_doc = data.get("per_document_assessment", [])
    if per_doc:
        lines.append("### Per-Document Assessment")
        for doc_eval in per_doc:
            rank = doc_eval.get("rank", "?")
            relevant = "✅" if doc_eval.get("is_relevant") else "❌"
            comment = doc_eval.get("comment", "")
            lines.append(f"- **Rank #{rank}:** {relevant} {comment}")
        lines.append("")

    # Recommendations
    recommendations = data.get("recommendations", [])
    if recommendations:
        lines.append("### Recommendations")
        for rec in recommendations:
            lines.append(f"- {rec}")

    return "\n".join(lines)