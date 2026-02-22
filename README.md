# WFPB Recipe RAG System

A Retrieval-Augmented Generation (RAG) system that makes 2,000+ Whole Food Plant-Based recipes from [Thankful2Plants.com](https://thankful2plants.com) searchable by natural language.

**Author:** Ashwini Vikram | **Week:** 1 — Baseline Pipeline  
**Data source:** Thankful2Plants.com by Gurmeet Manku (CC BY-NC-ND 4.0)

---

## Quick Start

```bash
# 1. Copy env template and fill in your keys
cp .env.example .env

# 2. Create the Qdrant collection (run once)
python scripts/01_setup_qdrant.py

# 3. Validate pipeline on a single page
python scripts/create_pipeline_02.py --pdf <filename>

# 4. Index Week 1 PDFs (3 files)
python scripts/03_run_indexing.py --test

# 5. Run 10 test queries with full pipeline visibility
python scripts/04_test_rag_system.py

# 6. Interactive query mode
python scripts/05_interactive_rag.py
python scripts/05_interactive_rag.py --retrieve-only   # inspect chunks without LLM
```

## What It Does

Indexes image-based recipe card PDFs into a Qdrant vector database, then answers natural language questions over the collection using Gemini 2.5 Flash.

**Example queries the system handles:**
- *"What can I make with avocado and tofu?"*
- *"Show me recipes by Dr Sirisha Potluri"*
- *"How do I make Walnut Mushroom Pate?"*
- *"Suggest quick weekday lunches with no cooking"*
- *"Which recipes use fermented ingredients?"*

## Tech Stack

| Component | Tool |
|---|---|
| Vector DB | Qdrant Cloud |
| Embedding model | BAAI/bge-large-en-v1.5 via FastEmbed (1024 dims) |
| LLM | Gemini 2.5 Flash (`google.genai`) |
| PDF extraction | PyMuPDF (fitz) |
| Vision extraction | Gemini Vision API |

## Project Structure

```
AshwiniVikramWeek1/
├── .env.example              # Environment variable template
├── .env                      # Your actual keys (never commit this)
├── README.md                 # This file
├── context.md                # Full technical context and architecture
├── docs/
│   └── scoping.md            # Project scope: IDENTIFY/QUALIFY/DEFINE/SCOPE
├── data/
│   ├── raw/                  # Source PDFs
│   ├── raw/images/           # Extracted page images (auto-generated)
│   └── processed/            # Extracted recipe JSONs (one per recipe card)
├── scripts/
│   ├── 01_setup_qdrant.py        # Create Qdrant collection (run once)
│   ├── create_pipeline_02.py     # Pipeline functions (imported by other scripts)
│   ├── 03_run_indexing.py        # Index PDFs into Qdrant
│   ├── 04_test_rag_system.py     # Teaching script — verbose pipeline internals
│   └── 05_interactive_rag.py     # Interactive query interface
├── analysis/
│   └── data_quality_notes.md    # Quantitative + qualitative findings
└── traces/                       # Session query logs (auto-generated)
```

## Required Environment Variables

```
QDRANT_URL                  # Qdrant Cloud cluster URL
QDRANT_API_KEY              # Qdrant API key
QDRANT_COLLECTION_PHASE1    # Collection name (e.g. WFPB recipes)
FASTEMBED_MODEL             # BAAI/bge-large-en-v1.5
EMBEDDING_DIMENSION         # 1024
FASTEMBED_BATCH_SIZE        # 32
GOOGLE_API_KEY              # Google AI Studio API key
```

## Documentation

- **[context.md](context.md)** — Full architecture, data model, known issues, and pipeline walkthrough
- **[docs/scoping.md](docs/scoping.md)** — Problem statement, design decisions, and Week 1 scope
- **[analysis/data_quality_notes.md](analysis/data_quality_notes.md)** — Pre- and post-indexing data quality observations
