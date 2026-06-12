# Multi-source document ingestion
#
# Uses sentence-window chunking (window=2): selected based on
# benchmark results from rag-pipeline repo:
#   Context recall: 0.779 vs 0.620 for recursive chunking (+25.6%)
#   Overall eval score: 0.816 vs 0.714 baseline (+14.2%)
 
from src.ingestion.pipeline import (
    EnterpriseIngestionPipeline,
    CollectionConfig,
    IngestionResult,
    DEFAULT_COLLECTIONS
)
 
__all__ = [
    "EnterpriseIngestionPipeline",
    "CollectionConfig",
    "IngestionResult",
    "DEFAULT_COLLECTIONS"
]