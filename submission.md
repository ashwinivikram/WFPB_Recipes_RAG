## Student Name
Ashwini Vikram

## Project Title
WFPB Recipe RAG System — Thankful2Plants.com Baseline

## Problem Statement
Anyone following or learning about the WFPB lifestyle who wants to cook from this collection but cannot efficiently find recipes based on ingredients they have, creators they follow, cooking techniques they want to learn, or meal planning needs.

## Data Overview
- **Corpus size:** 22 total PDFs across corpus (4 indexed for Week 1 baseline), ~227 recipe cards
- **Data sources:** Thankful2Plants.com personal blog (Gurmeet Manku)
- **Formats:** PDF files (image-based recipe cards)
- **Domain:** Whole Food Plant-Based (WFPB) recipes ranging from Sandwiches to Indian traditional cuisine

## Data Curation Summary
- **Extraction method:** Extracted PDFs to PNG images using PyMuPDF, then passed each image to Gemini Vision API to convert image-based recipe cards into structured JSON format.
- **Preprocessing steps:** Removed noise (navigation text, footers, copyright notices), normalized format into a consistent JSON schema to enable reliable metadata filtering, and added provenance (source PDF, page number).
- **Key decisions:** Kept creator names exactly as written for precise creator-based filtering rather than aggressive stemming. Kept original WFPB ingredient taxonomy labels (WHOLE GRAINS, BEANS, etc.) as they are meaningful terms used in queries.

## Pipeline Configuration
- **Vector database:** Qdrant
- **Collection name:** mcp_phase1_baseline
- **Embedding model:** BAAI/bge-large-en-v1.5 (dim=1024)
- **Chunk strategy:** One recipe card = one chunk (natural boundaries)
- **LLM:** Gemini 2.5 Flash
- **Documents indexed:** ~227 recipe chunks

## Trace Summary
Overall, the baseline RAG system performed excellently on named recipe retrieval, specific ingredient inclusions, and broad thematic searches (e.g., Indian themed dinners). It struggled significantly with exclusion queries ("no cooking") and shorthand metadata searches (dropping "Dr" in creator names), which exposed the limitations of pure dense vector search without explicit payload filtering. Generating answers was a strong point—the LLM correctly refused to hallucinate on missing info (like absent "natto" recipes).

| Query | Retrieval | Answer | Notes |
|-------|-----------|--------|-------|
| What recipes can I make with avocado and tomato? | Good | Good | Handled multi-ingredient well; filtered correctly. |
| Show me recipes that use edamame | Good | Good | Correctly returned the single relevant recipe across 4 PDFs. |
| What recipes did Sirisha Potluri create? | Partial | Partial | Shorthand name search missed multiple recipes. |
| Show me recipes by Dr Sirisha Potluri | Good | Good | Full name exact prefix search improved recall easily. |
| How do I make Walnut Mushroom Pate? | Good | Good | Highest score retrieval (0.8061); named queries are perfect. |
| What is the cooking strategy for Tofu Banh Mi? | Good | Good | Highest score (0.8323); correctly answered targeted method query. |
| Suggest quick weekday lunch ideas that need no cooking | Poor | Poor | "No cook" meaning wasn't captured strongly in dense vectors; top-k=5 too small. |
| What are good recipes for an Indian themed dinner? | Good | Good | Broad thematic categories with semantic synonyms worked really well. |
| Which recipes use fermented ingredients like miso or natto? | Partial | Good | No miso found, but LLM gracefully pivoted to soy sauce / tamari. |
| What breakfast or porridge recipes are available? | Good | Good | Overcame WFPB jargon mismatch (returned Savory Pancakes). |

## Observations
- **What types of queries work well?**
  Specific named recipes and explicit ingredient inclusion queries perform incredibly well. The system also shows strong semantic understanding for broad cultural thematic queries ("Indian dinner").
- **What types of queries struggle?**
  Exclusion criteria (e.g., "no cooking"), metadata shorthand (e.g., "Sirisha" vs "Dr Sirisha"), and meal planning queries that necessitate surfacing a large number of diverse recipes simultaneously.
- **Is the issue retrieval or generation?**
  The issue is almost entirely retrieval. The generation phase (Gemini 2.5 Flash) is robust, rarely hallucinates, and adheres nicely to the provided chunk context.
- **What would you improve first?**
  In Week 2, I will implement explicit metadata/payload filtering for `creator` and `category` to fix shorthand misses, separate nested sub-recipes into two unique chunks to avoid embedding dilution, and increase top-k or use HyDE to improve multi-recipe meal planning queries.

## Self-Assessment
Rate yourself honestly on each:

| Criteria | Score (1-5) | Notes |
|----------|-------------|-------|
| Problem scoping clarity | 5 | Clean IDENTIFY, QUALIFY, DEFINE, SCOPE mapped in scoping.md |
| Data sourcing and curation | 5 | Used complex Gemini Vision extraction for image-only PDFs |
| Pipeline is functional | 5 | All scripts run securely; Qdrant + FastEmbed + Gemini functional |
| Trace quality and depth | 5 | Sourced 10 high-quality traces breaking down retrieval vs general failures |
| Observations and analysis | 5 | Pinpointed exact dense vector limitations with "no cook" / negative constraints |
