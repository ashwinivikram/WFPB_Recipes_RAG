# Retrieval Strategy — WFPB Recipe RAG System
*Week 3 retrieval configuration. Completed: 2026-03-07*

## Approach: Hybrid Search + Reranking

Based on the assessment in `docs/retrieval-analysis.md`, the Week 3 retrieval pipeline adds two improvements over the Week 2 dense-only baseline:

1. **Hybrid search** — dense + sparse vectors combined via RRF fusion
2. **Reranking** — a cross-encoder that sees query and document together for final ordering

No narrowing is implemented (single-domain corpus; see retrieval-analysis.md).

---

## Pipeline Configuration

### Hybrid Configuration
| Parameter | Value |
|---|---|
| Collection name | `wfpb_recipes_week3_hybrid` |
| Input chunks | `data/processed/week2_chunks.json` (692 chunks) |
| Dense vector name | `dense` |
| Dense model | `voyage-3-large` (Voyage AI) |
| Dense dimension | 1024d |
| Dense distance | Cosine |
| Sparse vector name | `sparse` |
| Sparse model | `Qdrant/bm25` (via FastEmbed SparseTextEmbedding) |
| Fusion | RRF (Reciprocal Rank Fusion) |

### Retrieval
| Parameter | Value | Rationale |
|---|---|---|
| Stage 1 retrieve count | 50 | Enough candidates for reranker to work with |
| Reranker model | `rerank-2` (Voyage AI) | Good quality, reasonable cost |
| Rerank top-k | 10 | Standard context window size for LLM generation |

### Generation
| Parameter | Value |
|---|---|
| LLM | Gemini 2.5 Flash |
| Context chunks | Top 10 after reranking |

---

## Why Each Choice

**Dense model: voyage-3-large over BGE-large-en-v1.5**
- Voyage-3-large produces 2048d vectors vs 1024d for BGE — more expressive
- Voyage models are optimised for retrieval (not general sentence embedding)
- Same API already in the project (VOYAGE_API_KEY in .env)

**Sparse: BM25 via FastEmbed**
- BM25 captures exact keyword matches — handles ingredient names well (e.g., "aquafaba", "makhana", "chironji")
- Complements dense: when someone searches a specific ingredient term, BM25 finds it even if semantics miss
- `Qdrant/bm25` is the standard Qdrant-native sparse model, no additional infrastructure needed

**Fusion: RRF (Reciprocal Rank Fusion)**
- Rank-based fusion is robust to score scale differences between dense and sparse
- Qdrant's built-in RRF — no custom code needed

**Reranker: voyage rerank-2**
- Cross-encoder sees full query + document together — more accurate than bi-encoder similarity
- Reranker stage takes top 50 candidates from hybrid search and re-orders them
- Returns top 10 for LLM context — reduces noise from the broad recall stage

---

## Narrowing Decision

See `docs/retrieval-analysis.md` for full rationale. Summary: single-domain corpus, no wrong-domain retrievals, hybrid + rerank sufficient.

The creator query failure (known from Week 2) is addressed via payload filtering, not routing:
- `scripts/09_rag_with_rerank.py` accepts `--creator "Name"` to apply a Qdrant keyword filter
- This is simpler and more reliable than two-stage routing for this use case

---

## Scripts

| Script | Purpose |
|---|---|
| `scripts/08_index_hybrid.py` | Create `wfpb_recipes_week3_hybrid` collection, embed with Voyage + BM25, upsert |
| `scripts/09_rag_with_rerank.py` | Interactive RAG: hybrid search → rerank → Gemini answer |
| `scripts/10_evaluate_week3.py` | Compare Week 2 baseline vs Week 3 pipeline on 14 test questions |

---

## Baseline Comparison

| System | Collection | Embedding | Search | Rerank |
|---|---|---|---|---|
| Week 2 (baseline) | `wfpb_recipes_week2` | BGE-large (1024d) | Dense top-5 | None |
| Week 3 (this week) | `wfpb_recipes_week3_hybrid` | Voyage-3-large (1024d) | Hybrid top-50 → RRF | Voyage rerank-2 → top-10 |
