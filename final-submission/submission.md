# Final Capstone Submission

## Student Name(s)
Ashwini Vikram

## Product Name
WFPB Recipe Assistant

## Project Title
Retrieval-Augmented Chatbot for Highly Curated Whole Food Plant-Based Recipes

## Demo Video
https://www.loom.com/share/b03a3d5e23ac4985a9df61c10d3f272c

---

## Problem Statement
Finding authentic, ad-free, and strict Whole Food Plant-Based (WFPB) recipes online is incredibly time-consuming and fraught with inaccurate ingredient substitutions. The general internet requires sifting through long blog posts and non-compliant variations. This system provides instant, precise, hallucination-free recipe retrieval and exact preparation methodology extracted directly from 22 trusted, premium WFPB cookbooks.

## Data Overview
- **Corpus size:** 22 documents, ~692 carefully chunked recipes
- **Data sources:** Thankful2Plants.com, curated PDF diet guides, and manual cookbook scans.
- **Formats:** PDF extracted to Markdown text.
- **Domain:** WFPB Diet guidelines, recipes, techniques, and nutritional constraints.

## System Architecture

### Chunking Strategy (Week 2)
- **Strategy:** Custom Regex Boundary Detection
- **Configuration:** Chunking via `ALL-CAPS` headers separating Component Sub-recipes vs Main Assembly parent recipes.
- **Key decision:** Moving away from standard RecursiveCharacterTextSplitter towards explicit semantic blocks. Traditional token-based splitting was severing the ingredients from their assembly steps randomly, making answers useless.

### Retrieval Pipeline (Week 3)
- **Hybrid search:** `voyage-3-large` (1024d Dense) + FastEmbed SparseTextEmbedding (Sparse BM25), fused via Reciprocal Rank Fusion (RRF).
- **Reranking:** `voyage-rerank-2` cross-encoder, reranking from Top 50 down to the Top 10 contexts.
- **Narrowing:** Skipped. The corpus is a strictly homogeneous single-domain dataset (WFPB), rendering two-stage classification/categorical routing unnecessary and purely overhead.

### Evaluation Strategy (Week 4)
- **Golden dataset:** 15 manually curated Q&A pairs spanning 6 distinct query types (factoids, thematic, strategy, multi-ingredient).
- **Evaluation methods:** Deterministic Hit@1 matching (Voyage Cosine scoring) triangulated against a Decomposed LLM Judge (Faithfulness, Relevance, Context Precision).
- **Key finding:** The integration of dual metrics highlighted a massive system blindspot. The Deterministic method returned 100% Hit@1, claiming perfection. The LLM Judge outputted 1/5 for Answer Relevance, revealing that while the vector math fetched the right Recipe Title, the underlying chunk string completely lacked the cooking instructions for the ingredients.

### Production System (Week 5)
- **Services implemented:** Intent Routing (classifying FACTUAL, HOW_TO, COMPARISON, and PLAN requests), Redis-backed Sliding Window Conversation Memory (for context-aware followups), and Voyage-backed Redis Semantic Caching.
- **Services skipped:** Opik Observability tracing. Intentionally deferred to prioritize stabilizing the Docker multi-container core infrastructure over telemetry.
- **Deployment:** Containerized multi-service deployment via `docker-compose` combining FastAPI/Uvicorn, Redis Stack Server, and Gemini Generation natively mounted locally.

## Results
- **What the system does well:** Thematic lookups ("Give me an Indian Street food recipe") and exact Author/Creator lookups. The application is completely hallucination-free (scoring perfect 5.0 in Faithfulness). 
- **Query types it handles best:** Broad category discovery constraints, multi-ingredient search, and caching repetitive questions in under 50ms.
- **What you would improve next:** The Chunking Script needs a major refactoring to recursively bind sub-recipe ingredients strictly to their parent methodology instructions to prevent "Truncated Methods."

## Self-Assessment

| Criteria | Score (1-5) | Notes |
|----------|-------------|-------|
| Problem scoping clarity | 5 | Targeted a highly rigid domain (WFPB) constraint making RAG essential. |
| Data sourcing and curation | 4 | Limited volume size, but high semantic quality. |
| Chunking strategy reasoning | 5 | Caught the fundamental difference between standard token splitting vs semantic sub-recipes. |
| Retrieval pipeline quality | 5 | BM25 + Voyage cross-encoding handled creator strings excellently. |
| Production decisions | 5 | Prioritized practical user experience (Speed + Memory) over telemetry bloat. |
| Documentation clarity | 4 | Addressed all required triangulation details. |
| Overall system quality | 4 | Excellent prototype but requires the trunk chunking fix before public deployment. |
