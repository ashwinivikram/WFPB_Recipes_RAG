# Project Context: WFPB Recipe RAG System

## Overview
This is a RAG (Retrieval-Augmented Generation) capstone project built by Ashwini Vikram.
It indexes Whole Food Plant-Based (WFPB) recipes from Thankful2Plants.com into a vector
database and enables natural language querying over 2000+ recipe cards across 22 PDFs.

## Tech Stack
- **Language:** Python 3.13.12
- **Vector DB:** Qdrant Cloud
- **Embedding model:** BAAI/bge-large-en-v1.5 via FastEmbed (1024 dimensions, cosine similarity)
- **LLM:** Gemini 2.5 Flash (`google.genai` package)
- **PDF extraction:** PyMuPDF (fitz)
- **Vision extraction:** Gemini Vision API (recipe cards are image-based, not text)
- **Environment:** python-dotenv, `.env` file

## Project Structure
```
AshwiniVikramWeek1/
├── .env.example              # Environment variable template
├── .env                      # Your actual keys (never commit this)
├── README.md                 # Project entry point and quick start
├── context.md                # This file — full technical context
├── docs/
│   └── scoping.md            # Project scope: IDENTIFY/QUALIFY/DEFINE/SCOPE
├── data/
│   ├── raw/                  # Source PDFs (3 for Week 1, 22 total eventually)
│   ├── raw/images/           # Extracted page images (auto-generated, do not commit)
│   └── processed/            # Extracted recipe JSONs (one per recipe card)
├── scripts/
│   ├── 01_setup_qdrant.py        # Create Qdrant collection (run once)
│   ├── create_pipeline_02.py     # Pipeline validation + shared functions
│   ├── 03_run_indexing.py        # Index PDFs into Qdrant
│   ├── 04_test_rag_system.py     # Teaching script — verbose pipeline internals
│   └── 05_interactive_rag.py     # Interactive query interface
├── analysis/
│   └── data_quality_notes.md    # Quantitative + qualitative findings
└── traces/                       # Session query logs (auto-generated)
    └── session_YYYYMMDD.md
```

## Environment Variables
```
QDRANT_URL                  # Qdrant Cloud cluster URL
QDRANT_API_KEY              # Qdrant API key
QDRANT_COLLECTION_PHASE1    # Collection name (e.g. WFPB recipes)
FASTEMBED_MODEL             # BAAI/bge-large-en-v1.5
EMBEDDING_DIMENSION         # 1024
FASTEMBED_BATCH_SIZE        # 32
GOOGLE_API_KEY              # Google AI Studio API key
```

> Note: `LLM_MODEL` is not read from env — all scripts hardcode `"gemini-2.5-flash"` directly.

## Script Execution Order
```bash
python scripts/01_setup_qdrant.py                    # Run once
python scripts/create_pipeline_02.py --pdf <file>    # Validate pipeline on 1 page
python scripts/03_run_indexing.py --test             # Index Week 1 PDFs (3 files)
python scripts/03_run_indexing.py --full             # Index all 22 PDFs (later)
python scripts/04_test_rag_system.py                 # Run 10 test queries verbosely
python scripts/05_interactive_rag.py                 # Interactive mode
python scripts/05_interactive_rag.py --retrieve-only # Inspect chunks without LLM
```

## Data Model
Each indexed recipe is stored as a Qdrant point with:
```json
{
  "id": "pdf_stem_page_001",
  "recipe_name": "Walnut Mushroom Pate Sandwich",
  "creator": "Kumar Natarajan",
  "category": "Sandwich",
  "subcategory": "Ezekiel Sandwich",
  "source_pdf": "Sandwiches___Pita_Pockets___Whole_Food_Plant-Based.pdf",
  "page_number": 9,
  "source_url": "https://thankful2plants.com",
  "attribution": "Thankful2Plants.com by Gurmeet Manku (CC BY-NC-ND 4.0)",
  "all_ingredients_flat": "Ezekiel 4:9 bread, walnuts, mushrooms, spinach...",
  "cooking_methods": ["dry roast", "saute", "blend"],
  "text": "Recipe: ... Creator: ... Ingredients: ... Instructions: ...",
  "embedding": [1024-dim vector]
}
```

## Qdrant Payload Indexes (for filtered search)
- `creator` — keyword index (e.g. filter by "Kumar Natarajan")
- `category` — keyword index (e.g. filter by "Sandwich")
- `subcategory` — keyword index
- `source_pdf` — keyword index

## Known Issues and Fixes

### qdrant.search() removed in newer client versions
`qdrant.search()` was removed. Replace with `qdrant.query_points()`:
```python
# OLD (broken)
results = qdrant.search(collection_name=..., query_vector=..., limit=...)

# NEW (correct)
results = qdrant.query_points(collection_name=..., query=..., limit=...).points
```

**Status by script:**
| Script | Status |
|---|---|
| `04_test_rag_system.py` | ✅ Fixed — uses `query_points()` |
| `05_interactive_rag.py` | ✅ Fixed — uses `query_points()` |

### google.generativeai deprecated
The `google.generativeai` package is deprecated. Migrate to `google.genai`:
```python
# OLD (deprecated)
import google.generativeai as genai
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")
response = model.generate_content(prompt)

# NEW (correct)
from google import genai
client = genai.Client(api_key=GOOGLE_API_KEY)
response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
answer = response.text
```

**Status by script:**
| Script | Status |
|---|---|
| `04_test_rag_system.py` | ✅ Fixed — uses `google.genai` |
| `create_pipeline_02.py` | ✅ Fixed — uses `google.genai` |
| `03_run_indexing.py` | ✅ Fixed — uses `google.genai` |
| `05_interactive_rag.py` | ✅ Fixed — uses `google.genai` |

## RAG Pipeline (how it works)
```
User query (natural language)
    ↓
Embed query → 1024-dim vector (BAAI/bge-large-en-v1.5)
    ↓
Qdrant cosine similarity search → top-k recipe chunks
    ↓ (optional: filter by creator or category)
Format retrieved chunks as context string
    ↓
Build prompt: system prompt + context + user query
    ↓
Gemini 2.5 Flash → natural language answer
    ↓
User
```

## Query Types the System Handles
- **Ingredient:** "What can I make with avocado and tofu?"
- **Creator:** "Show me recipes by Dr Sirisha Potluri"
- **Strategy:** "How do I make Walnut Mushroom Pate?"
- **Meal planning:** "Suggest quick weekday lunches"
- **Thematic:** "Which recipes use fermented ingredients?"

## Week 1 Scope (current)
- 3 PDFs indexed: Sandwiches, Salads, Sweet Porridge
- Naive pipeline: one recipe card = one chunk
- Simple vector search (no hybrid, no reranking)
- Goal: working baseline to iterate on in Weeks 2-6

## Data Source
- Thankful2Plants.com by Gurmeet Manku
- License: CC BY-NC-ND 4.0
- Permission: explicitly granted by content owner
- Attribution required in all outputs
