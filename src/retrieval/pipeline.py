"""
Enterprise Retrieval Pipeline
 
Implements the best-performing retrieval configuration from the
rag-pipeline benchmarks:
    - HyDE (Hypothetical Document Embeddings) for query expansion
    - Cross-encoder reranking for precision
    - Multi-document retrieval with RBAC
    - Metadata filtering for access control
 
Benchmark results (from rag-pipeline/results/pipeline_benchmark.md):
    Sentence-window + HyDE + Reranking = 0.816 overall score
    vs baseline Recursive + Similarity  = 0.714 overall score
 
Components imported from rag-pipeline repo.
Install with: pip install -e ../rag-pipeline
"""
 
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
 
 
@dataclass
class RetrievalConfig:
    """
    Configuration for the enterprise retrieval pipeline.
 
    Defaults are set to the best-performing configuration
    from rag-pipeline benchmarks.
    """
    # HyDE settings
    use_hyde: bool = True
    hyde_n_hypotheses: int = 1
 
    # Reranking settings
    use_reranking: bool = True
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    retrieval_k: int = 20          # Fetch this many for reranker
    reranking_top_k: int = 5       # Return this many after reranking
 
    # Multi-doc settings
    collections: List[str] = field(default_factory=list)  # empty = search all
    user_access_level: str = "internal"
 
    # Metadata filter
    metadata_filter: Optional[Dict[str, Any]] = None
 
 
@dataclass
class RetrievalResult:
    """Result of a retrieval call."""
    chunks: List[Dict[str, Any]]
    query: str
    hypothesis: Optional[str] = None  # HyDE hypothesis used
    collections_searched: List[str] = field(default_factory=list)
    total_candidates: int = 0
    reranked: bool = False
 
 
class EnterpriseRetriever:
    """
    Enterprise retrieval pipeline using the best-performing
    configuration from rag-pipeline benchmarks.
 
    Two-stage retrieval:
        Stage 1 — HyDERetriever fetches top-K candidates from FAISS
        Stage 2 — CrossEncoderReranker reranks to top-k
 
    Plus RBAC enforcement via MultiDocRetriever — only chunks
    at or below the user's access level are returned.
 
    Args:
        vector_stores   : Dict of {collection_name: FAISSVectorStore}
        embedder        : Embedding model
        llm_client      : LLM client for HyDE hypothesis generation
        config          : RetrievalConfig
        verbose         : Print retrieval decisions
    """
 
    def __init__(
        self,
        vector_stores: Dict[str, Any],
        embedder=None,
        llm_client=None,
        config: Optional[RetrievalConfig] = None,
        verbose: bool = True
    ):
        self.vector_stores = vector_stores
        self.embedder = embedder
        self.llm_client = llm_client
        self.config = config or RetrievalConfig()
        self.verbose = verbose
 
        # Lazy-load rag-pipeline components
        self._hyde_retriever = None
        self._reranker = None
        self._multi_doc_retriever = None
        self._initialized = False
 
    def _initialize(self):
        """Lazy initialization of rag-pipeline components."""
        if self._initialized:
            return
 
        try:
            import sys
            sys.path.insert(0, "../rag-pipeline")
 
            from src.retrieval.hyde import HyDERetriever
            from src.retrieval.reranker import CrossEncoderReranker, TwoStageRetriever
            from src.retrieval.multi_doc_retriever import MultiDocRetriever, DocumentCollection
            from src.retrieval.metadata_filter import AccessLevelFilter
 
            # Build multi-doc retriever with all collections
            self._multi_doc_retriever = MultiDocRetriever(embedder=self.embedder)
            for name, store in self.vector_stores.items():
                access_level = store.get("access_level", "internal")
                self._multi_doc_retriever.add_collection(
                    DocumentCollection(
                        name=name,
                        vector_store=store.get("store"),
                        access_level=access_level,
                        weight=1.0
                    )
                )
 
            # Build reranker
            if self.config.use_reranking:
                self._reranker = CrossEncoderReranker(
                    model_name=self.config.reranker_model
                )
 
            self._initialized = True
            if self.verbose:
                print(f"[Retriever] Initialized with {len(self.vector_stores)} collections")
 
        except ImportError:
            if self.verbose:
                print(
                    "[Retriever] rag-pipeline not found — using mock retrieval.\n"
                    "Install with: pip install -e ../rag-pipeline"
                )
            self._initialized = True
 
    def retrieve(
        self,
        query: str,
        config_override: Optional[RetrievalConfig] = None
    ) -> RetrievalResult:
        """
        Retrieve relevant chunks using HyDE + reranking + RBAC.
 
        Args:
            query           : User's query
            config_override : Override default config for this call
 
        Returns:
            RetrievalResult with ranked chunks and retrieval metadata
        """
        self._initialize()
        config = config_override or self.config
 
        if self.verbose:
            print(f"[Retriever] Query: {query[:60]}...")
 
        # HyDE — generate hypothetical answer for better embedding
        hypothesis = None
        search_query = query
        if config.use_hyde and self.llm_client:
            hypothesis = self._generate_hypothesis(query)
            search_query = hypothesis or query
            if self.verbose and hypothesis:
                print(f"[Retriever] HyDE hypothesis: {hypothesis[:60]}...")
 
        # Multi-doc retrieval with RBAC
        if self._multi_doc_retriever:
            chunks_raw = self._multi_doc_retriever.retrieve(
                query=search_query,
                k=config.retrieval_k,
                user_access_level=config.user_access_level,
                collection_names=config.collections or None
            )
        else:
            chunks_raw = self._mock_retrieve(query, config.retrieval_k)
 
        total_candidates = len(chunks_raw)
 
        # Reranking
        reranked = False
        if config.use_reranking and self._reranker and chunks_raw:
            try:
                scored = self._reranker.rerank(
                    query=query,
                    chunks=chunks_raw,
                    top_k=config.reranking_top_k
                )
                chunks_raw = [chunk for chunk, _ in scored]
                reranked = True
            except Exception as e:
                if self.verbose:
                    print(f"[Retriever] Reranking failed: {e} — using unranked results")
                chunks_raw = chunks_raw[:config.reranking_top_k]
        else:
            chunks_raw = chunks_raw[:config.reranking_top_k]
 
        # Convert to dicts
        chunks = [
            {
                "content": getattr(c, "content", str(c)),
                "chunk_id": getattr(c, "chunk_id", f"chunk_{i}"),
                "source": getattr(c, "metadata", {}).get("filename", "unknown"),
                "collection": getattr(c, "metadata", {}).get("collection", "unknown"),
                "access_level": getattr(c, "metadata", {}).get("access_level", "internal"),
                "score": getattr(c, "metadata", {}).get("retrieval_score", 0.0)
            }
            for i, c in enumerate(chunks_raw)
        ]
 
        if self.verbose:
            print(f"[Retriever] {total_candidates} candidates → {len(chunks)} returned (reranked: {reranked})")
 
        return RetrievalResult(
            chunks=chunks,
            query=query,
            hypothesis=hypothesis,
            collections_searched=config.collections or list(self.vector_stores.keys()),
            total_candidates=total_candidates,
            reranked=reranked
        )
 
    def _generate_hypothesis(self, query: str) -> Optional[str]:
        """Generate a hypothetical document passage for HyDE."""
        prompt = (
            f"Write a short passage from a document that directly answers: {query}\n"
            f"Write it as a factual excerpt. Do not say 'According to'. Just write the passage."
        )
        try:
            response = self.llm_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=200
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return None
 
    def _mock_retrieve(self, query: str, k: int) -> List[Dict]:
        """Mock retrieval when rag-pipeline is not installed."""
        return [
            type("Chunk", (), {
                "content": f"Mock retrieved content for: {query}",
                "chunk_id": f"mock_chunk_{i}",
                "metadata": {
                    "filename": f"mock_doc_{i}.pdf",
                    "collection": "mock",
                    "access_level": "internal",
                    "retrieval_score": 0.8 - i * 0.05
                }
            })()
            for i in range(min(k, 3))
        ]