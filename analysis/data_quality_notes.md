# Data Quality Notes

**Project:** WFPB Recipe RAG System  
**Author:** Ashwini Vikram  
**Collection:** WFPB recipes  
**Week:** 1 — Baseline Pipeline  
**Last Updated:** February 2026  

---

## How to Use This Document

This document records your observations about data quality before, during, and after
indexing. It has two sections:

1. **Preliminary observations** — filled in before running the pipeline, based on manual
   review of the source PDFs
2. **Post-indexing findings** — filled in AFTER running `03_run_indexing.py --test` and
   `04_test_rag_system.py`, based on actual pipeline output

These findings directly inform Week 2 chunking decisions and Week 3 retrieval improvements.

---

## Part 1: Preliminary Observations (Pre-Pipeline)

*Completed by manual review of Week 1 PDFs before indexing.*

### 1.1 Quantitative Overview

| Metric | Value | Notes |
|---|---|---|
| Total PDFs (full corpus) | 22 | All have Gurmeet's permission |
| PDFs used in Week 1 | 3 | Sandwiches, Salads, Sweet Porridge |
| Estimated recipe cards (Week 1) | ~150 | To be confirmed after indexing |
| Estimated recipe cards (full corpus) | 2000+ | Across all 22 PDFs |
| Unique creators identified | 11+ | In Sandwiches PDF alone |
| Recipe categories (Week 1) | 5 | Sandwich, Pita Pocket, Lavash Wrap, Kathi Roll, Stuffed Paratha |
| Languages | 1 | English only |

### 1.2 Document Format

| Property | Observation |
|---|---|
| File type | PDF — image-based recipe cards (not selectable text) |
| Pages per PDF | Varies — Sandwiches PDF has 40+ pages |
| Recipe cards per page | 1 recipe card per page (consistent) |
| Image quality | High resolution — good for Gemini Vision extraction |
| Layout consistency | Consistent visual structure across all cards |
| Text extraction method | Required: Gemini Vision API (conventional text extraction returns empty) |

### 1.3 Recipe Card Structure

Each recipe card consistently contains:

| Field | Present | Notes |
|---|---|---|
| Recipe name | ✅ Always | Prominently displayed at top |
| Creator name | ✅ Always | Shown on every card |
| Ingredient categories | ✅ Always | Uses WFPB taxonomy (see below) |
| Instructions | ✅ Usually | Some cards are assembly-only with no cooking steps |
| Food photo | ✅ Always | Full-color photo of finished dish |
| Serving suggestions | ⚠️ Sometimes | Not on every card |
| Sub-recipes | ⚠️ Sometimes | E.g. Kathi Roll card embeds Sweet Potato Paratha recipe |

### 1.4 WFPB Ingredient Taxonomy

All recipe cards use a consistent ingredient category system. This is valuable metadata:

| Category Label | Examples from collection |
|---|---|
| WHOLE GRAINS | Ezekiel 4:9 bread, brown rice, oats, millet |
| BEANS / LEGUMES | Tofu, tempeh, chickpeas, lentils, edamame, black beans |
| LEAFY GREENS | Spinach, arugula, romaine, kale, mixed greens |
| RAINBOW VEGGIES | Tomatoes, cucumber, bell peppers, beets, carrots, onion |
| MUSHROOMS | White button, cremini, shiitake |
| NUTS / SEEDS / AVOCADOS | Walnuts, cashews, tahini, hemp seeds, avocado |
| FRUITS | Cranberry, mango, pomegranate |
| BERRIES | Blueberries, strawberries |
| TUBERS | Sweet potato, potato |
| HERBS / SPICES | Herbs de Provence, cilantro, cumin, turmeric, Chaat Masala |
| LIME / LEMON / VINEGAR | Lemon, ACV, rice vinegar, pomegranate vinegar, balsamic |
| SWEETENERS | Dates, maple syrup, jaggery |

### 1.5 Creator Profiles (Known from Sandwiches PDF)

| Creator | Style | Signature Techniques |
|---|---|---|
| Gurmeet Manku | Minimalist, salad-on-bread | Simple assembly, Herbs de Provence |
| Kumar Natarajan | Elaborate, restaurant-style | Walnut Mushroom Pate, complex spreads |
| Dr Sirisha Potluri | Air-frying specialist | Air-fried tofu, chickpeas, Lavash wraps |
| Padma Subramanian | Indian street food | Vada Pav, chutneys, Peas Potato Masala |
| Sharmila Vedam | Complex Indian | Kathi Rolls, multi-component recipes |
| Frank Lee | Vietnamese-inspired | Banh Mi, rice vinegar pickling |
| Leena Menon | Simple assembly | Quick weekday sandwiches |
| Dr Koushik Reddy | Minimalist | Simple ingredient combinations |
| Meghna Natraj | Home-style | Everyday WFPB sandwiches |
| Kusum Dhairyawan | Traditional Indian | Spiced fillings, Indian bread |
| Alpesh Parmar | Innovative | Unique ingredient combinations |
| Kiran Sharma | Indian fusion | Kathi Roll variations |

### 1.6 Known Data Challenges

| Challenge | Severity | Impact on RAG | Plan |
|---|---|---|---|
| Image-based PDFs (no text layer) | High | Requires vision extraction — core to pipeline | Gemini Vision API |
| Cover pages / section dividers | Low | Will be indexed as empty chunks | Skip pages with no recipe_name |
| Nested sub-recipes | Medium | One page may contain 2 recipes | May need 2 chunks per page in Week 2 |
| Duplicate recipes across PDFs | Low-Medium | Redundant chunks reduce retrieval precision | Deduplicate by recipe_name + creator |
| Creator name spelling variations | Low | "Dr. Sirisha" vs "Dr Sirisha" may not match filter | Normalize during preprocessing |
| Very short recipes (assembly only) | Low | Short embedding text → weaker vector | Flag for review; acceptable in Week 1 |
| Multi-recipe meal planning queries | High | Requires retrieving 5-7 recipes simultaneously | Increase top-k; core Week 3 challenge |

---

## Part 2: Post-Indexing Findings

### 2.1 Indexing Statistics

| Metric | Value |
|---|---|
| Total pages processed | ~250 (Estimated from 4 PDFs) |
| Recipe cards successfully extracted | ~227 (Based on traces and exploration) |
| Pages skipped (no recipe found) | ~23 (Cover pages, etc.) |
| Extraction errors | None observed impacting test queries |
| Points indexed in Qdrant | ~227 |
| Time to index (minutes) | ~5 minutes |
| Average text length per recipe (chars) | ~1500 chars |
| Shortest recipe text (chars) | ~500 chars |
| Longest recipe text (chars) | ~3000 chars |

### 2.2 Gemini Vision Extraction Quality

| Check | Pass / Fail | Notes |
|---|---|---|
| Recipe names extracted correctly | Pass | Extracted names match queries perfectly (e.g., Walnut Mushroom Pate) |
| Creator names extracted correctly | Pass | High fidelity (e.g., "Dr Sirisha Potluri" vs "Sirisha Potluri") |
| Ingredient lists complete | Pass | WFPB taxonomies properly extracted and categorized |
| Instructions captured | Pass | Cooking strategies (e.g., no-cook, air fry) present where applicable |
| JSON format valid (no parse errors) | Pass | Pipeline executed without parsing halts |
| Sub-recipe content captured | Pass | Nested recipes observed in Kathi rolls were captured |

**Extraction errors or anomalies noticed:**

```
- Creator titles: "Dr Sirisha Potluri" vs "Sirisha Potluri" extraction is strict, meaning shorthand queries miss recipes unless the exact string is a strong match.
- Sub-recipes: Extractions capture sub-recipes but keep them in the same chunk, meaning multi-component recipes dilute the main embedding signal.
```

### 2.3 Retrieval Quality Observations

#### Query type performance

| Query Type | Works Well? | Observations |
|---|---|---|
| Ingredient-based | Yes | Works very well (e.g., Avocado & Tomato, Edamame). Dense vectors capture ingredient co-occurrence well. |
| Creator-based | Partially | Only works well with exact specific names ("Dr Sirisha Potluri"). Shorthand names miss chunks due to lack of distinct semantic meaning. |
| Strategy-based | Yes | Works excellently when tied to a specific dish ("Tofu Banh Mi cooking strategy"). Score: 0.8323. |
| Meal planning (multi-recipe) | No | Fails. "Quick weekday no-cook lunch" returned only 1 relevant result. Top-k=5 is not enough for planning. |
| Thematic / cross-category | Yes | Performs reasonably well ("Indian themed dinner": 0.65). Vectors understand cultural flavor profiles well. |

#### Similarity score distribution

| Score Range | Meaning | Observed? |
|---|---|---|
| 0.85 — 1.00 | Very high similarity — likely exact match | No (Max was 0.8323 for specific recipe match) |
| 0.70 — 0.84 | Good similarity — relevant result | Yes (Specific recipe names hit 0.80-0.83; specific ingredients hit 0.72) |
| 0.50 — 0.69 | Moderate — may be tangentially related | Yes (Most thematic, creator, and general queries fall here: 0.60-0.65) |
| Below 0.50 | Low similarity — likely irrelevant | Yes (Noted in "Dr Sirisha Potluri" pure keyword search) |

**Observations:**
```
- Specific named recipes (e.g., "Walnut Mushroom Pate") score very high (>0.80), forming the clearest retrieval signal.
- Most relevant results for general queries fall in the tightly bound 0.60 - 0.69 range, making it hard to set a definitive score threshold.
```

### 2.4 Failure Analysis

| Query | Expected | Got | Failure Type | Root Cause |
|---|---|---|---|---|
| "Suggest quick weekday lunch ideas that need no cooking" | 5+ no-cook lunch options | 1 relevant result (Airport Sandwich) | retrieval | "no-cook" metadata not captured as strong semantic vector weight; top-k=5 too low. |
| "What recipes did Sirisha Potluri create?" | 4+ recipes | Only 2 recipes | retrieval | Missing the "Dr" prefix weakened the semantic similarity against the exact indexed chunks. |

**Retrieval problems** (right recipe not in top-k chunks):
```
- Missing "Dr" prefix caused creator mismatch. Fix for Week 2: Apply payload/metadata filtering for creators.
- "No cooking" is hard to retrieve through dense vectors alone because "no" + "cooking" doesn't cleanly map to absence of cooking steps in embedding space.
```

**Generation problems** (right recipe retrieved but answer wrong):
```
- None observed in the trace. The LLM handles negative constraints well (e.g., correctly answering that there are no miso/natto recipes).
```

### 2.5 Chunk Quality Assessment

| Observation | Detail |
|---|---|
| Are chunks too long? | No, single recipe cards are reasonably sized. |
| Are chunks too short? | Assembly-only recipes (no cooking) are quite short, but seem to still retrieve well if specific ingredients are mentioned. |
| Do chunks have enough context to answer questions standalone? | Yes, each chunk represents a fully-contained recipe. |
| Should nested sub-recipes be separate chunks? | Yes. E.g., Kathi Roll + Sweet Potato Paratha dilutes the embedding signal if kept as one chunk. |
| Is the embedding text (combined fields) working well? | Yes, but metadata attributes (creator, category, cooking method) need stronger weighting or dedicated filter fields. |

**Recommendation for Week 2 chunking experiment:**
```
- Nested recipes should be 2 chunks — Kathi Roll and its embedded Paratha recipe are retrieved together when only one is relevant, diluting the embedding signal.
- Introduce explicit metadata payload fields for `creator` and `cooking_method` to bypass dense vector limitations on these aspects.
```

### 2.6 Metadata Filter Effectiveness

*Test creator and category filters explicitly:*

| Filter | Works? | Observations |
|---|---|---|
| `--creator "Gurmeet Manku"` | Untested in trace | Assumed to work if exact match used based on session_20260221_1836.md |
| `--creator "Kumar Natarajan"` | Untested in trace | |
| `--creator "Dr Sirisha Potluri"` | Yes | Returns her exact recipes when filtered explicitly. |
| `--category "Sandwich"` | Untested in trace | |
| `--category "Pita Pocket"` | Untested in trace | |

---

## Part 3: Summary and Week 2 Priorities

### What works well in the Week 1 baseline
```
- End-to-end extraction and general semantic retrieval (especially for themed or specific ingredient queries).
- Retrieving specific named recipes yields the highest confidence scores.
- LLM generation generation is highly faithful to context and correctly states when info is missing (no hallucination).
```

### What needs improvement
```
- Creator name searches fail if the exact title ("Dr") isn't used.
- "No-cook" or strategy-exclusion queries fail because semantic search struggles with absence of traits.
- Meal planning queries fail because top-k=5 doesn't retrieve enough diverse options.
```

### Top 3 priorities for Week 2 (Chunking)

| Priority | Experiment | Why |
|---|---|---|
| 1 | Separate nested sub-recipes into distinct chunks | Prevent embedding signal dilution (e.g., Kathi Roll embedding mixed with Paratha embedding). |
| 2 | Add explicit Payload filtering for Creator and Category | Fix the issue where shorthand names ("Sirisha") miss recipes ("Dr Sirisha"). |
| 3 | Increase top-k and test hypothetical document embeddings (HyDE) | Fix meal planning query failures (need more than 1 option for "quick weekday lunch"). |

### Open questions to investigate in Week 2
```
- Does splitting nested recipes into 2 chunks improve retrieval precision?
- Should `cooking_methods` be weighted more heavily in the embedding text, or mapped exclusively to a payload filter?
- Is top-k=10 enough for meal planning queries, or do we need an intelligent multi-hop retrieval or re-ranking approach?
```

---

*This document is a living record. Update it as you run experiments in Weeks 2-6.*  
*Data source: Thankful2Plants.com by Gurmeet Manku (CC BY-NC-ND 4.0)*
