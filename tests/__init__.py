# Test suite for enterprise-rag-system
#
# Test categories:
#   test_ingestion.py   — CollectionConfig, chunking, metadata
#   test_retrieval.py   — RBAC filter, multi-doc retrieval
#   test_security.py    — Injection detection, guardrails
#   test_evaluation.py  — PipelineEvaluator integration
#   test_api.py         — FastAPI endpoints, auth, rate limiting