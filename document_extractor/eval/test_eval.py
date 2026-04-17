import os
import sys

import pytest

# Ensure the document_extractor package directory is on sys.path
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Load .env before importing agent so env vars (MODEL_NAME etc.) are available
_env_path = os.path.join(_project_root, ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())

from google.adk.evaluation import AgentEvaluator  # noqa: E402


def test_agent_evaluation():
    """Evaluate agent tool-use trajectory against the eval dataset."""
    eval_dataset_path = os.path.join(os.path.dirname(__file__), "eval_dataset.json")

    # AgentEvaluator.evaluate is a classmethod/staticmethod that accepts:
    #   agent_module:  string path to the agent module (e.g. "document_extractor")
    #   eval_dataset_file_path_or_dir:  path to the JSON eval dataset
    #   num_runs:  how many times to run each eval case (default 1)
    metrics = AgentEvaluator.evaluate(
        agent_module="document_extractor",
        eval_dataset_file_path_or_dir=eval_dataset_path,
        num_runs=1,
    )

    print(f"Evaluation metrics: {metrics}")

    # Assert minimum performance thresholds
    assert metrics["tool_trajectory_avg_score"] >= 0.7, (
        f"Tool trajectory score {metrics['tool_trajectory_avg_score']} below 0.7 threshold"
    )
    assert metrics["response_match_score"] >= 0.75, (
        f"Response match score {metrics['response_match_score']} below 0.75 threshold"
    )