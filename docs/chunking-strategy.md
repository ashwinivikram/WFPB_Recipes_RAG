# Chunking Strategy — WFPB Recipe RAG System

**Author:** Ashwini Vikram
**Week:** 2 — Chunking Strategy
**Date:** February 2026
**Feeds from:** `docs/chunking-analysis.md`

---

## Step 2: SELECT — Strategy Choice

### Applying the Decision Flowchart

```
START: What dominates your corpus?
|
+--> CODE (or mixed code + docs)        → AST Code Chunking       ✗ No code
+--> STRUCTURED DOCUMENTATION           → Recursive Chunking      ✗ No markdown headers
+--> MULTI-TOPIC PROSE                  → Semantic Chunking       ✗ No topic shifts within docs
+--> UNIFORM TECHNICAL DOCS             → Recursive Chunking      ✗ Not technical docs
+--> SIMPLE PROSE / SHORT DOCS          → Naive Medium or Recursive
     └── SPECIAL CASE: docs already     → Document-level          ✓ Matches our corpus
         at natural atomic boundaries
```

### Strategy Selection Matrix

| If you checked... | Start with... | Why |
|---|---|---|
| Simple prose | Recursive or Naive Medium | Predictable, fast, good baseline |
| Short docs (< 500 words) | **Consider keeping as single chunk** | No splitting needed |
| Documents at natural boundaries | **Document-level** | Boundaries already exist |

**Our corpus:** 68% of PDF recipes are under 200 tokens. Median is 156 tokens.
The standard "how do I break large docs into smaller pieces?" problem does **not apply** here.
The problem is the inverse: **24 recipe cards embed two recipes in one chunk**.

### Selected Strategy: Document-Level with Sub-Recipe Boundary Detection

**What this is NOT:**
- Not recursive splitting (docs are already small)
- Not sentence splitting (fragments would lose ingredient + instruction context together)
- Not semantic chunking via embeddings (overkill; boundaries are visually and textually explicit)

**What this IS:**
A targeted rule-based split that detects when a recipe card embeds a second complete recipe (typically a sauce, chutney, bread, or component recipe), and separates them into two independent chunks — each with its own full metadata.

For all other recipe cards (95% of corpus), the Week 1 document-level strategy is kept unchanged, as it is already the correct approach for this content type.

---

## Rationale

### Why Not Recursive Chunking?

Recursive chunking would slice each recipe into overlapping ~400-word windows. For a 156-token median document, this produces:
- Chunks that split between ingredients and instructions
- Context about cooking method separated from ingredient list
- Partial recipes that can't answer "how do I make X?" on their own

A recipe card is the **minimum meaningful unit** for this domain. Splitting below recipe-card level hurts retrieval quality, not helps it.

### Why Not Semantic Chunking?

Semantic chunking detects topic transitions via embedding similarity drops. This is expensive (requires double-embedding) and unnecessary here. Recipe boundaries are explicit in the text:
- A sub-recipe always starts with a section header like `"For the Tzatziki Sauce:"`, `"Paratha Recipe:"`, `"Chutney:"`, or `"Sauce:"` followed by its own ingredient list
- These are textual signals detectable with lightweight pattern matching — no embedding needed

### Why Sub-Recipe Splitting Specifically?

From the Week 1 failure analysis (`data_quality_notes.md`):

> *"Sub-recipes: Extractions capture sub-recipes but keep them in the same chunk, meaning multi-component recipes dilute the main embedding signal."*

Concrete example: The chunk for **Kathi Rolls** currently embeds:
- The Kathi Roll recipe (rolling technique, filling, assembly)
- The Sweet Potato Paratha recipe (dough, rolling, cooking on tawa)

A query for "Sweet Potato Paratha recipe" retrieves this chunk — but the returned context is 50% about the Kathi Roll assembly. The LLM must work harder to isolate the relevant part. Splitting gives each component its own precise vector.

**24 recipes (10.1%)** are affected. Splitting them yields up to 48 cleaner chunks in place of 24 diluted ones.

---

## Step 3: CONFIGURE — Size and Overlap Settings

### Configuration Table

| Parameter | Value | Reasoning |
|---|---|---|
| Primary strategy | Document-level (one recipe = one chunk) | Natural atomic boundary; median 156 tokens |
| Sub-recipe split | Rule-based boundary detection | Explicit section headers in text |
| Target chunk size (sub-recipes) | Keep both halves as-is (no word limit imposed) | Sub-recipe halves are ~50–200 tokens each — well within BGE limit |
| Overlap | **0%** — no overlap | Recipes are atomic; overlap between ingredients and instructions adds noise, not signal |
| Embedding model | BAAI/bge-large-en-v1.5 (unchanged from Week 1) | Max 512 tokens; 99.7% of corpus already within safe limit |
| Cover-page filtering | Exclude chunks where `recipe_name == ""` | 4 empty chunks in current index; pure noise |
| Chat entry handling | Keep as document-level (no change) | 91% of chat entries are 50–400 tokens — acceptable range |

### Size Guidelines Check

| Content Type | Starting Size | Our Corpus | Action |
|---|---|---|---|
| FAQs / short docs | Document-level | ✓ Matches (recipes are short, self-contained) | Keep document-level |
| General text | 400–512 tokens, 10–15% overlap | Our docs average 156 tokens | Overlap not needed at this scale |

### Embedding Model Constraint Check

| Model | Max Tokens | Safe Max | Our Max Chunk | Status |
|---|---|---|---|---|
| BAAI/bge-large-en-v1.5 | 512 | 400 | 502 (1 PDF chunk) | ✅ No action |

The single PDF chunk that reaches 502 tokens (Quinoa Handvo – Mug Cake Style) stays within the hard limit. Post-split, sub-recipe halves will all be well under 300 tokens.

---

## Step 4: Implementation Plan

### New Qdrant Collection

| Collection | Purpose | Strategy |
|---|---|---|
| `mcp_phase1_baseline` (Week 1) | **Keep untouched** — evaluation baseline | Naive: one card = one chunk, sub-recipes included |
| `wfpb_recipes_week2` (Week 2) | New collection for evaluation | Document-level + sub-recipe split + empty chunk removal |

### Script: `scripts/06_chunk_with_strategy.py`

This script reads all processed JSONs and outputs a list of chunks applying the Week 2 strategy:
1. Skip chunks where `recipe_name == ""` (cover/TOC pages)
2. For recipes without sub-recipe content: emit as-is (same as Week 1)
3. For recipes with sub-recipe content: detect the boundary, split into two chunks, assign each full metadata with a `_main` / `_sub` suffix on the ID

### Script: `scripts/07_index_with_strategy.py`

Reads output of `06_chunk_with_strategy.py` and upserts to the `wfpb_recipes_week2` collection.

### Sub-Recipe Detection Logic

Section headers that mark the start of an embedded sub-recipe:
```python
SUB_RECIPE_MARKERS = [
    r'\bFor the\b',         # "For the Tzatziki Sauce:"
    r'\bParatha Recipe\b',  # "Paratha Recipe:"
    r'\bChutney[:\s]',      # "Chutney:" or "Chutney Recipe"
    r'\bSauce[:\s]',        # "Sauce:" or "Sauce Recipe"
    r'\bDip[:\s]',          # "Dip:"
    r'\bBatter[:\s]',       # "Batter:" (for pancakes with separate batter recipes)
]
```

**Handling:** Find the first marker line in the `Instructions` section. Everything from that line onward (plus the sub-recipe ingredients) becomes the second chunk, with a new `recipe_name` derived from the section header.

---

## Step 5: What We Expect to Improve

### Hypothesis

Splitting sub-recipe cards into two focused chunks will improve retrieval precision for:
1. Queries targeting a sub-component directly ("Tzatziki Sauce recipe", "Walnut Mushroom Pate")
2. Queries where the main recipe and sub-component are semantically distant (e.g., "Kathi Roll" vs "Sweet Potato Paratha")
3. Ingredient queries that happen to be exclusive to the sub-component

### Expected Outcome

| Query type | Week 1 (naive) | Week 2 (expected) |
|---|---|---|
| "How do I make Walnut Mushroom Pate?" | Good (specific recipe name) — but chunk also contains Ezekiel Sandwich context | Better — dedicated chunk for the Pate only |
| "Kathi Roll recipe" | Good — chunk contains full Kathi Roll | Same or better — dedicated chunk |
| "Sweet Potato Paratha" | Poor — buried inside Kathi Roll chunk | Better — dedicated chunk with full sub-recipe text |
| "Green chutney recipe" | Poor — multiple chutneys buried inside parent recipes | Better — each chutney as its own chunk |
| Ingredient queries in sub-recipes only | Partial — relevant ingredients in chunk but diluted | Better — vector is focused on that ingredient set only |

### What May Not Improve

- General ingredient queries (e.g., "tofu recipes") — these work well already in Week 1
- Creator-based filtering — still handled by payload filters, not chunking
- Meal planning queries — still a top-k problem, not a chunk quality problem
- Very short chat entries — out of scope for this experiment

---

## Summary

| Decision | Choice | Rationale |
|---|---|---|
| Base strategy | Document-level (unchanged) | Corpus is already at atomic natural boundaries |
| Improvement | Sub-recipe boundary detection + split | 24 multi-recipe cards dilute embedding signal |
| Chunk size | Kept as-is (no word limit) | 99.7% of corpus within BGE's safe limit |
| Overlap | 0% | Atomic units; overlap adds noise |
| Empty chunk filtering | Yes | Remove 4 cover-page empty chunks |
| Embedding model | BGE-large-en-v1.5 (unchanged) | No truncation issues; no reason to switch |
| Evaluation approach | Compare `mcp_phase1_baseline` vs `wfpb_recipes_week2` on 8–15 test queries | Per course framework: signal %, cut-off count, usefulness |

---

*Data source: Thankful2Plants.com by Gurmeet Manku (CC BY-NC-ND 4.0)*
