# Evaluation Strategy

**Project:** WFPB Recipe RAG System  
**Author:** Ashwini Vikram  
**Week:** 4  
**Date:** March 2026  

---

## 1. Scope Decisions

- **Goal:** Assessed the absolute quality of the Week 3 Hybrid retrieval system (Voyage-3-large + BM25) and compared it against the Week 2 dense-only baseline.
- **Constraints:** Time-boxed evaluation by a single developer on a static, slowly-changing corpus (22 PDFs).
- **Priorities:** High retrieval accuracy (fetching the right recipe) and faithfulness (no hallucinations of ingredients). Because the domain is static, a one-time intensive development evaluation is prioritized over complex continuous CI/CD evaluation pipelines.

---

## 2. Ground Truth Decisions

- **Dataset:** 15 curated questions (`evaluations/golden_dataset.json`).
- **Generation:** Queries were drawn from real Week 1/2 failures. Ground truth context chunks were determined by running the queries, verifying the chunks manually against the known PDFs, and then using a constrained LLM prompt to generate the "Golden Answer" based strictly on those valid chunks.
- **Rationale:** This bootstrapped approach is highly efficient for a solo developer when external domain experts are unavailable, provided the developer has strong familiarity with the corpus.

---

## Evaluation Methods

To avoid the pitfalls of single-score LLM grading seen in Week 3, I implemented a Triangulation approach using two distinct methods:

1. **Method 1: Deterministic Semantic Metrics (`scripts/13_run_deterministic_eval.py`)**
   - *Metrics:* Context Hit@1 (binary), Context Relevance (Cosine similarity to target chunk), Answer ROUGE-1 F1.
   - *Rationale:* Provides a fast, inexpensive, mathematically reproducible baseline for retrieval success. Hit@1 guarantees we found the target recipe card.

2. **Method 2: Decomposed LLM Judge (`scripts/14_run_judge_eval.py`)**
   - *Metrics:* Faithfulness (1-5), Answer Relevance (1-5), Context Precision (1-5).
   - *Rationale:* By decomposing the score, we isolated generation flaws (hallucination) from retrieval flaws (noise). This specific matrix was chosen to catch cases where we retrieve the right chunk (high Hit@1) but the chunk text is inadequate to answer the question (low Answer Relevance).

---

## 4. Findings & Future Maintenance

The triangulated strategy was highly successful. It revealed a critical flaw: **The "Truncated Method" disagreement.**

Deterministic metrics showed 100% Hit@1, but the Decomposed Judge gave the generated answers a 1/5 for Answer Relevance on sub-recipes. The judge successfully identified that while we retrieved the correct sub-recipe chunk, the chunk only contained the ingredients list and was missing the cooking instructions.

**Future Maintenance:**
1. Fix the chunking pipeline to bundle instructions with sub-recipe ingredient lists.
2. In production, log the Cosine Similarity of user queries to the top chunk. If it drops below `0.60`, flag the query and add it to the golden dataset for the next evaluation cycle.
