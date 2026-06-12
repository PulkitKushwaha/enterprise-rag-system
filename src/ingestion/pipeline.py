"""
Enterprise Multi-Source Ingestion Pipeline
 
Ingests documents from multiple sources into per-collection
FAISS vector stores with metadata enrichment and access control.
 
The chunking strategy (SentenceWindowChunker, window=2) was
selected based on evaluation results from the rag-pipeline repo:
    - Context recall: 0.779 vs 0.620 for recursive chunking (+25.6%)
    - Overall score: 0.816 vs 0.714 for baseline (+14.2%)
 
This is the configuration that produced the best benchmark scores.
See: https://github.com/pulkitkushwaha/rag-pipeline/results/
 
Document collections supported:
    - HR policies (access_level: internal)
    - Legal contracts (access_level: restricted)
    - Product documentation (access_level: internal)
    - Public FAQ (access_level: public)
    - Custom collections (configurable)
"""
 
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path
import os
 
 
@dataclass
class CollectionConfig:
    """Configuration for a document collection."""
    name: str
    source_dir: str
    access_level: str  # public, internal, confidential, restricted
    department: Optional[str] = None
    description: str = ""
    chunk_window_size: int = 2
 
 
@dataclass
class IngestionResult:
    """Result of ingesting a collection."""
    collection_name: str
    documents_processed: int
    chunks_created: int
    access_level: str
    errors: List[str] = field(default_factory=list)
 
    @property
    def success(self) -> bool:
        return self.documents_processed > 0 and not self.errors
 
 
# Pre-defined enterprise collections
DEFAULT_COLLECTIONS = [
    CollectionConfig(
        name="hr_policies",
        source_dir="data/hr_policies/",
        access_level="internal",
        department="HR",
        description="HR policies, procedures, and employee handbook"
    ),
    CollectionConfig(
        name="product_docs",
        source_dir="data/product_docs/",
        access_level="internal",
        department="Product",
        description="Product documentation, user guides, release notes"
    ),
    CollectionConfig(
        name="public_faq",
        source_dir="data/public_faq/",
        access_level="public",
        description="Public-facing FAQ and support documentation"
    ),
    CollectionConfig(
        name="legal",
        source_dir="data/legal/",
        access_level="restricted",
        department="Legal",
        description="Legal contracts, compliance documents"
    ),
]
 
 
class EnterpriseIngestionPipeline:
    """
    Ingests documents from multiple collections into FAISS vector stores.
 
    Uses sentence-window chunking (window=2): the best-performing
    configuration from rag-pipeline benchmarks.
 
    Each collection gets its own vector store, allowing:
    - Per-collection access control
    - Independent updates (add new legal docs without re-indexing HR)
    - Collection-specific retrieval weighting
 
    Args:
        embedder        : Embedding model
        output_dir      : Directory to save vector stores
        chunk_window    : Sentence window size (default: 2)
        verbose         : Print progress
    """
 
    def __init__(
        self,
        embedder=None,
        output_dir: str = "./data/vector_stores",
        chunk_window: int = 2,
        verbose: bool = True
    ):
        self.embedder = embedder
        self.output_dir = output_dir
        self.chunk_window = chunk_window
        self.verbose = verbose
        self.vector_stores: Dict[str, Any] = {}
        os.makedirs(output_dir, exist_ok=True)
 
    def ingest_collection(
        self,
        config: CollectionConfig
    ) -> IngestionResult:
        """
        Ingest all documents in a collection.
 
        Args:
            config: CollectionConfig for this collection
 
        Returns:
            IngestionResult with statistics and any errors
        """
        if self.verbose:
            print(f"\n[Ingestion] Processing collection: '{config.name}'")
            print(f"  Source: {config.source_dir}")
            print(f"  Access level: {config.access_level}")
 
        source_path = Path(config.source_dir)
        if not source_path.exists():
            return IngestionResult(
                collection_name=config.name,
                documents_processed=0,
                chunks_created=0,
                access_level=config.access_level,
                errors=[f"Source directory not found: {config.source_dir}"]
            )
 
        # Load documents
        documents = self._load_documents(source_path, config)
        if not documents:
            return IngestionResult(
                collection_name=config.name,
                documents_processed=0,
                chunks_created=0,
                access_level=config.access_level,
                errors=["No documents found in source directory"]
            )
 
        # Chunk using sentence-window strategy
        all_chunks = []
        for doc in documents:
            chunks = self._chunk_document(doc, config)
            all_chunks.extend(chunks)
 
        # Index into FAISS
        vector_store = self._create_vector_store(all_chunks, config)
        self.vector_stores[config.name] = vector_store
 
        if self.verbose:
            print(f"  ✅ {len(documents)} docs → {len(all_chunks)} chunks")
 
        return IngestionResult(
            collection_name=config.name,
            documents_processed=len(documents),
            chunks_created=len(all_chunks),
            access_level=config.access_level
        )
 
    def ingest_all(
        self,
        collections: Optional[List[CollectionConfig]] = None
    ) -> List[IngestionResult]:
        """
        Ingest all collections.
 
        Args:
            collections: List of CollectionConfig (default: DEFAULT_COLLECTIONS)
 
        Returns:
            List of IngestionResult for each collection
        """
        collections = collections or DEFAULT_COLLECTIONS
        results = []
 
        print(f"[Ingestion] Starting enterprise ingestion — {len(collections)} collections")
 
        for config in collections:
            result = self.ingest_collection(config)
            results.append(result)
 
        # Summary
        total_docs = sum(r.documents_processed for r in results)
        total_chunks = sum(r.chunks_created for r in results)
        failed = [r for r in results if not r.success]
 
        print(f"\n[Ingestion] Complete:")
        print(f"  Collections: {len(results)}")
        print(f"  Documents: {total_docs}")
        print(f"  Chunks: {total_chunks}")
        if failed:
            print(f"  Errors: {len(failed)} collections failed")
 
        return results
 
    def _load_documents(
        self,
        source_path: Path,
        config: CollectionConfig
    ) -> List[Dict[str, Any]]:
        """Load documents from a directory."""
        documents = []
        supported_extensions = {".pdf", ".txt", ".md", ".docx"}
 
        for file_path in source_path.glob("**/*"):
            if file_path.suffix.lower() not in supported_extensions:
                continue
 
            try:
                # In production: use DocumentLoader from rag-pipeline
                # For scaffold: return file metadata
                documents.append({
                    "filename": file_path.name,
                    "path": str(file_path),
                    "content": f"[Content of {file_path.name}]",
                    "metadata": {
                        "filename": file_path.name,
                        "collection": config.name,
                        "access_level": config.access_level,
                        "department": config.department or "general",
                        "source_dir": config.source_dir
                    }
                })
            except Exception as e:
                if self.verbose:
                    print(f"  ⚠️  Failed to load {file_path.name}: {e}")
 
        return documents
 
    def _chunk_document(
        self,
        document: Dict[str, Any],
        config: CollectionConfig
    ) -> List[Dict[str, Any]]:
        """
        Chunk a document using sentence-window strategy.
 
        In production: use SentenceWindowChunker from rag-pipeline.
        Scaffold implementation splits by sentence.
        """
        content = document.get("content", "")
        sentences = [s.strip() for s in content.split(".") if s.strip()]
        window = config.chunk_window_size
 
        chunks = []
        for i, sentence in enumerate(sentences):
            start = max(0, i - window)
            end = min(len(sentences), i + window + 1)
            window_content = ". ".join(sentences[start:end])
 
            chunks.append({
                "chunk_id": f"{config.name}_{document['filename']}_{i}",
                "content": window_content,
                "target_sentence": sentence,
                "metadata": {
                    **document["metadata"],
                    "chunk_index": i,
                    "window_size": window
                }
            })
 
        return chunks
 
    def _create_vector_store(
        self,
        chunks: List[Dict[str, Any]],
        config: CollectionConfig
    ) -> Dict[str, Any]:
        """
        Create and save a FAISS vector store for a collection.
 
        In production: use FAISSVectorStore from rag-pipeline.
        Scaffold returns a dict representation.
        """
        store_path = os.path.join(self.output_dir, f"{config.name}.faiss")
 
        # In production:
        # store = FAISSVectorStore()
        # embeddings = [self.embedder.embed_query(c["content"]) for c in chunks]
        # store.add(chunks, embeddings)
        # store.save(store_path)
 
        return {
            "collection": config.name,
            "chunks": chunks,
            "path": store_path,
            "access_level": config.access_level
        }
 
 
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=None, help="Override source directory")
    parser.add_argument("--collection", default=None, help="Ingest specific collection only")
    args = parser.parse_args()
 
    pipeline = EnterpriseIngestionPipeline(verbose=True)
 
    if args.collection:
        matching = [c for c in DEFAULT_COLLECTIONS if c.name == args.collection]
        results = [pipeline.ingest_collection(c) for c in matching]
    else:
        results = pipeline.ingest_all()
 
    for r in results:
        status = "✅" if r.success else "❌"
        print(f"{status} {r.collection_name}: {r.documents_processed} docs, {r.chunks_created} chunks")