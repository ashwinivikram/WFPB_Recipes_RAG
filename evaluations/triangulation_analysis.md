# Triangulation Analysis — WFPB Recipe RAG System

**Author:** Ashwini Vikram  
**Project:** WFPB Recipe RAG System  
**Week:** 4 — Formal Evaluation  
**Date:** March 2026  

---

## 1. Evaluation Overview

### Systems Evaluated
- **Comparison baseline:** `wfpb_recipes_week2` (Dense-only BGE-large-en-v1.5, top-k=5)
- **Target system:** `wfpb_recipes_week3_hybrid` (Voyage-3-large + BM25 hybrid search → Voyage rerank-2, top-k=10)

### Golden Dataset Size / Type Coverage
15 manually curated questions representing actual usage scenarios across 6 query types:
- Sub-recipe factoid (6) — *e.g., "How do I make walnut mushroom pate?"*
- Main recipe factoid (2) — *e.g., "How do I make Kathi Rolls?"*
- Ingredient query (1) — *e.g., "What recipes use sweet potato?"*
- Multi-ingredient query (1) — *e.g., "What recipes can I make with chickpeas and spinach together?"*
- Strategy query (1) — *e.g., "Give me a quick no-cook sandwich recipe"*
- Creator query (1) — *e.g., "What recipes did Kumar Natarajan create?"*
- Thematic-analytical (3) — *e.g., "What are some Indian street food recipes I can make at home?"*

### Methods Chosen & Why
1. **Method 1: Deterministic Semantic Metrics (Voyage)** 
   - *Why:* Fast, highly reproducible. Captures exactly how well our retrieval engine matched the known ground truth chunk (Hit@1) and the semantic relevance of the top retrieved context. Lexical answer overlap (ROUGE-1 F1) tests rigid extraction.
2. **Method 2: Decomposed LLM Judge (Gemini 2.5 Flash)**
   - *Why:* Holistic quality measurement. Splitting into three scores (`Faithfulness`, `Answer Relevance`, `Context Precision`) prevents the "single score blur" seen in naive LLM judgers.

---

## 2. Results Summary

| Metric Dimension | Method 1: Deterministic | Method 2: Judge (1-5) |
|---|---|---|
| **Retrieval Success** | Context Hit@1: **100%** | Context Precision: **3.47/5** |
| **Retrieval Quality** | Context Relevance (Cosine): **0.84** | — |
| **Answer Quality** | Answer ROUGE-1 F1: **0.26** | Answer Relevance: **3.00/5** |
| **Hallucination** | — | Faithfulness: **5.00/5** |

*(Note: Method 1 ROUGE-1 represents lexical token overlap with the golden answer. A vocabulary-rich RAG answer may have low overlap but still be highly relevant.)*

---

## 3. Where Methods Agree

**1. The system never hallucinates.**
- **Method 1** doesn't track this explicitly, but **Method 2** scored Faithfulness at a perfect **5.00/5** across all 15 questions. The generated answers are strictly grounded in the retrieved chunks.

**2. Thematic queries excel.**
Both methods identified broad, thematic queries as strong points:
- **q07 (sweet potato)**: Method 1 (Hit@1=1, CtxRel=0.80), Method 2 (Rel=5, CtxP=5).
- **q11 (Indian street food)**: Method 1 (Hit@1=1, CtxRel=0.75), Method 2 (Rel=5, CtxP=5).
- **q14 (Savory pancakes)**: Method 1 (Hit@1=1, CtxRel=0.81), Method 2 (Rel=5, CtxP=5).
*Conclusion:* The hybrid BM25 + dense approach is extremely good at answering broad category questions.

**3. Creator queries work but retrieve noisy contexts.**
- **q09 (Kumar Natarajan)**: Method 1 confirmed the top chunk hit (CtxRel=0.66). Method 2 gave Answer Relevance a 5/5 (the LLM extracted the right answer), but Context Precision matched the low cosine score (5/5). The hybrid system successfully used BM25 to find the creator name, but the retrieved chunks contained a mix of relevance.

---

## 4. Where Methods Disagree

The most critical insight came from questions where the Deterministic metric showed a perfect hit, but the LLM Judge scored Answer Relevance very poorly.

**The "Truncated Method" Disagreement:**
- **q03 (Zucchini chutney):** Method 1: Hit@1=1, CtxRel=0.90. Method 2: Answer Relevance=1/5, CtxP=2/5.
- **q04 (Homemade hummus):** Method 1: Hit@1=1, CtxRel=0.88. Method 2: Answer Relevance=1/5, CtxP=2/5.
- **q12 (Ragda pattice):** Method 1: Hit@1=1, CtxRel=0.88. Method 2: Answer Relevance=1/5, CtxP=4/5.
- **q13 (Mushroom sauce):** Method 1: Hit@1=1, CtxRel=0.91. Method 2: Answer Relevance=2/5, CtxP=2/5.

**Why this happened:** The deterministic metric only checked if the *name* of the top chunk matched the golden reference (which it did perfectly, Hit@1=100%). The high cosine context relevance (0.88-0.91) confirmed it was semantically similar. 

However, the Judge actually *read* the chunks. It found that while the chunks were indeed the correct sub-recipes (ingredients), the **instructions for how to make them were missing or truncated**. The LLM correctly judged the generated answer as 1/5 ("off-topic or fails to answer the question") because it could only list the ingredients, not the *how-to* steps the user asked for.

The root cause lies in our Week 2 Python script (`scripts/06_chunk_with_strategy.py`). While our RegEx perfectly detected the sub-recipe boundary (which is why Hit@1 scored 100%), the text-splitting logic accidentally left the actual cooking instructions stranded inside the main "assembly" chunk, rather than keeping them with the ingredients in the "component" chunk.

**Verdict:** The LLM Judge is more trustworthy here. The deterministic metric measured "did we retrieve the right chunk ID?" but the Judge measured "does this chunk actually contain the answer?" This exposes a data representation flaw (ingredients separated from instructions during extraction), not a retrieval failure.

---

## 5. System Assessment

Based on the triangulated data, the `wfpb_recipes_week3_hybrid` system has distinct strengths and weaknesses:

### Strongest Dimensions
1. **Faithfulness / Grounding:** Perfect 5/5. The LLM handles the chunk context exceptionally well and refuses to invent WFPB recipes.
2. **Retrieval Precision (Target ID):** 100% Hit@1. The system is incredibly good at finding the correct recipe card for named queries.
3. **Thematic / Multi-Ingredient Discovery:** Broad queries (q07, q11, q14) scored perfectly on relevance. The combination of dense semantic understanding and sparse keyword matching excels at grouping related recipes.

### Weakest Dimensions
1. **Completeness of Sub-Recipes:** The "Truncated Method" disagreement (q03, q04, q12, q13) shows that our chunking boundaries sometimes sever ingredients from their instructions. A chunk titled "Zucchini Chutney" only contains ingredients, leaving the generated answer useless (Score 1/5).
2. **Strategy / Negative Constraint Queries:** "No-cook" (q08) scored poorly on Answer Relevance (2/5) even with a high Context Relevance (0.78). Dense embeddings struggle to differentiate the absence of a trait ("no cooking") from the presence of it.

### Immediate Priority
The #1 fix required is to revisit the data extraction/chunking pipeline. We must ensure that when sub-recipes are split into separate chunks, the cooking method instructions are bundled with their respective ingredient lists.

---

## 6. Future Evaluation Strategy

**Current Maturity Level:** Level 2 (Development system with a formal baseline evaluation). 

**Next Steps & Ongoing Strategy:**
Given the constraints of a solo developer in a slow-moving domain (Thankful2Plants.com updates infrequently), continuous complex evaluation is unnecessary overhead.

1. **Fix & Re-run (Short-term):** We will address the chunking boundary completeness issue. To verify the fix, we will re-run the `14_run_judge_eval.py` script. Success is defined as q03/q04/q12/q13 Answer Relevance scores jumping from 1/5 → 4/5 or 5/5.
2. **Production Monitoring (Long-term):** When this system is deployed as a Slack/Discord bot, we do not need to run the expensive decomposed LLM judge on every query. We will log the `Context Relevance` (cosine) score for every user query. If we observe production queries returning top chunks with Cosine < 0.60, we will flag those queries, add them to `evaluations/golden_dataset.json`, manually curate an answer, and use them to test future pipeline improvements.
