"""Tests for the evaluation integration."""
 
import pytest
import json
import os
import tempfile
from src.evaluation.pipeline_eval import (
    EnterpriseRAGEvaluator,
    EvalConfig
)
 
 
def test_eval_config_defaults():
    """EvalConfig should have sensible defaults."""
    config = EvalConfig(
        dataset_path="data/eval_dataset.json",
        pipeline_version="v1.0"
    )
    assert config.model_name == "gpt-4"
    assert config.output_dir == "./results"
    assert config.run_by_category is True
 
 
def test_eval_config_target_scores():
    """EnterpriseRAGEvaluator should have target scores defined."""
    config = EvalConfig(
        dataset_path="data/eval_dataset.json",
        pipeline_version="v1.0"
    )
    evaluator = EnterpriseRAGEvaluator(
        pipeline=lambda q: q,
        config=config,
        verbose=False
    )
    assert "faithfulness" in evaluator.TARGET_SCORES
    assert "answer_relevancy" in evaluator.TARGET_SCORES
    assert "context_precision" in evaluator.TARGET_SCORES
    assert "context_recall" in evaluator.TARGET_SCORES
    assert "overall" in evaluator.TARGET_SCORES
 
 
def test_target_scores_are_reasonable():
    """Target scores should be between 0 and 1 and above the 0.7 baseline."""
    config = EvalConfig(
        dataset_path="data/eval_dataset.json",
        pipeline_version="v1.0"
    )
    evaluator = EnterpriseRAGEvaluator(
        pipeline=lambda q: q,
        config=config,
        verbose=False
    )
    for metric, score in evaluator.TARGET_SCORES.items():
        assert 0.0 < score <= 1.0, f"Target score for {metric} out of range: {score}"
        assert score >= 0.70, f"Target score for {metric} should exceed baseline: {score}"
 
 
def test_compare_versions_detects_improvement():
    """compare_versions should identify improvements correctly."""
    config = EvalConfig(
        dataset_path="data/eval_dataset.json",
        pipeline_version="v1.0"
    )
    evaluator = EnterpriseRAGEvaluator(
        pipeline=lambda q: q,
        config=config,
        verbose=False
    )
 
    # Write temporary result files
    with tempfile.TemporaryDirectory() as tmpdir:
        baseline_path = os.path.join(tmpdir, "baseline.json")
        current_path = os.path.join(tmpdir, "current.json")
 
        baseline_data = {
            "summary": {
                "metric_averages": {
                    "faithfulness": 0.78,
                    "context_recall": 0.62
                }
            }
        }
        current_data = {
            "summary": {
                "metric_averages": {
                    "faithfulness": 0.85,
                    "context_recall": 0.78
                }
            }
        }
 
        with open(baseline_path, "w") as f:
            json.dump(baseline_data, f)
        with open(current_path, "w") as f:
            json.dump(current_data, f)
 
        comparison = evaluator.compare_versions(baseline_path, current_path)
 
        assert "faithfulness" in comparison["improvements"]
        assert "context_recall" in comparison["improvements"]
        assert len(comparison["regressions"]) == 0
 
 
def test_compare_versions_detects_regression():
    """compare_versions should identify regressions correctly."""
    config = EvalConfig(
        dataset_path="data/eval_dataset.json",
        pipeline_version="v1.0"
    )
    evaluator = EnterpriseRAGEvaluator(
        pipeline=lambda q: q,
        config=config,
        verbose=False
    )
 
    with tempfile.TemporaryDirectory() as tmpdir:
        baseline_path = os.path.join(tmpdir, "baseline.json")
        current_path = os.path.join(tmpdir, "current.json")
 
        baseline_data = {
            "summary": {"metric_averages": {"faithfulness": 0.85}}
        }
        current_data = {
            "summary": {"metric_averages": {"faithfulness": 0.72}}
        }
 
        with open(baseline_path, "w") as f:
            json.dump(baseline_data, f)
        with open(current_path, "w") as f:
            json.dump(current_data, f)
 
        comparison = evaluator.compare_versions(baseline_path, current_path)
        assert "faithfulness" in comparison["regressions"]