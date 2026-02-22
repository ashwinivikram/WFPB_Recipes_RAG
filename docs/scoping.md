# Capstone Project Scoping Document

**Project:** Whole Food Plant-Based Recipe RAG System  
**Data Source:** Thankful2Plants.com (thankful2plants.com)  
**Author:** Ashwini Vikram  
**Date:** February 2026  
**Week:** 1 — Baseline Pipeline  

---

## IDENTIFY — What problem are you solving?

### Problem Statement
Gurmeet Manku's Thankful2Plants website contains hundreds of whole food plant-based (WFPB)
recipes across 22 recipe categories. Every recipe is stored as an image-based recipe card
(embedded in PDFs and on the website), making the content completely unsearchable by
conventional means. There is no way to ask "what can I make with tofu and spinach tonight?"
or "show me all recipes by Dr Sirisha Potluri" or "what's the cooking strategy for Kathi Rolls?"
and get a useful answer.

### Who has this problem?
Anyone following or learning about the WFPB lifestyle who wants to cook from this collection
but cannot efficiently find recipes based on ingredients they have, creators they follow,
cooking techniques they want to learn, or meal planning needs.

### What does success look like?
A conversational system where a user can ask natural language questions about the recipe
collection and receive accurate, grounded answers — with the retrieved recipe cards as
evidence — rather than hallucinated or generic responses.

### Example queries the system must handle
| Query Type | Example |
|---|---|
| Ingredient-based | "What recipes use avocado and tofu?" |
| Creator-based | "Show me all recipes by Kumar Natarajan" |
| Strategy-based | "What is the cooking technique behind Walnut Mushroom Pate?" |
| Meal planning | "Plan me a week of quick weekday lunches" |
| Thematic | "Which recipes use fermented ingredients?" |
| Dietary | "Which recipes require no cooking at all?" |
| Comparative | "How do Gurmeet Manku and Dr Sirisha Potluri differ in their sandwich style?" |

---

## QUALIFY — Is RAG the right approach?

### Why RAG and not a simple prompt?
The full recipe collection (2000+ recipe cards across 22 PDFs) is too large to fit in a
single prompt reliably and will continue to grow as Gurmeet adds new recipes. RAG allows
the system to scale without rebuilding the entire prompt as the corpus grows.

### Why RAG and not fine-tuning?
The recipes are factual, structured data. Fine-tuning would teach the model patterns but
would not reliably ground answers in specific recipe cards. RAG retrieves the actual source
content, enabling faithful, verifiable answers.

### Why RAG and not keyword search?
Many queries are semantic rather than keyword-based. "Something light and Mediterranean for
summer" will not match any exact keywords but should retrieve relevant recipes. Vector
similarity search handles this naturally.

### Data quality assessment
| Criterion | Assessment |
|---|---|
| Self-contained | ✅ Each recipe card is a complete, standalone document |
| Question-answerable | ✅ Clear ground truth — ingredients, creators, methods are verifiable |
| Familiar to builder | ✅ Domain is well understood; easy to evaluate correctness |
| Reasonable size | ✅ 2000+ recipes across 22 PDFs — start with subset for Week 1 baseline |
| Permission to use | ✅ Explicit permission granted by Gurmeet Manku (content owner) |
| License | ✅ CC BY-NC-ND 4.0 — non-commercial use with attribution permitted |

---

## DEFINE — What exactly are you building?

### System Architecture (Week 1 Baseline)

```
PDFs (22 files)
    ↓
[Extract] PyMuPDF → page images
    ↓
[Transform] Vision LLM → structured text per recipe card
    ↓
[Store] data/processed/ → JSON files (one per recipe card)
    ↓
[Embed] BAAI/bge-large-en-v1.5 via FastEmbed (dim=1024)
    ↓
[Index] Qdrant cloud collection (mcp_phase1_baseline)
    ↓
[Retrieve] Vector similarity search → top-k chunks
    ↓
[Generate] Gemini 2.5 Flash → grounded natural language answer
    ↓
User
```

### What this system is NOT (Week 1)
- Not a web application with a UI (command line only)
- Not optimized (naive chunking, simple vector search — intentionally)
- Not multi-modal (images are used for extraction only, not stored as embeddings)
- Not real-time (batch ingestion pipeline, not live scraping)

### Chunking strategy (Week 1 baseline)
One recipe card = one chunk. Natural boundaries exist in the data — each PDF page
contains one recipe card. This is the simplest meaningful chunking strategy and will
serve as the baseline against which Week 2 chunking experiments are compared.

### Metadata schema per chunk
```json
{
  "id": "unique_recipe_id",
  "text": "full extracted recipe text",
  "metadata": {
    "creator": "Gurmeet Manku",
    "category": "Sandwich",
    "subcategory": "Ezekiel Sandwich",
    "source_pdf": "Sandwiches___Pita_Pockets___Whole_Food_Plant-Based.pdf",
    "page_number": 2,
    "key_ingredients": ["tofu", "avocado", "alfalfa"],
    "cooking_method": ["no-cook", "assembly"],
    "source_url": "https://thankful2plants.com"
  }
}
```

---

## SCOPE — What are the boundaries for Week 1?

### In scope
- All 22 recipe PDFs currently in hand (2000+ recipe cards)
- Start with 3 PDFs for `--test` run, then full corpus for `--full` run
- 5 query types: ingredient, creator, strategy, meal planning, thematic
- Command-line interactive interface (`05_interactive_rag.py`)
- Retrieve-only mode for diagnostic inspection (`--retrieve-only`)
- Session traces documenting what works and what fails

### Out of scope (deferred to later weeks)
- Web scraping from thankful2plants.com (PDFs are sufficient for Week 1)
- Hybrid search combining keyword + vector (Week 3)
- Re-ranking retrieved chunks (Week 3)
- Evaluation framework with automated metrics (Week 4)
- Production serving, caching, API layer (Week 5-6)
- UI / frontend application
- Automatic ingestion of newly published recipes

### Success criteria for Week 1
- [ ] All 22 PDFs ingested and indexed in Qdrant (2000+ recipe cards)
- [ ] At least 10 test queries run and traced
- [x] System correctly retrieves relevant recipe cards for ingredient queries
- [x] System correctly filters by creator name
- [x] `--retrieve-only` used to diagnose at least one failure case
- [ ] `analysis/data_quality_notes.md` completed with quantitative findings
- [ ] All session traces saved in `traces/`

> *Pipeline scripts are complete and functional. Deprecation warnings exist in `03_run_indexing.py`, `create_pipeline_02.py`, and `05_interactive_rag.py` (see `context.md` Known Issues). Full corpus indexing and trace collection are in progress.*

### Known risks and challenges
| Risk | Likelihood | Mitigation |
|---|---|---|
| PDF recipe cards are image-based, not text | Certain | Use vision LLM for extraction |
| OCR/vision extraction quality varies | Medium | Manual spot-check 10% of extractions |
| Duplicate recipes across PDFs | Low-Medium | Check during data analysis step |
| Nested recipes (e.g. Kathi Roll has sub-recipe) | Medium | Handle in preprocessing, may need two chunks |
| Queries requiring multiple recipes (meal planning) | High | Increase top-k retrieval, note as Week 3 improvement |

---

## Tech Stack

| Component | Tool | Version/Config |
|---|---|---|
| Language | Python | 3.13.12 |
| Vector Database | Qdrant | Cloud hosted |
| Collection name | — | WFPB recipes |
| Embedding model | BAAI/bge-large-en-v1.5 | FastEmbed, dim=1024, batch=32 |
| LLM | Gemini 2.5 Flash | Google AI API |
| PDF extraction | PyMuPDF (fitz) | TBD version |
| Vision extraction | Gemini Vision API | For recipe card image → text |
| Environment config | python-dotenv | .env file |

---

## Data Source Documentation

| Field | Detail |
|---|---|
| Source | Thankful2Plants.com personal blog |
| Owner | Gurmeet Manku (computer scientist, WFPB practitioner since 2012) |
| Permission | Explicit permission granted by owner |
| License | CC BY-NC-ND 4.0 |
| Format | PDF files (image-based recipe cards) |
| Volume | 22 PDFs, 2000+ recipe cards |
| Categories | Sandwiches, Salads, Soups, Dal/Sambar, Idli/Dosa, Smoothies, and more |
| Attribution required | Yes — credit Thankful2Plants.com in all outputs |

---

*This document will be updated as the project evolves through Weeks 2-6.*
