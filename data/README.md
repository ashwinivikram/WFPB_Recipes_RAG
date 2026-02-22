# Data Documentation

**Project:** WFPB Recipe RAG System  
**Author:** Ashwini Vikram  
**Last Updated:** February 2026  

---

## Data Source

| Field | Detail |
|---|---|
| Source | Thankful2Plants.com — personal WFPB recipe blog |
| Owner | Gurmeet Manku (computer scientist, WFPB practitioner since 2012) |
| Permission | Explicit permission granted by owner |
| License | CC BY-NC-ND 4.0 — non-commercial use with attribution required |
| Attribution | All outputs must credit Thankful2Plants.com |
| Contact | gurmeet@gmail.com |

---

## Data Volume

| Scope | PDFs | Estimated Recipe Cards |
|---|---|---|
| Full corpus | 22 | 2000+ |
| Week 1 baseline | 3 | ~150 |

---

## Week 1 PDFs (data/raw/)

The following 3 PDFs are used for the Week 1 baseline pipeline. They were selected
to represent a diverse cross-section of recipe types, creators, and complexity levels.

| File | Category | Why Selected |
|---|---|---|
| `Sandwiches___Pita_Pockets___Whole_Food_Plant-Based.pdf` | Sandwiches, Pita Pockets, Lavash Wraps, Kathi Rolls, Stuffed Paratha | Largest category, most creator diversity, nested sub-recipes for chunking challenge |
| `Salads___Whole_Food_Plant-Based.pdf` | Salads | Different recipe structure, shorter ingredient lists, good contrast to sandwiches |
| `Sweet_Porridge__Beyond_Oatmeal____Whole_Food_Plant-Based.pdf` | Sweet Porridge / Breakfast | Different meal type, different vocabulary, tests cross-category retrieval |

---

## Full Corpus PDFs (to be added in later weeks)

| File | Category |
|---|---|
| `Sandwiches___Pita_Pockets___Whole_Food_Plant-Based.pdf` | Sandwiches & Pita Pockets |
| `Salads___Whole_Food_Plant-Based.pdf` | Salads |
| `Sweet_Porridge__Beyond_Oatmeal____Whole_Food_Plant-Based.pdf` | Sweet Porridge |
| `Soups___Stews___Whole_Food_Plant-Based.pdf` | Soups & Stews |
| `Dal__Sambar___Whole_Food_Plant-Based.pdf` | Dal & Sambar |
| `Idli__Dosa___Whole_Food_Plant-Based.pdf` | Idli & Dosa |
| `Roti_Paratha___Whole_Food_Plant-Based.pdf` | Roti & Paratha |
| `Indian_Thali___Whole_Food_Plant-Based.pdf` | Indian Thali |
| `Rainbow_Meals___Whole_Food_Plant-Based.pdf` | Rainbow Meals |
| `Rainbow_Veggies_Medley___Whole_Food_Plant-Based.pdf` | Rainbow Veggies Medley |
| `Savory_Pancakes___Waffles___Whole_Food_Plant-Based.pdf` | Savory Pancakes & Waffles |
| `Savory_Snacks___Whole_Food_Plant-Based.pdf` | Savory Snacks |
| `Smoothies___Beverages___Whole_Food_Plant-Based.pdf` | Smoothies & Beverages |
| `Tikkis__Cutlets__Falafel__Dumplings___Whole_Food_Plant-Based.pdf` | Tikkis, Cutlets, Falafel |
| `Misc_Recipes___Whole_Food_Plant-Based.pdf` | Miscellaneous Recipes |
| *(remaining 7 PDFs to be added as obtained)* | TBD |

---

## Extraction Method

### Why extraction is non-trivial
Every recipe in this collection is stored as an **image-based recipe card** — not as
selectable text. The PDFs are collections of recipe card images. Conventional text
extraction tools (pdfplumber, pdfminer) return empty or near-empty results.
A vision-based extraction pipeline is required.

### Extraction Pipeline

```
Step 1 — PDF to Images
    Tool: PyMuPDF (fitz)
    Method: Extract each PDF page as a PNG image at 200 DPI
    Output: data/raw/images/{pdf_name}/page_{n}.png

Step 2 — Image to Structured Text
    Tool: Gemini Vision API
    Method: Send each page image to Gemini with a structured extraction prompt
    Output: data/processed/{pdf_name}/recipe_{n}.json

Step 3 — Validate and Store
    Method: Spot-check 10% of extractions manually
    Output: Validated JSON files ready for indexing
```

### Gemini Vision Extraction Prompt (template)
```
Extract all recipe information from this recipe card image.
Return a JSON object with the following fields:
{
  "recipe_name": "",
  "creator": "",
  "category": "",
  "subcategory": "",
  "ingredients": {
    "whole_grains": [],
    "beans_legumes": [],
    "leafy_greens": [],
    "rainbow_veggies": [],
    "mushrooms": [],
    "nuts_seeds_avocados": [],
    "fruits": [],
    "berries": [],
    "tubers": [],
    "herbs_spices": [],
    "lime_lemon_vinegar": [],
    "sweeteners": []
  },
  "instructions": "",
  "serving_suggestion": "",
  "notes": ""
}
If a field is not present on the card, use an empty string or empty list.
```

---

## Preprocessing Steps

### What was cleaned / transformed
| Step | What | Why |
|---|---|---|
| Remove noise | Navigation text, footers, copyright notices, Disqus comment boilerplate | Not relevant to recipe retrieval |
| Normalize format | Convert all extracted text to consistent JSON structure | Enables reliable metadata filtering |
| Enrich metadata | Add source PDF filename, page number, extraction date | Enables provenance tracking and re-indexing |
| Deduplicate | Check for identical recipe names across PDFs | Avoid redundant chunks in vector store |

### What was intentionally kept
| Element | Reason |
|---|---|
| Creator name exactly as written | Enables precise creator-based filtering |
| Original ingredient category labels (WHOLE GRAINS, BEANS, etc.) | These are meaningful WFPB taxonomy terms used in queries |
| Cooking method notes | Relevant for strategy-based queries |
| Attribution to Thankful2Plants.com | Required by CC BY-NC-ND 4.0 license |

---

## Processed Data Format

Each recipe card is stored as a single JSON file in `data/processed/`.
One JSON file = one chunk in the vector store.

### File naming convention
```
data/processed/{pdf_stem}/recipe_{page_number:03d}.json
```

### Example
```
data/processed/Sandwiches___Pita_Pockets/recipe_002.json
```

### JSON schema
```json
{
  "id": "sandwiches_pita_pockets_002",
  "recipe_name": "Ezekiel Sandwich with Walnut Mushroom Pate",
  "creator": "Kumar Natarajan",
  "category": "Sandwich",
  "subcategory": "Ezekiel Sandwich",
  "source_pdf": "Sandwiches___Pita_Pockets___Whole_Food_Plant-Based.pdf",
  "page_number": 2,
  "source_url": "https://thankful2plants.com",
  "extraction_date": "2026-02-20",
  "text": "Full extracted recipe text used for embedding...",
  "ingredients": {
    "whole_grains": ["Ezekiel 4:9 bread"],
    "beans_legumes": ["Ezekiel 4:9 bread", "mung bean sprouts"],
    "leafy_greens": ["spinach"],
    "mushrooms": ["white button mushrooms"],
    "nuts_seeds_avocados": ["walnuts"],
    "herbs_spices": ["parsley", "green chili", "black pepper"]
  },
  "cooking_method": ["dry roast", "sauté without oil", "blend"],
  "instructions": "Dry roast walnuts. Sauté mushrooms, onion and garlic without oil..."
}
```

---

## Data Quality Notes

*To be completed after running `analysis/data_quality_notes.md` pipeline.*

Preliminary observations from manual review of Week 1 PDFs:

| Observation | Detail |
|---|---|
| Recipe card layout | Consistent visual structure across all cards — good for extraction |
| Creator diversity | Sandwiches PDF alone has 11 different creators |
| Nested recipes | Some cards contain sub-recipes (e.g. Kathi Roll contains Sweet Potato Paratha recipe) — may need 2 chunks |
| Ingredient taxonomy | All cards use consistent WFPB category labels (WHOLE GRAINS, BEANS, LEAFY GREENS, etc.) — valuable metadata |
| Language | All recipes in English |
| Image quality | Recipe cards are high resolution — Gemini Vision should extract reliably |

---

## Re-indexing Policy

Processed JSON files in `data/processed/` are saved **before** indexing.
This means:
- If chunking strategy changes (Week 2), re-index from JSON — do not re-extract from PDFs
- If embedding model changes, re-index from JSON — do not re-extract from PDFs  
- Only re-run Gemini Vision extraction if source PDFs change or extraction quality is poor

This separation of extraction and indexing is intentional and saves significant API costs.

---

*This document will be updated as additional PDFs are ingested in Weeks 2-6.*
