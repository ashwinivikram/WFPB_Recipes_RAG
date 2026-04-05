# Retrieval Analysis — WFPB Recipe RAG System
*Week 3 ASSESS step. Completed: 2026-03-07*

## Constraint Assessment

| Question | Answer |
|---|---|
| What is your latency budget? | Interactive — seconds are acceptable. No real-time requirement. |
| What is your cost budget? | Low. Personal project, occasional use. |
| How critical is accuracy? | High. Recipe instructions need to be precise; wrong ingredients or steps matter. |
| What query volume do you expect? | Very low — personal use, a few queries per session. |

---

## Corpus Assessment

| Question | Answer |
|---|---|
| Is your corpus heterogeneous (multi-domain, multi-SDK)? | No. Single domain: Whole Food Plant-Based recipes. 4 recipe books + 1 WhatsApp chat log. |
| Are domain boundaries clear and unambiguous? | Yes. Recipe cards have consistent structure (title, ingredients, instructions). Chat log is clearly separate. |
| Do you have high-quality metadata? | Yes. Every chunk carries: `category`, `creator`, `chunk_type`, `source_pdf`. All indexed in Qdrant. |
| What are your typical query patterns? | (1) Sub-recipe factoids — "how do I make hummus for this sandwich?" (2) Ingredient lookups — "what uses sweet potatoes?" (3) Thematic discovery — "show me no-cook options". (4) Creator queries — "what did Gurmeet make?" |

---

## Corpus Characteristics

**Size:** 692 chunks (Week 2 chunking strategy)
- 632 unchanged recipe cards
- 60 focused chunks from 30 sub-recipe splits
- 4 empty cover pages excluded

**Token distribution (from Week 2 corpus analysis):**
- 68% of chunks are under 200 tokens (short, specific recipe cards)
- Mean chunk length: ~180 tokens
- Long tail: a few chat entries reach 400+ tokens

**Known retrieval failures from Week 2 evaluation:**
- Creator queries (e.g., "What did Kumar Natarajan share?") — dense vector search encodes content, not authorship
- Strategy-exclusion queries (e.g., "no-cook sandwiches") — absence of a technique isn't represented in embeddings

---

## Narrowing Decision

**Decision: Skip narrowing. Hybrid + rerank is sufficient.**

Rationale using the course decision checklist:

| Check | Result | Recommendation |
|---|---|---|
| No heterogeneity boxes | ✓ Single domain, single content type | Skip narrowing |
| Heterogeneous + accuracy-critical + latency-flexible | ✗ Not applicable | — |
| Quality metadata available | ✓ Yes — category, creator, chunk_type indexed | Consider metadata filtering for creator queries only |
| Cost-constrained or latency-critical | ✗ Not a concern | — |

**Why narrowing would hurt here:**
- The corpus is single-domain (WFPB recipes) — no wrong-domain retrievals to filter out
- Hybrid + rerank already covers the "aboutness" vs "contains" gap
- Two-stage routing adds latency and cost for a personal-use system
- Metadata filtering (hard filters) failed in course experiments; our creator queries are better fixed with payload filtering at query time, not routing

**Creator query workaround (not narrowing):**
The `creator` field is indexed as a keyword payload in Qdrant. A dedicated creator-filter mode in the RAG pipeline (passing `must=[FieldCondition(key="creator", match=MatchValue(value=name))]`) is a simpler and more reliable fix than two-stage routing. This is implemented as an optional flag in `scripts/09_rag_with_rerank.py`.
