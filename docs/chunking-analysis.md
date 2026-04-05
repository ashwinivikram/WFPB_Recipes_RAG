# Chunking Analysis — WFPB Recipe RAG System

**Author:** Ashwini Vikram
**Week:** 2 — Chunking Strategy
**Date:** February 2026
**Corpus:** Thankful2Plants.com recipes + WFPB WhatsApp Group chats

---

## Step 1: ANALYZE — Content Type Assessment

### Content Type Checklist

| Question | Answer |
|---|---|
| What file types dominate? | PDF-extracted prose (structured recipe text as JSON) + plain WhatsApp chat text |
| Is content mixed or homogeneous? | Homogeneous — each document is a single recipe card with a consistent schema |
| How structured is it? | Highly structured: every recipe has Name → Creator → Category → Ingredients → Cooking Methods → Instructions |
| What's the average document length? | ~168 tokens (PDF recipes), ~93 tokens (chat entries) — both well under 500 words |
| Does content shift topics within documents? | No — each document is exactly one recipe or one cooking tip |

### Content Type Checklist (tick all that apply)

- [ ] Code files (.py, .js, .ts) — functions and classes need intact boundaries
- [ ] Structured markdown — headers, lists, code blocks with clear hierarchy
- [ ] Technical documentation — dense content, stays on-topic for extended sections
- [ ] Multi-topic articles — clear subject transitions within documents
- [x] **Simple prose** — paragraphs of text without complex structure
- [ ] Mixed content — combination of code and documentation

**Assessment:** Corpus is structured, domain-specific prose. Each document is self-contained and semantically singular (one recipe = one topic). Documents do not shift subjects internally. The corpus most closely matches "simple prose" with **structured field boundaries** (not markdown headers, but consistent schema labels).

---

## Step 2: Document Length Distribution

All token counts use the estimate: `words ÷ 0.75` (standard English prose approximation).
BGE-large-en-v1.5 safe max = **400 tokens**. Hard limit = **512 tokens**.

### PDF Recipe Chunks (4 categories indexed)

| Category | Count | Min tok | Max tok | Avg tok | Median tok |
|---|---|---|---|---|---|
| Sandwiches & Pita Pockets | 45 | 0 | 456 | 111 | 70 |
| Savory Pancakes & Waffles | 52 | 0 | 502 | 179 | 142 |
| Savory Snacks | 79 | 0 | 472 | 181 | 173 |
| Tikkis, Cutlets, Falafel, Dumplings | 61 | 0 | 428 | 183 | 184 |
| **TOTAL (PDF)** | **237** | **0** | **502** | **168** | **156** |

> Note: 4 chunks have 0 tokens — these are cover/TOC pages with no `recipe_name`. They are harmless noise in the index (Qdrant returns them but with near-zero scores).

#### Token Distribution — PDF Recipes

| Bucket | Count | % of corpus | BGE status |
|---|---|---|---|
| < 200 tokens | 162 | 68.4% | Well within limit |
| 200–400 tokens | 65 | 27.4% | Within safe limit |
| 400–512 tokens | 10 | 4.2% | Within hard limit |
| 512–800 tokens (truncated) | 0 | 0.0% | N/A |
| > 800 tokens (truncated) | 0 | 0.0% | N/A |

**Key finding:** No PDF recipe chunks are truncated by BGE-large-en-v1.5. The problem is the opposite direction — **most chunks are very short** (68% under 200 tokens). Short chunks embed well for specific factoid lookups but may lack enough context for analytical or meal-planning queries.

### WhatsApp Chat Entries

| Metric | Value |
|---|---|
| Total entries | 429 |
| Min tokens | 4 |
| Max tokens | 680 |
| Avg tokens | 93 |
| Median tokens | 69 |
| Over 400 tokens (soft limit) | 4 (0.9%) |
| Over 512 tokens (hard limit / **truncated**) | 2 (0.5%) |

#### Token Distribution — Chat Entries

| Bucket | Count | % | BGE status |
|---|---|---|---|
| < 50 tokens | 135 | 31.5% | Dangerously short — poor embedding signal |
| 50–200 tokens | 256 | 59.7% | Good range |
| 200–400 tokens | 34 | 7.9% | Within safe limit |
| 400–512 tokens | 2 | 0.5% | At limit |
| > 512 tokens (truncated) | 2 | 0.5% | **Silently truncated** |

**Key finding:** 31.5% of chat entries are under 50 tokens — single-sentence tips like *"Sweet potato is prepared by air-frying and adding basic spices."* These embed poorly and will have low retrieval precision since there's barely any semantic signal.

#### Chat Entry Categories

| Category | Count |
|---|---|
| Recipe | 250 |
| Tip | 123 |
| Discussion | 51 |
| Other (Technique, Resource) | 5 |

### Combined Corpus

| Source | Chunks | Avg tokens | Truncation risk |
|---|---|---|---|
| PDF recipes | 237 | 168 | None |
| WhatsApp chats | 429 | 93 | 2 entries (0.5%) |
| **Total** | **666** | **122** | Negligible |

---

## Step 3: Structural Observations

### 3.1 Consistent Schema (Strength)
Every PDF recipe chunk follows the same field order:
```
Recipe: <name>
Creator: <name>
Category: <category>
Ingredients: <list>
Cooking methods: <list>
Instructions: <steps>
```
This means **field-level semantic structure is already present** within each chunk. A query about "creator" lands in the right text segment — but the embedding treats all fields with equal weight.

### 3.2 Sub-Recipe Dilution (Key Problem)
**24 of 237 PDF recipes (10.1%)** contain embedded sub-recipes — a recipe card that describes the main dish AND includes a full secondary recipe (sauce, chutney, bread, etc.) within the same chunk.

| Examples | Sub-component |
|---|---|
| Kathi Rolls | Sweet Potato Paratha embedded within |
| Ezekiel Sandwich with Walnut Mushroom Pate | Walnut Mushroom Pate sub-recipe |
| Pita Pockets w/ Tzatziki Sauce | Tzatziki Sauce full sub-recipe |
| Quinoa Chana Dhokla | Chutney sub-recipe |
| Moong Dosa Wrap | Chutney + Wrap recipe |
| Tofu Pakoda | Chutney sub-recipe (354 words — among the longest) |

**Impact:** When a query targets the sub-component (e.g., "Tzatziki Sauce recipe"), the chunk retrieved also contains the full main recipe. The embedding of both together dilutes specificity. The single chunk vector is pulled in two semantic directions simultaneously.

### 3.3 Very Short Chat Entries (Noise Risk)
135 chat entries are under 50 tokens. These are single-sentence tips that contain almost no context:
- *"Sweet potato is prepared by air-frying and adding basic spices."* (12 tokens)
- *"Air-frying technique: food can be air-fried without any oil."* (14 tokens)

A query embedding has to "match" these with very little surface area. They may pollute top-k results with low-information chunks.

### 3.4 Empty Chunks (Known Noise)
4 chunks have empty `text` and empty `recipe_name`. These are cover/title pages (e.g., the introductory page of each PDF). They won't be retrieved for meaningful queries (near-zero cosine similarity) but waste index space.

### 3.5 Corpus IS Homogeneous — Rechunking Is Not the Problem
The recipe corpus does not need the standard "break large documents into smaller chunks" treatment. All documents are already at or below 500 tokens — the opposite of the MCP documentation corpus (500–3000 word pages). The chunking opportunity here is:
1. **Splitting** the few multi-recipe cards into separate chunks
2. **Enriching** short chat entries with more context (or filtering them out)
3. **Not touching** the majority of well-sized recipe cards

---

## Step 4: Key Findings Summary

| Finding | Impact | Week 2 Action |
|---|---|---|
| 68% of PDF chunks are < 200 tokens | Short chunks are OK for factoid queries but weak for analytical ones | Accept as-is (documents are naturally short); document in evaluation |
| 0% of PDF chunks exceed BGE's 512-token hard limit | No silent truncation happening in Week 1 | No action needed |
| 24 recipes (10.1%) contain embedded sub-recipes | Embedding diluted; sub-component queries retrieve irrelevant main recipe context | **Split sub-recipe chunks** — primary Week 2 experiment |
| 2 chat entries exceed 512 tokens and are silently truncated | Partial embeddings for 2 entries | Reduce those 2 entries or switch to Voyage embedder for chats |
| 135 chat entries < 50 tokens | Poor embedding signal; may add retrieval noise | Flag for evaluation; consider grouping related tips into topic clusters |
| 4 empty/cover-page chunks in index | Minor noise | Filter during re-indexing in Week 2 |
| 52 unique creators across PDF corpus | Rich metadata; creator-based filtering is high-value | Ensure payload indexes exist for `creator` field |

---

## Step 5: Embedding Model Constraints

**Current model:** BAAI/bge-large-en-v1.5 (via FastEmbed)

| Constraint | Value | Implication |
|---|---|---|
| Max tokens | 512 | Any chunk over 512 tokens is silently truncated |
| Safe max chunk | 400 tokens | Provides buffer; target for new chunks |
| Current corpus compliance | ✅ 99.7% within hard limit | No architecture change needed for embedder |
| Very short chunk risk | ⚠️ 31.5% of chats < 50 tokens | Short entries have poor embedding signal |

**Decision:** Keep BGE-large-en-v1.5 for Week 2. The corpus does not stress the 512-token limit.
No reason to switch to Voyage-4-lite at this stage.

---

## Summary: What This Analysis Tells Us About Strategy

The corpus does **not** need the standard "chunking" treatment (breaking large docs into smaller pieces). The documents are already small. What it does need is:

1. **Sub-recipe boundary detection:** 24 recipe cards should become 48 chunks — one per recipe component. This is the highest-impact, most testable chunking improvement.
2. **Cover-page filtering:** 4 empty chunks should be excluded from the index.
3. **Chat entry quality review:** 135 very short entries may need to be merged with related tips into richer chunks, or evaluated to see if they help or hurt retrieval.

This analysis feeds directly into `docs/chunking-strategy.md`.

---

*Data source: Thankful2Plants.com by Gurmeet Manku (CC BY-NC-ND 4.0)*
*Chat data: WFPB WhatsApp Group (PII sanitized — phone numbers replaced with "WFPB member")*
