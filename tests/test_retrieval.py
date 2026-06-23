"""Tests for the enterprise retrieval pipeline."""
 
import pytest
from src.retrieval.pipeline import (
    EnterpriseRetriever,
    RetrievalConfig,
    RetrievalResult
)
 
 
def test_retrieval_config_defaults():
    """RetrievalConfig defaults should match benchmark-winning config."""
    config = RetrievalConfig()
    assert config.use_hyde is True
    assert config.use_reranking is True
    assert config.retrieval_k == 20
    assert config.reranking_top_k == 5
    assert config.user_access_level == "internal"
 
 
def test_retrieval_config_access_level():
    """User access level should be configurable."""
    config = RetrievalConfig(user_access_level="restricted")
    assert config.user_access_level == "restricted"
 
 
def test_retriever_initializes_without_dependencies():
    """Retriever should initialize gracefully without rag-pipeline installed."""
    retriever = EnterpriseRetriever(
        vector_stores={},
        embedder=None,
        llm_client=None,
        verbose=False
    )
    assert retriever is not None
 
 
def test_retriever_returns_result_object():
    """Retriever.retrieve() should always return a RetrievalResult."""
    retriever = EnterpriseRetriever(
        vector_stores={},
        verbose=False
    )
    result = retriever.retrieve("What is the return policy?")
    assert isinstance(result, RetrievalResult)
    assert result.query == "What is the return policy?"
 
 
def test_retrieval_result_has_required_fields():
    """RetrievalResult should always have chunks and query."""
    result = RetrievalResult(
        chunks=[{"content": "test", "source": "doc.pdf"}],
        query="test query"
    )
    assert result.chunks is not None
    assert result.query == "test query"
    assert isinstance(result.collections_searched, list)
 
 
def test_retriever_mock_fallback():
    """Retriever should return mock results when no vector stores configured."""
    retriever = EnterpriseRetriever(
        vector_stores={},
        verbose=False
    )
    result = retriever.retrieve("test query")
    assert isinstance(result, RetrievalResult)
    # No crash — graceful mock fallback
 
 
def test_rbac_access_levels():
    """get_allowed_levels should return correct hierarchy."""
    retriever = EnterpriseRetriever(
        vector_stores={},
        config=RetrievalConfig(user_access_level="internal"),
        verbose=False
    )
    allowed = retriever._get_allowed_levels()
    assert "public" in allowed
    assert "internal" in allowed
    assert "restricted" not in allowed
    assert "confidential" not in allowed
 
 
def test_rbac_restricted_user_gets_all_levels():
    """Restricted user should have access to all document levels."""
    retriever = EnterpriseRetriever(
        vector_stores={},
        config=RetrievalConfig(user_access_level="restricted"),
        verbose=False
    )
    allowed = retriever._get_allowed_levels()
    assert "public" in allowed
    assert "internal" in allowed
    assert "confidential" in allowed
    assert "restricted" in allowed
 
 
def test_rbac_public_user_gets_only_public():
    """Public user should only access public documents."""
    retriever = EnterpriseRetriever(
        vector_stores={},
        config=RetrievalConfig(user_access_level="public"),
        verbose=False
    )
    allowed = retriever._get_allowed_levels()
    assert allowed == ["public"]