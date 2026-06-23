"""Tests for the integrated security pipeline."""
 
import pytest
from src.security.pipeline import (
    SecureEnterpriseRAGPipeline,
    SecureQueryResult
)
 
 
class MockBasePipeline:
    """Mock base pipeline for testing security wrapper."""
    def __call__(self, question: str, metadata_filter=None):
        return type("Result", (), {
            "answer": f"Answer to: {question}",
            "sources": [],
            "context_chunks": []
        })()
 
 
def test_secure_pipeline_initializes():
    """SecureEnterpriseRAGPipeline should initialize without external deps."""
    pipeline = SecureEnterpriseRAGPipeline(
        base_pipeline=MockBasePipeline(),
        system_prompt="You are a helpful assistant.",
        verbose=False
    )
    assert pipeline is not None
 
 
def test_system_prompt_hardened():
    """System prompt should have security suffix appended."""
    original = "You are a helpful assistant."
    pipeline = SecureEnterpriseRAGPipeline(
        base_pipeline=MockBasePipeline(),
        system_prompt=original,
        verbose=False
    )
    assert len(pipeline.system_prompt) > len(original)
    assert "SECURITY" in pipeline.system_prompt or "security" in pipeline.system_prompt.lower()
 
 
def test_query_returns_secure_result():
    """Secure pipeline should always return SecureQueryResult."""
    pipeline = SecureEnterpriseRAGPipeline(
        base_pipeline=MockBasePipeline(),
        system_prompt="You are helpful.",
        enable_guardrails=False,
        verbose=False
    )
    result = pipeline.query("What is the return policy?")
    assert isinstance(result, SecureQueryResult)
    assert result.answer is not None
 
 
def test_clean_query_not_blocked():
    """Normal in-scope queries should not be blocked."""
    pipeline = SecureEnterpriseRAGPipeline(
        base_pipeline=MockBasePipeline(),
        system_prompt="You are helpful.",
        enable_guardrails=False,
        verbose=False
    )
    result = pipeline.query("What is the return policy?")
    assert result.blocked is False
 
 
def test_security_metadata_populated():
    """SecureQueryResult should include security metadata."""
    pipeline = SecureEnterpriseRAGPipeline(
        base_pipeline=MockBasePipeline(),
        system_prompt="You are helpful.",
        enable_guardrails=False,
        verbose=False
    )
    result = pipeline.query("What is the return policy?")
    assert result.security_metadata is not None
    assert isinstance(result.security_metadata, dict)
 
 
def test_rbac_levels_hierarchy():
    """RBAC access level hierarchy should be enforced."""
    pipeline = SecureEnterpriseRAGPipeline(
        base_pipeline=MockBasePipeline(),
        system_prompt="test",
        user_access_level="public",
        verbose=False
    )
    allowed = pipeline._get_allowed_levels()
    assert allowed == ["public"]
    assert "internal" not in allowed
    assert "restricted" not in allowed
 
 
def test_internal_user_access():
    """Internal user should access public and internal documents."""
    pipeline = SecureEnterpriseRAGPipeline(
        base_pipeline=MockBasePipeline(),
        system_prompt="test",
        user_access_level="internal",
        verbose=False
    )
    allowed = pipeline._get_allowed_levels()
    assert "public" in allowed
    assert "internal" in allowed
    assert "restricted" not in allowed