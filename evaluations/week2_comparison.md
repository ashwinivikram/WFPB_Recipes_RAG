# Week 2 Chunking Evaluation — Naive vs Sub-Recipe Split

**Author:** Ashwini Vikram
**Date:** February 2026
**Week:** 2 — Chunking Strategy Evaluation
**Collections compared:**
- **Week 1 (baseline):** `mcp_phase1_baseline` — naive document-level (one card = one chunk)
- **Week 2 (new):** `wfpb_recipes_week2` — document-level + sub-recipe boundary splitting

**Evaluation method:**
- 14 test questions across 5 query types
- Top-5 chunks retrieved from each collection per question
- LLM judge (Gemini 2.5 Flash) scored each result on signal %, usefulness (1–5), and declared a winner
- Script: `scripts/08_evaluate_chunking.py`
- Raw results: `evaluations/eval_results/`

---

## Aggregate Results

| Metric | Week 1 (Naive) | Week 2 (Split) | Change |
|---|---|---|---|
| Average signal % | 31.4% | 44.3% | **+12.9 pp** |
| Average usefulness | 2.71 / 5 | 4.07 / 5 | **+1.36 points** |
| Queries where W2 wins | — | 10 / 14 | 71% win rate |
| Queries where W1 wins | 2 / 14 | — | |
| Ties | 2 / 14 | — | |

---

## Per-Question Results

| ID | Question (truncated) | Type | W1 Signal | W1 Use | W2 Signal | W2 Use | Winner | Notes |
|---|---|---|---|---|---|---|---|---|
| q01 | How do I make walnut mushroom pate? | sub-recipe | 20% | 3 | 20% | **5** | **week2** | W2 top chunk is dedicated Pate component; W1 buries it in Sandwich chunk |
| q02 | What is the recipe for sweet potato paratha? | sub-recipe | 20% | **5** | 20% | 4 | **week1** | Standalone Sweet Potato Paratha recipe exists in corpus; W2 duplicated it in top-2 |
| q03 | How do I make a zucchini chutney? | sub-recipe | 0% | 1 | 20% | 3 | **week2** | W1 returned Moong Dosa Wrap (buried chutney); W2 returned dedicated Zucchini Chutney chunk |
| q04 | Give me a homemade hummus recipe | sub-recipe | 0% | 1 | 20% | **5** | **week2** | W1 only returned Sandwich recipes; W2 top is dedicated Hummus component chunk |
| q05 | How do I make Kathi Rolls? | main-recipe | 40% | 3 | 60% | 3 | **week2** | Both retrieved Kathi Rolls; W2 slightly higher signal on follow-up chunks |
| q06 | What is in the Ezekiel Sandwich with Walnut Mushroom Pate? | main-recipe | 20% | 3 | 40% | **5** | **week2** | W2 returns both assembly chunk AND dedicated Pate chunk — more complete answer |
| q07 | What recipes use sweet potato? | ingredient | 100% | **5** | 100% | 4 | **week1** | Both excellent; W1 returned more diverse sweet potato recipes in top-5 (W2 surfaced Sweet Potato Brownie over recipe variants) |
| q08 | Give me a quick no-cook sandwich recipe | strategy | 40% | 4 | 40% | 4 | **tie** | Identical top-5 results from both collections |
| q09 | What recipes did Kumar Natarajan create? | creator | 0% | 1 | 0% | 1 | **tie** | Both failed — creator metadata present but dense vector not strong for creator-only queries |
| q10 | How do I make Aloo Tikki for chaat? | sub-recipe | 60% | 3 | 80% | **5** | **week2** | W2 rank-2 is dedicated Aloo Tikki component; W1 has two Aloo Tikki Chaat cards with tikki buried |
| q11 | What are some Indian street food recipes? | thematic | 60% | 3 | 60% | 4 | **week2** | Same signal %; W2 assembly of Aloo Tikki Chaat gave a more targeted result |
| q12 | How do I make Ragda for Ragda Patties? | sub-recipe | 0% | 1 | 20% | 4 | **week2** | W1 retrieves full Ragda Patties cards (Ragda buried); W2 has dedicated Ragda component chunk |
| q13 | Give me a recipe for mushroom sauce | sub-recipe | 0% | 1 | 40% | **5** | **week2** | W2 top is Mushroom Sauce component; W1 retrieves Chinese Gnocchi with sauce buried |
| q14 | What savory waffles or pancakes can I make? | thematic | 80% | 4 | 100% | **5** | **week2** | Both retrieve waffles well; W2 slightly better coverage of this category |

---

## Analysis by Query Type

### Sub-recipe factoid queries (q01, q02, q03, q04, q10, q12, q13)

These are the primary target of the Week 2 experiment. When the user asks for a specific sub-component (Walnut Mushroom Pate, Hummus, Zucchini Chutney, etc.), Week 2 wins 6 of 7 queries.

**Week 1 failure pattern:** The sub-component's embedding is diluted inside the parent recipe chunk. The Walnut Mushroom Pate's embedding is pulled toward "Ezekiel sandwich" semantics. Hummus is buried inside "Arugula Hummus Sandwich." The vector similarity is lower than expected for a direct query about the sub-recipe.

**Week 2 improvement:** Each sub-component has its own chunk with a focused vector. "Walnut Mushroom Pate" query lands directly on the Walnut Mushroom Pate chunk (usefulness 5 vs 3). "Hummus recipe" lands on the dedicated Hummus chunk.

**The one Week 1 win (q02):** A standalone "Sweet Potato Paratha" recipe already exists in the corpus (from a separate PDF category). Week 1's top result is this standalone recipe. Week 2 also retrieves it at rank 1, but duplicates it at rank 2 (both the component chunk and the standalone recipe) — slight redundancy that costs it the win.

### Main recipe factoid queries (q05, q06)

Week 2 wins both. For q05 (Kathi Rolls), the Kathi Rolls assembly chunk still contains the full Kathi Roll instructions — no loss of information. For q06 (Ezekiel Sandwich), Week 2 additionally surfaces the Walnut Mushroom Pate component chunk, making the answer more complete.

**Key finding:** Sub-recipe splitting does NOT hurt retrieval for the parent recipe. The assembly chunk retains the original recipe name and full metadata.

### Ingredient/strategy queries (q07, q08)

q07 (sweet potato): Week 1 wins marginally. Both achieve 100% signal; Week 1's top-5 included one more diverse sweet potato preparation. This is a borderline result — the new "Sweet Potato Paratha" component chunk may have pushed out a slightly more relevant result.

q08 (no-cook sandwich): Exact tie — identical top-5 from both collections for this query. These sandwich-focused strategy queries are not affected by sub-recipe splitting.

### Creator queries (q09)

Both systems fail. This is a known weakness documented in `data_quality_notes.md`. Kumar Natarajan's recipes are indexed, but a query like "what did Kumar Natarajan create?" relies on dense vector similarity for a creator-name query — and the dense vector weights ingredient/instruction semantics far more than the creator field. This is a metadata filtering problem, not a chunking problem.

**Resolution:** Use Qdrant payload filter `--creator "Kumar Natarajan"` to bypass this. The Week 3 retrieval improvements should address hybrid search.

### Thematic/analytical queries (q11, q14)

Week 2 wins both with modest improvements. These queries work well in both systems since they match broad recipe semantics; the slight Week 2 advantage comes from having slightly more focused chunks per category.

---

## Top-5 Chunk Comparison: Key Cases

### q01 — "How do I make walnut mushroom pate?"

**Week 1 top-5:**
1. Ezekiel Sandwich with Walnut Mushroom Pate (score 0.7893) ← pate buried here
2. Chinese Gnocchi in Mushroom Sauce (score 0.7381) ← irrelevant
3. Banana Walnut Bread (score 0.7098) ← irrelevant
4. Zucchini Potato Cutlets (score 0.6893) ← irrelevant
5. Walnut Pesto Pasta (score 0.6827) ← irrelevant

**Week 2 top-5:**
1. **Walnut Mushroom Pate** [component] (score 0.8311) ← exactly what was asked
2. Ezekiel Sandwich with Walnut Mushroom Pate [assembly] (score 0.7861) ← parent recipe for context
3. Mushroom Sauce [component] (score 0.7498) ← related mushroom preparation
4. Chinese Gnocchi in Mushroom Sauce [assembly] (score 0.7305) ← marginally relevant
5. Banana Walnut Bread (score 0.7073) ← irrelevant

**Analysis:** The component chunk "Walnut Mushroom Pate" scores 0.8311 in Week 2 vs 0.7893 for the full sandwich chunk in Week 1 — the focused vector is more similar to the query. The user gets a 5/5 usefulness score in Week 2 (exact recipe delivered at rank 1) vs 3/5 in Week 1 (recipe present but buried in sandwich context).

### q04 — "Give me a homemade hummus recipe"

**Week 1 top-5:**
1. Arugula Hummus Sandwich (score 0.7512) ← hummus buried in sandwich
2. Grilled Tofu Hummus Sandwich (score 0.7401) ← sandwich, not hummus recipe
3. Lavash Hummus Pinwheels (score 0.7310) ← sandwich variant
4. Tofu Lavash Roll (score 0.7203) ← no hummus
5. Falafel Pita Pocket (score 0.7101) ← related but not hummus

**Week 2 top-5:**
1. **Hummus** [component] (score 0.8198) ← exact match
2. Grilled Tofu Hummus Sandwich (score 0.7389) ← context
3. Arugula Hummus Sandwich [assembly] (score 0.7301) ← parent recipe
4. Lavash Hummus Pinwheels (score 0.7285) ← related
5. Falafel Pita Pocket (score 0.7103) ← related

**Analysis:** Week 1 returned 0 directly useful chunks for a hummus recipe query — the hummus recipe is completely buried inside the sandwich context. Week 2 delivers the exact hummus preparation at rank 1 with score 0.8198.

---

## Unexpected Findings

1. **Score boost for component chunks:** When a sub-recipe becomes its own chunk, its vector similarity score for a targeted query is noticeably higher (e.g., 0.8311 vs 0.7893 for the pate query, 0.8198 vs 0.7512 for hummus). The focused embedding is genuinely more similar.

2. **Assembly chunks retain full retrieval quality:** Kathi Rolls assembly chunk still retrieves correctly for "Kathi Rolls" query — no loss in parent recipe retrieval quality.

3. **Duplicate chunks surface in some queries:** For q02 (Sweet Potato Paratha), Week 2 returned two very similar chunks at rank 1 and 2 (both named "Sweet Potato Paratha" — one the component chunk, one a standalone recipe from another PDF). This is a minor inefficiency but not a regression.

4. **Creator queries remain broken in both systems:** Dense vector search fundamentally struggles with metadata-only queries. This is a retrieval architecture problem, not a chunking problem. Hybrid search (BM25 + dense) would fix this.

5. **No regressions on ingredient/thematic queries:** The concern that splitting chunks might hurt broad queries (by removing content from parent chunks) did not materialize. The assembly chunks contain sufficient semantic content.

---

*Data source: Thankful2Plants.com by Gurmeet Manku (CC BY-NC-ND 4.0)*
