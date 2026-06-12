"""Tests for the multi-source ingestion pipeline."""
 
import pytest
from src.ingestion.pipeline import (
    EnterpriseIngestionPipeline,
    CollectionConfig,
    IngestionResult,
    DEFAULT_COLLECTIONS
)
 
 
def test_collection_config_defaults():
    """CollectionConfig should have sensible defaults."""
    config = CollectionConfig(
        name="test_collection",
        source_dir="data/test/",
        access_level="internal"
    )
    assert config.name == "test_collection"
    assert config.access_level == "internal"
    assert config.chunk_window_size == 2  # benchmark-winning default
 
 
def test_collection_config_access_levels():
    """Access levels should be one of the four valid tiers."""
    valid_levels = ["public", "internal", "confidential", "restricted"]
    for level in valid_levels:
        config = CollectionConfig(
            name="test",
            source_dir="data/",
            access_level=level
        )
        assert config.access_level == level
 
 
def test_default_collections_exist():
    """DEFAULT_COLLECTIONS should contain the four enterprise collections."""
    names = [c.name for c in DEFAULT_COLLECTIONS]
    assert "hr_policies" in names
    assert "product_docs" in names
    assert "public_faq" in names
    assert "legal" in names
 
 
def test_default_collections_access_levels():
    """Each default collection should have the correct access level."""
    collection_map = {c.name: c for c in DEFAULT_COLLECTIONS}
    assert collection_map["hr_policies"].access_level == "internal"
    assert collection_map["legal"].access_level == "restricted"
    assert collection_map["public_faq"].access_level == "public"
    assert collection_map["product_docs"].access_level == "internal"
 
 
def test_ingestion_pipeline_initializes():
    """Pipeline should initialize without errors."""
    pipeline = EnterpriseIngestionPipeline(verbose=False)
    assert pipeline is not None
    assert pipeline.chunk_window == 2
 
 
def test_ingestion_missing_directory_returns_error():
    """Ingesting a non-existent directory should return an error result."""
    pipeline = EnterpriseIngestionPipeline(verbose=False)
    config = CollectionConfig(
        name="missing",
        source_dir="data/does_not_exist/",
        access_level="internal"
    )
    result = pipeline.ingest_collection(config)
    assert isinstance(result, IngestionResult)
    assert not result.success
    assert len(result.errors) > 0
 
 
def test_ingestion_result_success_property():
    """IngestionResult.success should reflect documents_processed and errors."""
    result_with_docs = IngestionResult(
        collection_name="test",
        documents_processed=5,
        chunks_created=25,
        access_level="internal"
    )
    assert result_with_docs.success is True
 
    result_no_docs = IngestionResult(
        collection_name="test",
        documents_processed=0,
        chunks_created=0,
        access_level="internal"
    )
    assert result_no_docs.success is False
 
    result_with_errors = IngestionResult(
        collection_name="test",
        documents_processed=5,
        chunks_created=25,
        access_level="internal",
        errors=["Something went wrong"]
    )
    assert result_with_errors.success is False
 
 
def test_chunk_window_applied():
    """Chunking should use the configured window size."""
    pipeline = EnterpriseIngestionPipeline(chunk_window=3, verbose=False)
    assert pipeline.chunk_window == 3