# Evaluation Scope — WFPB Recipe RAG System

**Project:** WFPB Recipe RAG System  
**Author:** Ashwini Vikram  
**Week:** 4 — Formal Evaluation  
**Date:** March 2026  

---

## Evaluation Goal Assessment

| Question | Answer |
|---|---|
| What stage is your system in? | **Development** — pipeline built over Weeks 1–3, not yet in production |
| What decision are you making? | **System comparison + quality assessment** — comparing Week 2 (sub-recipe chunking, dense-only) vs Week 3 (hybrid+rerank), and assessing absolute answer quality |
| How often will you evaluate? | **One-time** (with framework designed for periodic re-use as data grows) |
| What are the stakes of a wrong answer in your domain? | **Low–Medium.** This is a personal recipe assistant, not a medical or financial domain. A wrong answer (e.g., missing a recipe or citing wrong ingredients) is inconvenient but not harmful. However, accuracy still matters — a system that misses "no-cook" recipes for someone heat-intolerant is a real failure. |

---

## Constraint Assessment

| Question | Answer |
|---|---|
| What is your evaluation budget? | Minimal. Free-tier Gemini API + Voyage API (existing keys). Time budget: ~1 day. |
| Do you have domain experts for validation? | No external experts. Self-validation only (I know the WFPB recipe corpus well from Weeks 1–3). |
| How fast does your domain change? | **Slowly.** The Thankful2Plants.com corpus is static (22 PDFs, CC BY-NC-ND 4.0). New PDFs may be added over months, not days. |
| How much time can you spend on evaluation? | ~4 hours for scripting + running. Triangulation analysis written in ~2 hours. |

---

## Priority Checklist

- [ ] Accuracy-critical — Wrong answers have real cost
- [ ] Fast-moving domain — Content changes weekly or more
- [x] Multiple systems to compare — Need ranking, not just pass/fail *(Weeks 2 vs 3 comparison)*
- [ ] Regulated domain — Need audit trail
- [ ] Production system — Already serving users
- [x] Solo developer — Limited time and budget

---

## Scope Interpretation

This is a **development-stage system evaluated by a solo developer, comparing two system versions**. Based on the checked priorities:

- **Ground truth approach:** Manual curation + bootstrapped validation. The 14 test questions from Weeks 2–3 are already carefully curated. I will extend these with reference answers and reference chunk IDs using the existing corpus knowledge.
- **Evaluation methods:** Deterministic semantic metrics (fast, reproducible baseline) + Decomposed LLM judge (broader quality signal including faithfulness and answer relevance). Together they cover retrieval quality and generation quality.
- **Evaluation depth:** Per-question analysis on 15 questions across 6 query types (sub-recipe factoid, main recipe factoid, ingredient-query, strategy-query, creator-query, thematic-analytical).

The simplicity of this scope is appropriate: a solo developer with a static domain corpus doesn't need continuous monitoring or audit trails. The evaluation framework is designed to re-run when new PDFs are added to the corpus or when retrieval strategies change.

---

## Systems Being Evaluated

| System | Collection | Embedding | Retrieval | Top-k |
|---|---|---|---|---|
| Week 2 baseline | `wfpb_recipes_week2` | BGE-large-en-v1.5 (dense) | Dense cosine | 5 |
| Week 3 (primary) | `wfpb_recipes_week3_hybrid` | Voyage voyage-3-large (dense) + BM25 sparse | Hybrid RRF → Voyage rerank-2 | 50→10 |

The Week 3 system is the primary system being evaluated for absolute quality. The Week 2 system serves as the comparison baseline.

---

*Data source: Thankful2Plants.com by Gurmeet Manku (CC BY-NC-ND 4.0)*
