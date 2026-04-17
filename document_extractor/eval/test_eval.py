import pytest
from google.adk.evaluation import AgentEvaluator
from document_extractor.agent import root_agent

def test_agent_evaluation():
    """Evaluate agent performance on test dataset."""
    evaluator = AgentEvaluator(
        agent=root_agent,
        test_data_path="eval/eval_dataset.json",
    )

    results = evaluator.run()

    # Assert minimum performance thresholds
    assert results["tool_trajectory_avg_score"] >= 0.7
    assert results["response_match_score"] >= 0.75

    print(f"Evaluation Results: {results}")
