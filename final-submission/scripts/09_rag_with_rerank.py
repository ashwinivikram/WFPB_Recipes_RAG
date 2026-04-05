"""
09_rag_with_rerank.py
---------------------
Week 3 RAG pipeline: hybrid search (dense + sparse) + Voyage reranking.

Retrieval pipeline:
  1. Embed query with Voyage voyage-3-large (dense) + BM25 (sparse)
  2. Hybrid search in wfpb_recipes_week3_hybrid, top 50 via RRF fusion
  3. Rerank with Voyage rerank-2, return top 10
  4. Generate answer with Gemini 2.5 Flash

Usage:
    python scripts/09_rag_with_rerank.py
    python scripts/09_rag_with_rerank.py --retrieve-only   # skip LLM answer
    python scripts/09_rag_with_rerank.py --top-k 10        # rerank top-k
    python scripts/09_rag_with_rerank.py --creator "Gurmeet"  # filter by creator

Commands in interactive mode:
    /help       Show this help
    /top-k N    Set rerank top-k (default 10)
    /retrieve   Toggle retrieve-only mode
    /status     Show current settings
    /quit       Exit

Author: Ashwini Vikram
Project: WFPB Recipe RAG System — Week 3
Data Source: Thankful2Plants.com (CC BY-NC-ND 4.0)
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

import voyageai
from dotenv import load_dotenv
from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import (
    SparseVector,
    Prefetch,
    FusionQuery,
    Fusion,
    Filter,
    FieldCondition,
    MatchValue,
)
from google import genai

# ── Load environment ───────────────────────────────────────────────────────────
load_dotenv()

QDRANT_URL      = os.getenv("QDRANT_URL")
QDRANT_API_KEY  = os.getenv("QDRANT_API_KEY")
VOYAGE_API_KEY  = os.getenv("VOYAGE_API_KEY")
GOOGLE_API_KEY  = os.getenv("GOOGLE_API_KEY")

VOYAGE_EMBED_MODEL  = "voyage-3-large"
VOYAGE_RERANK_MODEL = "rerank-2"
SPARSE_MODEL        = "Qdrant/bm25"
LLM_MODEL           = "gemini-2.5-flash"

COLLECTION_NAME     = "wfpb_recipes_week3_hybrid"
RETRIEVE_COUNT      = 50   # broad recall before reranking
DEFAULT_RERANK_K    = 10   # final chunks passed to LLM

# ── Paths ──────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
TRACES_DIR   = PROJECT_ROOT / "traces"


# ── System prompt ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a knowledgeable Whole Food Plant-Based (WFPB) cooking assistant.
Answer the user's question using ONLY the recipe context provided.
Be specific — cite ingredient quantities and steps when they appear in context.
If the context does not contain enough information to fully answer the question,
say so clearly and offer what partial information you have.
Do not invent ingredients or steps not present in the context."""


def validate_env():
    missing = []
    if not QDRANT_URL:     missing.append("QDRANT_URL")
    if not QDRANT_API_KEY: missing.append("QDRANT_API_KEY")
    if not VOYAGE_API_KEY or VOYAGE_API_KEY == "your_voyage_api_key_here":
        missing.append("VOYAGE_API_KEY")
    if not GOOGLE_API_KEY: missing.append("GOOGLE_API_KEY")
    if missing:
        print(f"[ERROR] Missing environment variables: {', '.join(missing)}")
        sys.exit(1)


# ── Retrieval ──────────────────────────────────────────────────────────────────
def hybrid_search(
    query: str,
    qdrant: QdrantClient,
    vo: voyageai.Client,
    sparse_model: SparseTextEmbedding,
    retrieve_count: int = RETRIEVE_COUNT,
    creator_filter: str = None,
) -> list:
    """Run hybrid search: dense + sparse vectors fused via RRF."""

    # Dense query embedding
    dense_result = vo.embed([query], model=VOYAGE_EMBED_MODEL, input_type="query")
    q_dense = dense_result.embeddings[0]

    # Sparse query embedding
    q_sparse_raw = list(sparse_model.embed([query]))[0]
    q_sparse = SparseVector(
        indices=q_sparse_raw.indices.tolist(),
        values=q_sparse_raw.values.tolist(),
    )

    # Optional creator filter
    qdrant_filter = None
    if creator_filter:
        qdrant_filter = Filter(
            must=[FieldCondition(key="creator", match=MatchValue(value=creator_filter))]
        )

    results = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        prefetch=[
            Prefetch(query=q_sparse, using="sparse", limit=retrieve_count),
            Prefetch(query=q_dense,  using="dense",  limit=retrieve_count),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=retrieve_count,
        query_filter=qdrant_filter,
        with_payload=True,
        with_vectors=False,
    )
    return results.points


def rerank(
    query: str,
    candidates: list,
    vo: voyageai.Client,
    top_k: int = DEFAULT_RERANK_K,
) -> list:
    """Rerank candidates with Voyage rerank-2. Returns top_k results."""
    if not candidates:
        return []

    documents = [r.payload.get("text", "") for r in candidates]
    reranked = vo.rerank(query, documents, model=VOYAGE_RERANK_MODEL, top_k=top_k)

    # Map reranked indices back to original candidate objects
    top_results = []
    for item in reranked.results:
        candidate = candidates[item.index]
        candidate.score = item.relevance_score
        top_results.append(candidate)

    return top_results


def retrieve_and_rerank(
    query: str,
    qdrant: QdrantClient,
    vo: voyageai.Client,
    sparse_model: SparseTextEmbedding,
    top_k: int = DEFAULT_RERANK_K,
    creator_filter: str = None,
) -> list:
    """Full retrieval pipeline: hybrid search → rerank → top_k chunks."""
    candidates = hybrid_search(query, qdrant, vo, sparse_model,
                               retrieve_count=RETRIEVE_COUNT,
                               creator_filter=creator_filter)
    return rerank(query, candidates, vo, top_k=top_k)


# ── Generation ─────────────────────────────────────────────────────────────────
def build_context(chunks: list) -> str:
    parts = []
    for i, chunk in enumerate(chunks, 1):
        p = chunk.payload
        name     = p.get("recipe_name", "(unnamed)")
        creator  = p.get("creator", "")
        category = p.get("category", "")
        text     = p.get("text", "")
        score    = round(chunk.score, 4)
        parts.append(
            f"[{i}] {name} (creator: {creator}, category: {category}, score: {score})\n{text}"
        )
    return "\n\n---\n\n".join(parts)


def generate_answer(query: str, chunks: list, gemini: genai.Client) -> str:
    context = build_context(chunks)
    prompt  = f"{SYSTEM_PROMPT}\n\nContext:\n{context}\n\nQuestion: {query}"
    resp = gemini.models.generate_content(
        model=LLM_MODEL,
        contents=prompt,
    )
    return resp.text


# ── Display ────────────────────────────────────────────────────────────────────
def display_chunks(chunks: list, retrieve_only: bool = False):
    label = "Reranked chunks" if not retrieve_only else "Retrieved chunks"
    print(f"\n  ── {label} ──")
    for i, chunk in enumerate(chunks, 1):
        p = chunk.payload
        name      = p.get("recipe_name", "(unnamed)")
        creator   = p.get("creator", "")
        category  = p.get("category", "")
        c_type    = p.get("chunk_type", "")
        score     = round(chunk.score, 4)
        type_str  = f" [{c_type}]" if c_type else ""
        print(f"  {i}. {name}{type_str}")
        print(f"     creator={creator}  category={category}  score={score}")


def print_help():
    print("""
  Commands:
    /help        Show this help
    /top-k N     Set number of chunks after reranking (default 10)
    /retrieve    Toggle retrieve-only mode (skip LLM answer)
    /status      Show current settings
    /quit        Exit
""")


# ── Session trace ──────────────────────────────────────────────────────────────
def save_trace(turns: list, retrieve_only: bool):
    TRACES_DIR.mkdir(exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M")
    path = TRACES_DIR / f"session_{ts}_w3.md"
    mode = "retrieve-only" if retrieve_only else "full-rag"
    lines = [f"# Session trace — Week 3 ({mode})\n", f"*{datetime.now().isoformat()}*\n\n"]
    for turn in turns:
        lines.append(f"## Q: {turn['query']}\n\n")
        lines.append("**Retrieved chunks:**\n")
        for i, c in enumerate(turn["chunks"], 1):
            p = c.payload
            lines.append(f"{i}. {p.get('recipe_name','')} (score={round(c.score,4)})\n")
        if turn.get("answer"):
            lines.append(f"\n**Answer:**\n{turn['answer']}\n")
        lines.append("\n---\n\n")
    path.write_text("".join(lines), encoding="utf-8")
    print(f"\n  [Session saved → {path.name}]")


# ── Main interactive loop ──────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Week 3 RAG with hybrid search + reranking")
    parser.add_argument("--retrieve-only", action="store_true",
                        help="Print retrieved chunks without generating an LLM answer")
    parser.add_argument("--top-k", type=int, default=DEFAULT_RERANK_K,
                        help=f"Number of chunks after reranking (default {DEFAULT_RERANK_K})")
    parser.add_argument("--creator", type=str, default=None,
                        help="Filter results to a specific creator name")
    args = parser.parse_args()

    print(f"\n=== 09_rag_with_rerank.py — Week 3 RAG Pipeline ===")
    print(f"  Collection   : {COLLECTION_NAME}")
    print(f"  Dense model  : {VOYAGE_EMBED_MODEL}")
    print(f"  Reranker     : {VOYAGE_RERANK_MODEL}")
    print(f"  Retrieve     : top {RETRIEVE_COUNT} (hybrid RRF)")
    print(f"  Rerank top-k : {args.top_k}")
    print(f"  Mode         : {'retrieve-only' if args.retrieve_only else 'full RAG'}")
    if args.creator:
        print(f"  Creator filter: {args.creator}")
    print("\nType /help for commands, /quit to exit.\n")

    validate_env()

    # Init clients
    print("Initialising clients...")
    qdrant       = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    vo           = voyageai.Client(api_key=VOYAGE_API_KEY)
    sparse_model = SparseTextEmbedding(SPARSE_MODEL)
    gemini       = genai.Client(api_key=GOOGLE_API_KEY)
    print("[OK] All clients ready.\n")

    top_k         = args.top_k
    retrieve_only = args.retrieve_only
    creator       = args.creator
    turns         = []

    while True:
        try:
            query = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not query:
            continue

        # Commands
        if query.startswith("/"):
            cmd = query.lower().split()
            if cmd[0] == "/quit":
                break
            elif cmd[0] == "/help":
                print_help()
            elif cmd[0] == "/retrieve":
                retrieve_only = not retrieve_only
                print(f"  Retrieve-only: {retrieve_only}")
            elif cmd[0] == "/top-k" and len(cmd) > 1:
                try:
                    top_k = int(cmd[1])
                    print(f"  Rerank top-k set to {top_k}")
                except ValueError:
                    print("  Usage: /top-k N")
            elif cmd[0] == "/status":
                print(f"  top-k={top_k}  retrieve-only={retrieve_only}  creator={creator}")
            else:
                print(f"  Unknown command: {cmd[0]}. Type /help.")
            continue

        # Retrieve + rerank
        print(f"\n  [Searching...]")
        try:
            chunks = retrieve_and_rerank(
                query, qdrant, vo, sparse_model,
                top_k=top_k, creator_filter=creator,
            )
        except Exception as e:
            print(f"  [ERROR] Retrieval failed: {e}")
            continue

        display_chunks(chunks, retrieve_only)

        answer = None
        if not retrieve_only and chunks:
            print("\n  [Generating answer...]")
            try:
                answer = generate_answer(query, chunks, gemini)
                print(f"\nAssistant: {answer}\n")
            except Exception as e:
                print(f"  [ERROR] Generation failed: {e}")

        turns.append({"query": query, "chunks": chunks, "answer": answer})

    if turns:
        save_trace(turns, retrieve_only)
    print("\nGoodbye!\n")


if __name__ == "__main__":
    main()
