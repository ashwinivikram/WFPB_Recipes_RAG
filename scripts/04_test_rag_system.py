"""
04_test_rag_system.py
---------------------
Teaching script — shows the WFPB RAG pipeline internals step by step.

Unlike 05_interactive_rag.py which is designed for smooth interaction,
this script is designed for LEARNING. It prints every intermediate
result so you can see exactly what RAG does at each stage:

    Stage 1 — Embed the query
    Stage 2 — Search Qdrant for similar vectors
    Stage 3 — Inspect retrieved chunks
    Stage 4 — Build the prompt with context
    Stage 5 — Generate answer with Gemini
    Stage 6 — Evaluate: was the right context retrieved?

Run this AFTER 03_run_indexing.py has indexed your recipes.

Usage:
    python 04_test_rag_system.py
    python 04_test_rag_system.py --query "What recipes use avocado?"
    python 04_test_rag_system.py --top-k 5

Author: Ashwini Vikram
Project: WFPB Recipe RAG System
Data Source: Thankful2Plants.com (CC BY-NC-ND 4.0)
"""

import os
import sys
import json
import argparse
import textwrap
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
from rich.rule import Rule

console = Console()

from google import genai
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from dotenv import load_dotenv

# ── Load environment variables ────────────────────────────────────────────────
load_dotenv()

QDRANT_URL      = os.getenv("QDRANT_URL")
QDRANT_API_KEY  = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_PHASE1", "WFPB recipes")
GOOGLE_API_KEY  = os.getenv("GOOGLE_API_KEY")
FASTEMBED_MODEL = os.getenv("FASTEMBED_MODEL", "BAAI/bge-large-en-v1.5")
EMBEDDING_DIM   = int(os.getenv("EMBEDDING_DIMENSION", "1024"))

# ── Test queries covering all query types ─────────────────────────────────────
# These 10 queries test every retrieval scenario your system must handle.
# Run all of them and save results to traces/session_YYYYMMDD.md
TEST_QUERIES = [
    # Ingredient-based
    {
        "query":    "What recipes can I make with avocado and tofu?",
        "type":     "ingredient",
        "expected": "recipes containing both avocado and tofu",
    },
    {
        "query":    "Show me recipes that use edamame",
        "type":     "ingredient",
        "expected": "recipes with edamame as an ingredient",
    },
    # Creator-based
    {
        "query":    "What recipes did Kumar Natarajan create?",
        "type":     "creator",
        "expected": "Walnut Mushroom Pate sandwich, Tofu Bhurji, Cranberry Relish",
    },
    {
        "query":    "Show me recipes by Dr Sirisha Potluri",
        "type":     "creator",
        "expected": "Hummus Mushroom Tofu Sandwich, Chickpea Tuna Pita, Tzatziki Pita",
    },
    # Strategy-based
    {
        "query":    "How do I make Walnut Mushroom Pate?",
        "type":     "strategy",
        "expected": "dry roast walnuts, sauté mushrooms without oil, blend",
    },
    {
        "query":    "What is the cooking strategy for Tofu Banh Mi?",
        "type":     "strategy",
        "expected": "marinate overnight, bake at 350F, pickle vegetables in rice vinegar",
    },
    # Meal planning
    {
        "query":    "Suggest quick weekday lunch ideas that need no cooking",
        "type":     "meal_planning",
        "expected": "simple assembly sandwiches, no-cook recipes",
    },
    {
        "query":    "What are good recipes for an Indian themed dinner?",
        "type":     "meal_planning",
        "expected": "Vada Pav, Kathi Rolls, Chutney Sandwich, Peas Potato Masala",
    },
    # Thematic
    {
        "query":    "Which recipes use fermented ingredients like miso or natto?",
        "type":     "thematic",
        "expected": "recipes mentioning miso, natto, tempeh, ACV, or soy yogurt",
    },
    # Cross-category
    {
        "query":    "What breakfast or porridge recipes are available?",
        "type":     "cross_category",
        "expected": "sweet porridge recipes from the porridge PDF",
    },
]


# ── RAG System prompt ─────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a knowledgeable Whole Food Plant-Based (WFPB) recipe assistant
for the Thankful2Plants collection (thankful2plants.com) by Gurmeet Manku.

Answer the user's question using ONLY the recipe information provided in the context below.
Do not invent recipes or ingredients that are not in the context.

If the context does not contain enough information to answer the question fully, say so clearly
and describe what information IS available.

Always mention the recipe creator's name when discussing a specific recipe.
Always cite the source PDF name and page number for each recipe (e.g. "Source: Sandwiches & Pita Pockets — Whole Food Plant-Based.pdf, page 9").
Always attribute information to Thankful2Plants.com.
Format your response in clean Markdown. When listing multiple recipes, put a blank line between each bullet point so the list is easy to read.

Context (retrieved recipe cards):
{context}
"""


# ── Initialize clients ────────────────────────────────────────────────────────
def initialize_clients():
    """Initialize Qdrant, Gemini, and FastEmbed clients."""
    # Qdrant
    qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    qdrant.get_collections()  # verify connection

    # Gemini
    gemini = genai.Client(api_key=GOOGLE_API_KEY)

    # FastEmbed
    embedder = TextEmbedding(model_name=FASTEMBED_MODEL)

    return qdrant, gemini, embedder


# ── Stage 1: Embed query ──────────────────────────────────────────────────────
def embed_query(query: str, embedder: TextEmbedding) -> list[float]:
    """
    Convert the user's natural language query into a vector.

    This is the same embedding model used for indexing — critical that
    they match, otherwise similarity search is meaningless.
    """
    embeddings = list(embedder.embed([query]))
    return embeddings[0].tolist()


# ── Stage 2: Search Qdrant ────────────────────────────────────────────────────
def search_qdrant(
    query_vector: list[float],
    qdrant: QdrantClient,
    top_k: int = 5,
    creator_filter: str = None,
    category_filter: str = None,
) -> list:
    """
    Search Qdrant for the most similar recipe vectors.

    Optionally filter by creator or category BEFORE similarity search.
    Filtering narrows the candidate set — Qdrant then ranks by similarity
    within that filtered set.

    Args:
        query_vector:    Embedded query (1024 dims)
        qdrant:          Qdrant client
        top_k:           Number of results to return
        creator_filter:  Optional exact creator name to filter by
        category_filter: Optional category to filter by

    Returns:
        List of ScoredPoint objects with payload and score
    """
    # Build optional metadata filter
    query_filter = None
    conditions   = []

    if creator_filter:
        conditions.append(
            FieldCondition(
                key="creator",
                match=MatchValue(value=creator_filter),
            )
        )
    if category_filter:
        conditions.append(
            FieldCondition(
                key="category",
                match=MatchValue(value=category_filter),
            )
        )
    if conditions:
        query_filter = Filter(must=conditions)

    results = qdrant.query_points(
    collection_name = COLLECTION_NAME,
    query           = query_vector,
    limit           = top_k,
    query_filter    = query_filter,
    with_payload    = True,
    with_vectors    = False,
).points

    return results


# ── Stage 3: Format retrieved chunks ─────────────────────────────────────────
def format_chunks_as_context(results: list) -> str:
    """
    Convert retrieved Qdrant results into a context string for the LLM prompt.

    Each chunk includes recipe name, creator, and full text.
    Numbered so the LLM can reference specific recipes.
    """
    if not results:
        return "No relevant recipes found."

    context_parts = []
    for i, result in enumerate(results, 1):
        payload = result.payload or {}
        chunk   = [
            f"[Recipe {i}]",
            f"Name    : {payload.get('recipe_name', 'Unknown')}",
            f"Creator : {payload.get('creator', 'Unknown')}",
            f"Category: {payload.get('category', 'Unknown')}",
            f"Source  : {payload.get('source_pdf', 'Unknown')}",
            f"Page    : {payload.get('page_number', 'Unknown')}",
            f"Score   : {result.score:.4f}",
            f"",
            payload.get("text", ""),
        ]
        context_parts.append("\n".join(chunk))

    return "\n\n---\n\n".join(context_parts)


# ── Stage 4: Build prompt ─────────────────────────────────────────────────────
def build_prompt(query: str, context: str) -> str:
    """Inject retrieved context into the system prompt template."""
    return SYSTEM_PROMPT.format(context=context) + f"\n\nUser question: {query}"


# ── Stage 5: Generate answer ──────────────────────────────────────────────────
def generate_answer(prompt: str, gemini) -> str:
    """Send the prompt to Gemini and return the generated answer."""
    response = gemini.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text


# ── Full RAG pipeline (verbose — for teaching) ────────────────────────────────
def run_rag_verbose(
    query:           str,
    qdrant:          QdrantClient,
    gemini,
    embedder:        TextEmbedding,
    top_k:           int = 5,
    creator_filter:  str = None,
    category_filter: str = None,
    show_prompt:     bool = False,
) -> dict:
    """
    Run the complete RAG pipeline with detailed logging at each stage.
    Returns a dict with all intermediate results for tracing.
    """
    divider = "─" * 60

    print(f"\n{'═' * 60}")
    print(f"  QUERY: {query}")
    print(f"{'═' * 60}")

    # ── Stage 1: Embed query ──────────────────────────────────────────────────
    print(f"\n── Stage 1: Embedding Query {divider[:20]}")
    query_vector = embed_query(query, embedder)
    print(f"  Model  : {FASTEMBED_MODEL}")
    print(f"  Dims   : {len(query_vector)}")
    print(f"  Sample : [{query_vector[0]:.6f}, {query_vector[1]:.6f}, ... {query_vector[-1]:.6f}]")

    # ── Stage 2: Search Qdrant ────────────────────────────────────────────────
    print(f"\n── Stage 2: Searching Qdrant {divider[:19]}")
    if creator_filter:
        print(f"  Filter : creator = '{creator_filter}'")
    if category_filter:
        print(f"  Filter : category = '{category_filter}'")
    print(f"  Top-k  : {top_k}")

    results = search_qdrant(
        query_vector    = query_vector,
        qdrant          = qdrant,
        top_k           = top_k,
        creator_filter  = creator_filter,
        category_filter = category_filter,
    )
    print(f"  Found  : {len(results)} results")

    # ── Stage 3: Inspect retrieved chunks ────────────────────────────────────
    print(f"\n── Stage 3: Retrieved Chunks {divider[:19]}")
    for i, result in enumerate(results, 1):
        payload = result.payload or {}
        print(f"\n  [{i}] Score: {result.score:.4f}")
        print(f"       Recipe  : {payload.get('recipe_name', 'Unknown')}")
        print(f"       Creator : {payload.get('creator', 'Unknown')}")
        print(f"       Category: {payload.get('category', 'Unknown')}")
        print(f"       Source  : {payload.get('source_pdf', 'Unknown')}")
        # Show first 120 chars of text
        text_preview = payload.get("text", "")[:120].replace("\n", " ")
        print(f"       Preview : {text_preview}...")

    # ── Stage 4: Build prompt ─────────────────────────────────────────────────
    print(f"\n── Stage 4: Building Prompt {divider[:20]}")
    context = format_chunks_as_context(results)
    prompt  = build_prompt(query, context)
    print(f"  Context length : {len(context)} characters")
    print(f"  Prompt length  : {len(prompt)} characters")
    print(f"  Recipes in ctx : {len(results)}")

    if show_prompt:
        print(f"\n  Full prompt:")
        print(textwrap.indent(prompt[:800] + "...", "    "))

    # ── Stage 5: Generate answer ──────────────────────────────────────────────
    print(f"\n── Stage 5: Generating Answer {divider[:17]}")
    print("  Calling Gemini 2.5 Flash...")
    answer = generate_answer(prompt, gemini)
    print(f"  Answer length  : {len(answer)} characters")

    # ── Stage 6: Display answer ───────────────────────────────────────────────
    console.print()
    console.rule("[bold cyan]Stage 6: Answer[/bold cyan]", style="cyan")
    console.print(Markdown(answer))
    console.rule(style="cyan")

    return {
        "query":        query,
        "query_vector": query_vector[:5],  # Save only sample for traces
        "results":      [
            {
                "score":       r.score,
                "recipe_name": r.payload.get("recipe_name"),
                "creator":     r.payload.get("creator"),
                "category":    r.payload.get("category"),
                "source_pdf":  r.payload.get("source_pdf"),
            }
            for r in results
        ],
        "answer":       answer,
        "context_len":  len(context),
    }


# ── Self-assessment prompt ────────────────────────────────────────────────────
def prompt_self_assessment(result: dict):
    """
    Ask the user to assess the quality of the retrieval and answer.
    This assessment goes into the traces/ folder as your evaluation dataset.
    """
    print(f"\n── Self-Assessment (for traces/) {'─' * 26}")
    print("  Please evaluate this result:")
    print("  1 = Poor  2 = Fair  3 = Good  4 = Excellent")

    retrieval_score = input("\n  Retrieval quality (were right recipes retrieved?): ").strip()
    answer_score    = input("  Answer quality (was the answer accurate?): ").strip()
    notes           = input("  Notes (what worked? what failed?): ").strip()

    result["assessment"] = {
        "retrieval_score": retrieval_score,
        "answer_score":    answer_score,
        "notes":           notes,
    }
    return result


# ── Save trace ────────────────────────────────────────────────────────────────
def save_trace(results: list[dict], traces_dir: Path):
    """
    Save session results to traces/session_YYYYMMDD.md
    These traces become your evaluation dataset for Week 4.
    """
    from datetime import datetime
    timestamp    = datetime.now().strftime("%Y%m%d_%H%M")
    trace_path   = traces_dir / f"session_{timestamp}.md"
    traces_dir.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# RAG Session Trace",
        f"",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Collection:** {COLLECTION_NAME}",
        f"**Embedding model:** {FASTEMBED_MODEL}",
        f"**LLM:** Gemini 2.5 Flash",
        f"**Total queries:** {len(results)}",
        f"",
        f"---",
        f"",
    ]

    for i, result in enumerate(results, 1):
        assessment = result.get("assessment", {})
        lines += [
            f"## Query {i}: {result['query']}",
            f"",
            f"**Retrieved chunks ({len(result['results'])}):**",
            f"",
        ]
        for j, r in enumerate(result["results"], 1):
            lines.append(
                f"{j}. `{r['recipe_name']}` by {r['creator']} "
                f"— score: {r['score']:.4f} — {r['source_pdf']}"
            )
        lines += [
            f"",
            f"**Answer:**",
            f"",
            f"{result['answer']}",
            f"",
            f"**Assessment:**",
            f"",
            f"- Retrieval quality: {assessment.get('retrieval_score', 'N/A')} / 4",
            f"- Answer quality: {assessment.get('answer_score', 'N/A')} / 4",
            f"- Notes: {assessment.get('notes', 'N/A')}",
            f"",
            f"---",
            f"",
        ]

    with open(trace_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n[OK] Trace saved to {trace_path}")
    return trace_path


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("\n=== 04_test_rag_system.py — WFPB RAG Pipeline Teaching Script ===\n")

    # ── Parse arguments ───────────────────────────────────────────────────────
    parser = argparse.ArgumentParser(description="Test and inspect the WFPB RAG pipeline")
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="Run a single query instead of all test queries",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of chunks to retrieve (default: 5)",
    )
    parser.add_argument(
        "--show-prompt",
        action="store_true",
        help="Print the full prompt sent to Gemini",
    )
    parser.add_argument(
        "--no-assess",
        action="store_true",
        help="Skip self-assessment prompts (for quick testing)",
    )
    args = parser.parse_args()

    # ── Validate environment ──────────────────────────────────────────────────
    missing = []
    if not QDRANT_URL:     missing.append("QDRANT_URL")
    if not QDRANT_API_KEY: missing.append("QDRANT_API_KEY")
    if not GOOGLE_API_KEY: missing.append("GOOGLE_API_KEY")
    if missing:
        print(f"[ERROR] Missing: {', '.join(missing)}")
        sys.exit(1)
    print("[OK] Environment loaded.")

    # ── Initialize ────────────────────────────────────────────────────────────
    print("[INFO] Initializing clients...")
    try:
        qdrant, gemini, embedder = initialize_clients()
        print("[OK] All clients ready.\n")
    except Exception as e:
        print(f"[ERROR] Initialization failed: {e}")
        sys.exit(1)

    # ── Check collection has data ─────────────────────────────────────────────
    info = qdrant.get_collection(COLLECTION_NAME)
    print(f"[INFO] Collection '{COLLECTION_NAME}' has {info.points_count} indexed recipes.")
    if info.points_count == 0:
        print("[ERROR] Collection is empty — run 03_run_indexing.py --test first.")
        sys.exit(1)

    # ── Determine queries to run ──────────────────────────────────────────────
    if args.query:
        queries = [{"query": args.query, "type": "custom", "expected": ""}]
    else:
        queries = TEST_QUERIES
        print(f"[INFO] Running {len(queries)} test queries.\n")
        print("       Tip: Use --query 'your question' to test a single query.")
        print("       Tip: Use --no-assess to skip assessment prompts.\n")

    # ── Run queries ───────────────────────────────────────────────────────────
    all_results = []

    for i, q in enumerate(queries, 1):
        if not args.query:
            print(f"\n[{i}/{len(queries)}] Query type: {q['type'].upper()}")
            if q.get("expected"):
                print(f"     Expected : {q['expected']}")

        result = run_rag_verbose(
            query       = q["query"],
            qdrant      = qdrant,
            gemini      = gemini,
            embedder    = embedder,
            top_k       = args.top_k,
            show_prompt = args.show_prompt,
        )
        result["query_type"] = q.get("type", "custom")
        result["expected"]   = q.get("expected", "")

        # Self-assessment
        if not args.no_assess:
            result = prompt_self_assessment(result)

        all_results.append(result)

        # Pause between queries if running full test suite
        if not args.query and i < len(queries):
            cont = input("\n  Continue to next query? [Enter / q to quit]: ").strip()
            if cont.lower() == "q":
                print("  Stopping early.")
                break

    # ── Save traces ───────────────────────────────────────────────────────────
    traces_dir = Path(__file__).parent.parent / "traces"
    trace_path = save_trace(all_results, traces_dir)

    print(f"\n{'═' * 60}")
    print(f"  SESSION COMPLETE")
    print(f"  Queries run : {len(all_results)}")
    print(f"  Trace saved : {trace_path}")
    print(f"{'═' * 60}")
    print("\n  Next step: python 05_interactive_rag.py")
    print("  Or review your traces and fill in analysis/data_quality_notes.md\n")


if __name__ == "__main__":
    main()
