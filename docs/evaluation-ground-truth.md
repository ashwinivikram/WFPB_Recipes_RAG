# Evaluation Ground Truth

**Project:** WFPB Recipe RAG System  
**Author:** Ashwini Vikram  
**Week:** 4  
**Date:** March 2026  

---

## 1. Dataset Overview

Our golden dataset (`evaluations/golden_dataset.json`) acts as the single source of truth for measuring the retrieval and generation quality of the WFPB recipe RAG system.

- **Total questions:** 15
- **Storage:** JSON format with question, type, expected source, reference chunks, and Gemini-generated reference answer.

---

## 2. Question Types & Coverage

The dataset is strictly curated to test both the "easy" paths (direct recipe matches) and the "hard" edge-cases (strategies, multi-ingredient overlaps) discovered during Weeks 1–3.

| Type | Count | Purpose | Example |
|---|---|---|---|
| **Sub-recipe Factoid** | 6 | Tests component chunking | *How do I make walnut mushroom pate?* |
| **Main Recipe Factoid** | 2 | Tests assembly chunking | *How do I make Kathi Rolls?* |
| **Ingredient Query** | 1 | Tests specific ingredient mapping | *What recipes use sweet potato?* |
| **Multi-ingredient Query** | 1 | Tests overlapping constraints | *What recipes can I make with chickpeas and spinach together?* |
| **Strategy Query** | 1 | Tests implicit traits | *Give me a quick no-cook sandwich recipe* |
| **Creator Query** | 1 | Tests metadata extraction | *What recipes did Kumar Natarajan create?* |
| **Thematic-Analytical** | 3 | Tests broad semantic grouping | *What are some Indian street food recipes...?* |

---

## 3. Selection & Validation Approach

**Selection (Manual curation + Bootstrapped):**
Since this system is in the development phase and is not yet taking public user queries, the 15 questions were manually curated. They were drawn directly from failures and successes observed in the Traces during the Week 1 and Week 2 evaluations. 

**Validation (Self-validated with LLM assistance):**
1. **Reference Chunks:** The 15 queries were run against the Week 3 Hybrid index. The top 5 returned chunks were visually verified against my domain knowledge of the Thankful2Plants.com corpus.
2. **Reference Answers:** Given the target chunks, we used a constrained prompt against Gemini 2.5 Flash to generate a "perfect", concise (<150 word) reference answer. These answers were reviewed to ensure they properly reflected the context.

---

## 4. Known Gaps

While covering the major edge-cases from Weeks 1–3, this golden dataset has minor gaps:
1. **No conversational context:** The dataset treats every query as a zero-shot standalone question. It does not test multi-turn RAG (e.g., *"What about replacing the spinach in the previous recipe?"*).
2. **Missing "Negative" constraints:** Other than the "no-cook" strategy query, it lacks explicit "exclude X" questions (e.g., *"Sandwiches without avocado"*), which dense models notoriously struggle with.

When the system moves to production, production logs will be used to fill these gaps.
