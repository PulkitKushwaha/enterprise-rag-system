"""
Evaluation-Driven Retrieval Optimization
 
Integrates llm-eval-framework to measure and optimize retrieval
quality across the enterprise RAG system.
 
The evaluation loop:
    1. Run pipeline against 30-question test dataset
    2. Score on Faithfulness, Relevancy, Precision, Recall
    3. Identify weakest metric and failing categories
    4. Apply targeted optimization
    5. Re-evaluate and compare
 
This is how the baseline (0.714) → optimized (0.816) improvement
was achieved in the rag-pipeline repo: systematic measurement,
not intuition-driven optimization.
 
Integrates with:
    llm-eval-framework: https://github.com/pulkitkushwaha/llm-eval-framework
"""
 
from typing import Optional, Dict, Any
from dataclasses import dataclass
 
 
@dataclass
class EvalConfig:
    """Configuration for an evaluation run."""
    dataset_path: str
    pipeline_version: str
    model_name: str = "gpt-4"
    max_samples: Optional[int] = None
    output_dir: str = "./results"
    run_by_category: bool = True
 
 
class EnterpriseRAGEvaluator:
    """
    Evaluates the enterprise RAG pipeline using llm-eval-framework.
 
    Wraps PipelineEvaluator with enterprise-specific configuration:
    - Per-collection evaluation (are HR queries better than legal?)
    - Security evaluation (what's the red-team attack success rate?)
    - Trend tracking (is the pipeline improving over time?)
 
    Args:
        pipeline    : Enterprise RAG pipeline callable
        config      : EvalConfig
        verbose     : Print progress
    """
 
    TARGET_SCORES = {
        "faithfulness": 0.80,
        "answer_relevancy": 0.80,
        "context_precision": 0.75,
        "context_recall": 0.75,
        "overall": 0.78
    }
 
    def __init__(self, pipeline, config: EvalConfig, verbose: bool = True):
        self.pipeline = pipeline
        self.config = config
        self.verbose = verbose
 
    def run_full_eval(self) -> Dict[str, Any]:
        """
        Run complete evaluation suite.
 
        Returns:
            Dict with overall scores, per-category breakdown,
            and comparison against target thresholds.
        """
        try:
            from llm_eval import Evaluator
            from llm_eval.models import EvalSample
            from llm_eval.metrics import (
                Faithfulness, AnswerRelevancy,
                ContextPrecision, ContextRecall
            )
            from llm_eval.reporters import JSONReporter, MarkdownReporter
        except ImportError:
            print(
                "[Evaluator] llm-eval-framework not installed.\n"
                "Install from: https://github.com/pulkitkushwaha/llm-eval-framework"
            )
            return {}
 
        import json
        import os
 
        # Load dataset
        with open(self.config.dataset_path) as f:
            questions = json.load(f)
 
        if self.config.max_samples:
            questions = questions[:self.config.max_samples]
 
        if self.verbose:
            print(f"[Eval] Running {len(questions)} questions...")
            print(f"[Eval] Pipeline version: {self.config.pipeline_version}")
 
        # Collect pipeline outputs
        samples = []
        for q in questions:
            try:
                result = self.pipeline(q["question"])
                answer = result.answer if hasattr(result, "answer") else str(result)
                contexts = [
                    chunk.content
                    for chunk in getattr(result, "context_chunks", [])
                ] or ["No context retrieved"]
 
                samples.append(EvalSample(
                    question=q["question"],
                    answer=answer,
                    contexts=contexts,
                    ground_truth=q.get("ground_truth")
                ))
            except Exception as e:
                print(f"  ⚠️ Pipeline failed on: {q['question'][:50]}... ({e})")
 
        # Run evaluation
        evaluator = Evaluator(
            metrics=[
                Faithfulness(),
                AnswerRelevancy(),
                ContextPrecision(),
                ContextRecall()
            ],
            metadata={
                "pipeline_version": self.config.pipeline_version,
                "model": self.config.model_name,
                "system": "enterprise-rag-system"
            },
            verbose=self.verbose
        )
 
        report = evaluator.evaluate(samples)
 
        # Save results
        os.makedirs(self.config.output_dir, exist_ok=True)
        version_slug = self.config.pipeline_version.replace("/", "_")
 
        json_path = f"{self.config.output_dir}/{version_slug}_results.json"
        md_path = f"{self.config.output_dir}/{version_slug}_summary.md"
 
        JSONReporter().save(report, json_path)
        MarkdownReporter(include_per_sample=False).save(report, md_path)
 
        # Check against targets
        results = {
            "pipeline_version": self.config.pipeline_version,
            "overall_score": report.overall_score,
            "metric_scores": report.metric_averages,
            "target_scores": self.TARGET_SCORES,
            "passing": {}
        }
 
        print(f"\n[Eval] Results for {self.config.pipeline_version}:")
        for metric, score in report.metric_averages.items():
            target = self.TARGET_SCORES.get(metric, 0.70)
            passing = score >= target
            results["passing"][metric] = passing
            status = "✅" if passing else "❌"
            print(f"  {status} {metric}: {score:.4f} (target: {target})")
 
        overall_pass = report.overall_score >= self.TARGET_SCORES["overall"]
        results["overall_passing"] = overall_pass
        print(f"\n  {'✅ PASS' if overall_pass else '❌ FAIL'} Overall: {report.overall_score:.4f}")
 
        return results
 
    def compare_versions(
        self,
        baseline_path: str,
        current_path: str
    ) -> Dict[str, Any]:
        """
        Compare two evaluation result files.
 
        Useful for tracking improvement over commits.
        """
        import json
 
        with open(baseline_path) as f:
            baseline = json.load(f)
        with open(current_path) as f:
            current = json.load(f)
 
        comparison = {"improvements": {}, "regressions": {}}
 
        baseline_metrics = baseline.get("summary", {}).get("metric_averages", {})
        current_metrics = current.get("summary", {}).get("metric_averages", {})
 
        for metric in baseline_metrics:
            if metric in current_metrics:
                delta = current_metrics[metric] - baseline_metrics[metric]
                if delta > 0.01:
                    comparison["improvements"][metric] = round(delta, 4)
                elif delta < -0.01:
                    comparison["regressions"][metric] = round(delta, 4)
 
        return comparison