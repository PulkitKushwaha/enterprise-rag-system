# Evaluation integration with llm-eval-framework
#
# Measures pipeline quality on every commit: CI/CD gate fails
# if overall score drops below 0.78.
#
# Target scores (based on optimized rag-pipeline benchmarks):
#   Faithfulness:       >= 0.80
#   Answer Relevancy:   >= 0.80
#   Context Precision:  >= 0.75
#   Context Recall:     >= 0.75
#   Overall:            >= 0.78
#
# Install llm-eval-framework:
#   pip install -e ../llm-eval-framework
 
from src.evaluation.pipeline_eval import (
    EnterpriseRAGEvaluator,
    EvalConfig
)
 
__all__ = [
    "EnterpriseRAGEvaluator",
    "EvalConfig"
]