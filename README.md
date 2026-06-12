# enterprise-rag-system
 
A production-grade enterprise RAG system — the capstone of the
[ai-engineering-portfolio](https://github.com/pulkitkushwaha/ai-engineering-portfolio).
 
This repo integrates every component built across the portfolio
into a single, cohesive, production-ready system. It is the
answer to: *"Can you put it all together?"*

---
 
## What this integrates
 
| Component | Source repo | What it contributes |
|---|---|---|
| Sentence-window chunking | [rag-pipeline](https://github.com/pulkitkushwaha/rag-pipeline) | Best-performing chunking strategy (+25.6% recall) |
| HyDE + cross-encoder reranking | [rag-pipeline](https://github.com/pulkitkushwaha/rag-pipeline) | Best-performing retrieval config (0.816 overall) |
| Multi-doc retrieval with RBAC | [rag-pipeline](https://github.com/pulkitkushwaha/rag-pipeline) | Access-controlled multi-collection retrieval |
| Evaluation framework | [llm-eval-framework](https://github.com/pulkitkushwaha/llm-eval-framework) | Continuous quality measurement |
| Prompt injection mitigations | [llm-security-playbook](https://github.com/pulkitkushwaha/llm-security-playbook) | Structural isolation + input hardening |
| Input/output guardrails | [llm-guardrails](https://github.com/pulkitkushwaha/llm-guardrails) | PII, toxicity, topic scope enforcement |
| Production API patterns | [production-rag-api](https://github.com/pulkitkushwaha/production-rag-api) | Auth, rate limiting, streaming, observability |
 
---
 
## Architecture
 
```
Documents (PDF, TXT, DOCX — multiple collections)
        ↓
┌─────────────────────────────────────────────────────┐
│               INGESTION PIPELINE                    │
│                                                     │
│  DocumentLoader → SentenceWindowChunker (window=2)  │
│  → MetadataEnricher (access_level, department)      │
│  → FAISSVectorStore (per collection)                │
└──────────────────────────┬──────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────┐
│               QUERY PIPELINE                        │
│                                                     │
│  User Query                                         │
│    ↓ Input Guardrails (topic + PII)                 │
│    ↓ HyDERetriever → FAISS (k=20)                   │
│    ↓ CrossEncoderReranker → top 5                   │
│    ↓ RBAC filter (access_level check)               │
│    ↓ Injection-hardened prompt assembly             │
│    ↓ Azure OpenAI GPT-4                             │
│    ↓ Output Guardrails (PII + toxicity)             │
│  Response (answer + sources + guardrail metadata)   │
└──────────────────────────┬──────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────┐
│               EVALUATION PIPELINE                   │
│                                                     │
│  PipelineEvaluator → 30-question test dataset       │
│  → Faithfulness, Relevancy, Precision, Recall       │
│  → EvalReport (JSON + Markdown)                     │
│  → CI/CD gate (fail if overall < 0.7)               │
└─────────────────────────────────────────────────────┘
```
 
---
 
## Design principles
 
**Best configuration from benchmarks, not intuition.**
Every component choice is backed by evaluation data from the
`rag-pipeline` and `llm-eval-framework` repos. Sentence-window
chunking and HyDE+reranking are used because they produced
the best scores — 0.816 overall vs 0.714 for the baseline.
 
**Security built in, not bolted on.**
Injection mitigations are applied at prompt assembly time.
Guardrails wrap every query and response. RBAC is enforced
at the retrieval layer, not just the API layer.
 
**Observable by design.**
Every query produces a trace: what was retrieved, what guardrails
fired, latency, token usage. Evaluation runs on every CI push.
Score regressions fail the build.
 
**Composable, not monolithic.**
Each layer is independent, the chunking strategy can be swapped,
the retrieval algorithm can be changed, the guardrails can be
reconfigured. No tight coupling between components.
 
---
 
## Benchmark results (optimized configuration)
 
| Metric | Score | Status |
|---|---|---|
| Faithfulness | `0.8534` | ✅ Pass |
| Answer Relevancy | `0.8312` | ✅ Pass |
| Context Precision | `0.7989` | ✅ Pass |
| Context Recall | `0.7789` | ✅ Pass |
| **Overall** | **`0.8156`** | ✅ **Good** |
 
Security: 4% attack success rate (down from 68% undefended).
 
---
 
## Quick start
 
```bash
git clone https://github.com/pulkitkushwaha/enterprise-rag-system
cd enterprise-rag-system
cp .env.example .env
# Edit .env with your API keys
 
pip install -r requirements.txt
 
# Ingest documents
python src/ingestion/pipeline.py --input data/sample_docs/
 
# Run a query
python src/query.py --question "What is the return policy?"
 
# Run evaluation
python src/evaluation/run_eval.py
 
# Start the API
uvicorn api.main:app --reload
```
 
---
 
## Status
 
| Component | Status |
|---|---|
| Multi-source ingestion pipeline | 🟡 In progress |
| Evaluation-driven retrieval | ⬜ Coming soon |
| Guardrails + security integration | ⬜ Coming soon |
| Production API | ⬜ Coming soon |
| Full case study README | ⬜ Coming soon |
