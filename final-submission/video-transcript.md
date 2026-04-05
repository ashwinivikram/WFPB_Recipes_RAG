# Video Transcript

## Product Name
WFPB Recipe Assistant

## Problem Setup
"Hi, I'm Ashwini Vikram. Finding accurate, whole-food plant-based (WFPB) recipes can be challenging because typical recipe sites are cluttered, full of ads, and often mix in non-compliant ingredients. I built this WFPB Recipe Assistant to provide instant, faithful, and step-by-step cooking instructions directly sourced from high-quality, curated WFPB cookbooks and PDFs."

## System Design
"Here is the architecture. The system ingests raw recipe PDFs, using a custom regex strategy to carefully split complex recipe cards into separate 'Assembly' and 'Component' sub-recipe chunks. We then index them using a Hybrid strategy—combining Voyage AI dense embeddings with Qdrant BM25 sparse matching, which are fused using Reciprocal Rank Fusion. Our queries are intelligently routed to specific Gemini 2.5 flash prompts based on whether it's a 'HOW_TO' or 'FACTUAL' intent. Finally, we use Redis for sliding-window conversation memory and semantic caching for lightning-fast repeated queries."

## Live Demo

### Query 1: "How do I make walnut mushroom pate?"
- **What happened:** The system routed the query to the HOW_TO prompt, retrieved the exact chunk featuring the ingredients and assembly, and generated a step-by-step guide.
- **Result:** A clean, bulleted recipe for Walnut Mushroom Pate with zero hallucinations.
- **What this shows:** Demonstrates the core retrieval pipeline successfully executing a sub-recipe boundary retrieval, answering exactly what was requested.

### Query 2: "What recipes did Kumar Natarajan create?"
- **What happened:** The system relied heavily on the BM25 sparse component of our hybrid search to exact-match the creator's name across the corpus.
- **Result:** A list of WFPB recipes authored by Kumar Natarajan.
- **What this shows:** Proves why Dense-only retrieval failed in early iterations, and how the Hybrid pipeline successfully solves keyword-based entity lookups.

### Query 3: "How do I make walnut mushroom pate?" (Again)
- **What happened:** The query bypassed the LLM completely.
- **Result:** The exact same answer is returned instantly in under 50ms.
- **What this shows:** Shows our semantic caching layer using Redis vector search successfully accelerating system response time for common queries.
