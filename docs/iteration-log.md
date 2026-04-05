# Iteration Log — Week 2 Chunking Strategy

**Author:** Ashwini Vikram
**Week:** 2 — Chunking Strategy
**Project:** WFPB Recipe RAG System

This document records what I tried, what happened, and what I changed during the Week 2 chunking experiment.

---

## Iteration 0 — Baseline (Week 1 naive strategy)

**What:** One recipe card = one chunk. No splitting. No filtering of empty chunks.
**Collection:** `mcp_phase1_baseline`
**Chunks:** 666 (including 4 empty cover-page chunks)

**What worked:**
- Specific named-recipe queries (e.g., "Walnut Mushroom Pate recipe") scored well if the recipe had a standalone card
- Ingredient-based queries worked very well (dense vector captures ingredient co-occurrence naturally)
- LLM generation was faithful — no hallucinations

**What didn't work:**
- Sub-recipe queries: "Give me a hummus recipe" returned sandwich cards with hummus buried inside
- Creator queries: "What did Kumar Natarajan create" failed because creator name is semantically diluted by ingredient/instruction content
- Meal planning queries: top-k=5 returned too few diverse options

**Key observation from `data_quality_notes.md`:**
> "Sub-recipes: Extractions capture sub-recipes but keep them in the same chunk, meaning multi-component recipes dilute the main embedding signal."

---

## Iteration 1 — Corpus Analysis (Prerequisite to Chunking)

**What:** Ran Python token-count analysis across all 666 processed chunks before deciding on a chunking strategy.

**Result:**
- 68% of PDF recipe chunks are < 200 tokens (median 156 tokens)
- 0% exceed the BGE-large-en-v1.5 512-token hard limit
- 24 recipes (10.1%) contain embedded sub-recipes
- 4 empty cover-page chunks

**What this changed:** Abandoned plans to apply recursive chunking (standard advice for large documents). Corpus is already small — the problem is the inverse: 24 cards are too big because they embed two recipes.

**Decision:** Document-level strategy (no splitting for 95% of corpus) + targeted sub-recipe boundary detection for the 24 affected cards.

**Written:** `docs/chunking-analysis.md`, `docs/chunking-strategy.md`

---

## Iteration 2 — First Implementation (script 06, v1)

**What:** Wrote `scripts/06_chunk_with_strategy.py` with the initial sub-recipe detection logic.

**Initial approach:**
- Regex: `r"(?:^|\n)([A-Z][A-Z &|\-\/]{1,40}):\s*\n"` — required newline AFTER the colon
- Named the main chunk with the split-header name, sub-chunk with original name
- Process words: standard set (BATTER, DOUGH, STUFFING, etc.)

**Dry-run result:** Only 7 splits detected out of the expected ~24.

**Problem diagnosed:** The regex required a literal `\n` after the colon. But recipe instructions use the format `HEADER: instruction text continues on same line` (e.g., `SWEET POTATO PARATHA: Mash cooked sweet potatoes...`). The regex missed all of these.

**Specific failure:** Kathi Rolls — the sub-recipe starts with `SWEET POTATO PARATHA: Mash...` which has no newline after the colon. The regex found 0 headers in Kathi Rolls instructions.

---

## Iteration 3 — Regex Fix + Naming Logic Fix

**What:** Rewrote the core detection in `06_chunk_with_strategy.py`.

**Changes:**
1. **Fixed regex:** `r"(?<![A-Za-z])([A-Z][A-Z ]{2,39}[A-Z]):\s*"` — removed newline requirement; uses negative lookbehind to avoid matching mid-word.
2. **Fixed naming logic:** Reversed which chunk gets which name. Component chunk (earlier text) gets the first food-named header found in that portion (e.g., "Walnut Mushroom Pate"). Assembly chunk (later text) keeps the original recipe name. Previously was backwards.
3. **Added safety check:** If no distinct sub-recipe found in earlier portion (all headers are process words), and the split-at header matches the recipe name, skip the split. This catches "Adai: BATTER / GRIND / FERMENT / ADAI" which previously split into "Adai + Adai".
4. **Extended PROCESS_WORDS:** Added GRIND, FERMENT, SOAK, SHAPE, KNEAD.

**Dry-run result:** 7 → 52 splits detected. All target recipes now split correctly (Kathi Rolls ✓, Walnut Mushroom Pate ✓, Hummus ✓, Zucchini Chutney ✓).

**New problem:** 52 splits included many false positives. Examples:
- `Sprouted Mung Dal Cheela → Sprouted Mung Dal Cheela` (same name both sides)
- `Dhokla → Tadka` (TADKA: is a finishing technique, not a sub-recipe)
- `Moong & Quinoa Cheela → Soaking` (SOAKING: is a process step; only SOAK was in PROCESS_WORDS)
- `Oven Roasted Fries → Note` (NOTE: is an annotation, not a recipe)
- `Kale Chips → Spice Rub` (SPICE RUB: is a preparation step, not a standalone recipe)

---

## Iteration 4 — False Positive Cleanup

**What:** Investigated each false positive by inspecting actual recipe instruction headers, then applied targeted fixes.

**Fixes applied:**
1. **New PROCESS_WORDS added:** `SERVE`, `SOAKING`, `NOTE`, `NOTES`, `TADKA`, `TEMPERING`, `SPICE`, `RUB`, `MIX`, `MASALA`, `PASTE`, `DRY`, `PAN`, `RAINBOW`, `VEGGIES`
   - SERVE: many recipes end with `SERVE: Plate hot and serve with chutney` which was triggering splits
   - SOAKING: the SOAK process word was already there but SOAKING wasn't
   - NOTE: `NOTE: This recipe can be...` was being detected as a food header
   - TADKA: Indian tempering technique, not a standalone meal
   - SPICE RUB, MASALA PASTE: spice/seasoning preparations, not standalone sub-recipes

2. **New safety check in `split_recipe()`:** If `comp_name == original_name` (component name falls back to original because no food header was found in the earlier portion), return `[recipe]` unchanged. This catches cases where the "food header" is actually just the recipe name repeated at the end (e.g., `KALE CHIPS: Toss with oil and bake` where the entire recipe is in the KALE CHIPS section).

**Dry-run result:** 52 → 30 splits. All key target splits retained; ~22 false positives eliminated.

**Final count:**
- Input: 666 chunks (Week 1 naive)
- Skipped (empty/cover pages): 4
- Passed through unchanged: 632
- Split: 30 recipe cards
- Output: 692 chunks (Week 2)

---

## Iteration 5 — Indexing and Evaluation

**What:** Ran `scripts/07_index_with_strategy.py` to create the `wfpb_recipes_week2` Qdrant collection, then `scripts/08_evaluate_chunking.py` to compare both collections.

**Bug found in script 07:** Chat entries (from WhatsApp ingest) don't have an `id` field — they only have `recipe_name`, `creator`, `category`, `text`. The upsert function assumed `chunk["id"]` always existed.

**Fix:** Added fallback ID generation: `chunk.get("id") or f"{recipe_name}__{creator}__{category}"`.

**Evaluation results:**
- Week 2 wins: 10/14 queries (71%)
- Average usefulness: 4.07 vs 2.71 (+1.36 points)
- Average signal %: 44.3% vs 31.4% (+12.9 percentage points)
- Sub-recipe factoid queries: Week 2 wins 6/7

**Key finding confirmed:** The split strategy works as hypothesized. Dedicated component chunks have measurably higher cosine similarity to targeted sub-recipe queries.

---

## What Did NOT Improve (Known Limitations)

1. **Creator queries:** Both systems fail. Dense vector search cannot effectively handle "what did Creator X make?" queries because creator name is a small part of the embedding text. Fix requires Qdrant payload filtering or hybrid BM25+dense search.

2. **Strategy-exclusion queries** (e.g., "no-cook recipes"): Both systems return identical results. The concept of "no cooking steps" is not well-represented in dense embeddings.

3. **Some borderline splits** remain in the final index — e.g., `Brown Rice Flour` (ingredient prep) or `Puttu Flour` (preparation section). These are minor quality issues that don't significantly affect retrieval for the main use cases.

---

## What I Would Try in Iteration 6 (If Time Permitted)

1. **Hybrid search (BM25 + dense):** Would fix creator and keyword queries. Qdrant supports sparse vectors (BM25) alongside dense vectors.
2. **Metadata field weighting:** Embed creator name more prominently in the text template — e.g., repeat it twice or weight it separately.
3. **Chat entry grouping:** 135 chat entries are under 50 tokens (too short for meaningful embeddings). Group related tips into ~200-token chunks.
4. **Evaluation with top-k=8 or 10:** For meal planning queries, more chunks retrieved would give more diverse options.

---

## Week 3 — Retrieval Optimization (Hybrid + Rerank)

**What:** Upgraded the retrieval pipeline from dense-only to hybrid search (dense + sparse BM25) with Voyage reranking. Corpus and chunks unchanged (692 chunks from Week 2).

**Collection:** `wfpb_recipes_week3_hybrid`
**Dense model:** Voyage voyage-3-large (1024d)
**Sparse model:** Qdrant/bm25 (BM25 keyword matching via FastEmbed)
**Reranker:** Voyage rerank-2, top 50 → top 10

---

### Iteration 6 — Hybrid Indexing

**What changed:** Re-indexed all 692 Week 2 chunks into a new collection with two vector types:
- Dense: Voyage voyage-3-large (replaced BGE-large-en-v1.5)
- Sparse: BM25 via `fastembed.SparseTextEmbedding("Qdrant/bm25")`

**Bug encountered:** voyage-3-large returns 1024d vectors, not 2048d as documented in course materials. Fixed by changing `EMBEDDING_DIM = 2048` to `EMBEDDING_DIM = 1024`.

**Result:** 692 chunks indexed successfully in 35 seconds. 688 unique points (4 hash collisions, same as Week 2).

---

### Iteration 7 — Week 3 Evaluation

Ran 14 test questions comparing Week 2 (dense-only, BGE, top-5) vs Week 3 (hybrid + rerank, top-10).

**Results:**

| Metric | Week 2 | Week 3 | Change |
|---|---|---|---|
| Avg signal % | 44.3% | 44.3% | 0 |
| Avg usefulness | 3.64/5 | 4.29/5 | +0.65 |
| Win rate | 7/14 (50%) | 6/14 (43%) | — |
| Ties | 1/14 | — | — |

**What improved (Week 3 wins):**
- **Thematic/analytical queries** (q11, q14): Week 3 wins decisively. Hybrid search with BM25 surfaces diverse results that dense-only misses. Indian street food query: 40%→100% signal, 3→5 usefulness.
- **Strategy queries** (q08 no-cook sandwiches): BM25 matches keyword "no-cook" in chunk text; Week 3 wins 3→5.
- **Creator queries** (q09): BM25 matched creator name as a keyword — the known Week 2 failure is partially resolved by sparse vectors.
- **Ingredient diversity** (q07): Both score 5/5, but Week 3 returns more diverse sweet potato recipes.

**What did NOT improve (Week 2 wins):**
- **Sub-recipe factoid queries** (q01-q06, q10, q13): Week 2 wins 6/7. The sub-recipe splitting from Week 2 already places the correct chunk at rank 1 with very high similarity. Reranking with top-10 window reduces signal% (1 relevant out of 10 vs 1 relevant out of 5) even when usefulness is identical. The judge penalizes signal% which skews win counts.
- Note: all sub-recipe queries return the correct recipe at rank 1 in both systems — the Week 2 win is a signal% artifact, not a true quality regression.

**Key insight:** Hybrid + rerank improves *broad* and *thematic* queries significantly. For *targeted* sub-recipe factoid queries, Week 2's focused chunks already achieve ceiling performance and the larger reranked pool doesn't add value.

---

### What I Would Try in Iteration 8 (If Time Permitted)

1. **Adjust judge scoring:** Signal% is unfair to Week 3 when top-k=10 — a relevant chunk at rank 1 of 10 scores lower than rank 1 of 5. Use precision@1 or NDCG instead.
2. **Tune retrieve count:** Try top-30 → rerank-5 to balance recall vs signal% dilution for factoid queries.
3. **Creator name injection:** Embed creator name as a BM25-indexed keyword field, separate from chunk text, to improve creator query precision.
4. **Chat entry grouping:** 135 chat entries are under 50 tokens (too short). Group related tips into ~200-token chunks for better embedding quality.

---

*Data source: Thankful2Plants.com by Gurmeet Manku (CC BY-NC-ND 4.0)*

## Week 4 — Formal Evaluation

### March 30, 2026

**Focus:** Formalizing the SCOPE/GROUND/MEASURE evaluation framework.

**What we tried:**
*   Built a golden dataset of 15 curated questions across 6 types (`evaluations/golden_dataset.json`).
*   Created a deterministic semantic metrics script to measure hit@1, cosine relevance, and ROUGE-1 F1.
*   Created a Decomposed LLM Judge to independently score Faithfulness, Answer Relevance, and Context Precision (1-5).
*   Triangulated the results finding cases where the methods agreed vs disagreed.

**What we learned:**
*   **The system is perfectly faithful:** The LLM judge gave a 5/5 for Faithfulness across all queries, meaning grounded generation is working correctly.
*   **Retrieval is highly accurate, but contexts are truncated:** The Deterministic hit@1 metric showed 100% accuracy in finding the correct recipe card name. However, the LLM Judge scored Answer Relevance at 1/5 for several sub-recipe queries (like Zucchini Chutney). Triangulation revealed that while we found the right sub-recipe chunk, the text was missing the cooking instructions (it only had the ingredients).

**Next Step:**
*   Fix the data extraction and chunking pipeline (likely Week 5/production prep) to ensure sub-recipe ingredient lists are bundled with their respective method/instruction steps.
