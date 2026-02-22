"""
05_interactive_rag.py
---------------------
Interactive RAG interface for the WFPB Recipe collection.

Clean conversational mode for exploring the recipe knowledge base.
Unlike 04_test_rag_system.py, this script is designed for smooth
day-to-day use — minimal logging, natural conversation flow.

Key features:
  - Natural language recipe queries
  - --retrieve-only mode to inspect chunks WITHOUT LLM generation
    (use this to isolate retrieval problems from generation problems)
  - Optional creator and category filters
  - Session history saved automatically to traces/

Usage:
    python 05_interactive_rag.py                    # Full RAG mode
    python 05_interactive_rag.py --retrieve-only    # Inspect chunks only
    python 05_interactive_rag.py --top-k 8          # Retrieve more chunks
    python 05_interactive_rag.py --creator "Kumar Natarajan"
    python 05_interactive_rag.py --category "Sandwich"

Commands during session:
    /help       Show available commands
    /filter     Set or clear creator/category filters
    /top-k      Change number of retrieved chunks
    /retrieve   Toggle retrieve-only mode on/off
    /save       Save session trace manually
    /quit       Exit and save trace

Author: Ashwini Vikram
Project: WFPB Recipe RAG System
Data Source: Thankful2Plants.com (CC BY-NC-ND 4.0)
"""

import os
import sys
import argparse
import textwrap
from pathlib import Path
from datetime import datetime

# Force UTF-8 for standard output/error (fixes 'ascii' codec errors in some terminals)
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

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

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a knowledgeable Whole Food Plant-Based (WFPB) recipe assistant
for the Thankful2Plants collection (thankful2plants.com) by Gurmeet Manku.

Answer the user's question using ONLY the recipe information provided in the context below.
Do not invent recipes, ingredients, or creators not present in the context.

If the context does not contain enough information, say so clearly and describe what
information IS available that might be related.

Always mention the recipe creator's name when discussing a specific recipe.
Always attribute information to Thankful2Plants.com (CC BY-NC-ND 4.0).

Context (retrieved recipe cards):
{context}
"""


# ── Session state ─────────────────────────────────────────────────────────────
class Session:
    """Holds all state for an interactive RAG session."""

    def __init__(self, top_k: int, retrieve_only: bool,
                 creator_filter: str, category_filter: str):
        self.top_k           = top_k
        self.retrieve_only   = retrieve_only
        self.creator_filter  = creator_filter
        self.category_filter = category_filter
        self.history         = []  # list of {query, chunks, answer}
        self.start_time      = datetime.now()

    def add_turn(self, query: str, chunks: list, answer: str = None):
        self.history.append({
            "query":   query,
            "chunks":  chunks,
            "answer":  answer,
            "time":    datetime.now().strftime("%H:%M:%S"),
        })


# ── Initialize clients ────────────────────────────────────────────────────────
def initialize_clients():
    qdrant   = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    qdrant.get_collections()
    gemini   = genai.Client(api_key=GOOGLE_API_KEY)
    embedder = TextEmbedding(model_name=FASTEMBED_MODEL)
    return qdrant, gemini, embedder


# ── Embed query ───────────────────────────────────────────────────────────────
def embed_query(query: str, embedder: TextEmbedding) -> list[float]:
    embeddings = list(embedder.embed([query]))
    return embeddings[0].tolist()


# ── Search Qdrant ─────────────────────────────────────────────────────────────
def search_qdrant(
    query_vector:    list[float],
    qdrant:          QdrantClient,
    session:         Session,
) -> list:
    conditions = []
    if session.creator_filter:
        conditions.append(FieldCondition(
            key="creator",
            match=MatchValue(value=session.creator_filter),
        ))
    if session.category_filter:
        conditions.append(FieldCondition(
            key="category",
            match=MatchValue(value=session.category_filter),
        ))

    query_filter = Filter(must=conditions) if conditions else None

    return qdrant.query_points(
        collection_name = COLLECTION_NAME,
        query           = query_vector,
        limit           = session.top_k,
        query_filter    = query_filter,
        with_payload    = True,
        with_vectors    = False,
    ).points


# ── Format chunks for display (retrieve-only mode) ────────────────────────────
def display_chunks(results: list, query: str):
    """
    Display retrieved chunks clearly without LLM generation.

    This is the core diagnostic tool. When your system gives a wrong answer,
    run --retrieve-only to see exactly what was retrieved. If the right recipe
    IS in the chunks but the answer is wrong → generation problem.
    If the right recipe is NOT in the chunks → retrieval problem.
    """
    print(f"\n{'─' * 60}")
    print(f"  Retrieved {len(results)} chunks for: \"{query}\"")
    print(f"{'─' * 60}")

    if not results:
        print("  No results found.")
        return []

    chunk_data = []
    for i, result in enumerate(results, 1):
        payload = result.payload or {}
        name    = payload.get("recipe_name", "Unknown")
        creator = payload.get("creator", "Unknown")
        cat     = payload.get("category", "Unknown")
        pdf     = payload.get("source_pdf", "Unknown")
        score   = result.score
        text    = payload.get("text", "")

        print(f"\n  [{i}] {name}")
        print(f"       Creator  : {creator}")
        print(f"       Category : {cat}")
        print(f"       Source   : {pdf}")
        print(f"       Score    : {score:.4f}")
        print(f"       Preview  : {text[:150].replace(chr(10), ' ')}...")

        chunk_data.append({
            "rank":        i,
            "score":       score,
            "recipe_name": name,
            "creator":     creator,
            "category":    cat,
            "source_pdf":  pdf,
        })

    print(f"\n{'─' * 60}")
    print("  Diagnostic tip: Is the recipe you expected in this list?")
    print("  YES → generation problem (LLM not using the context well)")
    print("  NO  → retrieval problem (embedding similarity not matching)")
    print(f"{'─' * 60}\n")

    return chunk_data


# ── Format chunks as LLM context ─────────────────────────────────────────────
def format_context(results: list) -> str:
    if not results:
        return "No relevant recipes found in the collection."
    parts = []
    for i, result in enumerate(results, 1):
        payload = result.payload or {}
        chunk   = "\n".join([
            f"[Recipe {i}]",
            f"Name    : {payload.get('recipe_name', 'Unknown')}",
            f"Creator : {payload.get('creator', 'Unknown')}",
            f"Category: {payload.get('category', 'Unknown')}",
            f"",
            payload.get("text", ""),
        ])
        parts.append(chunk)
    return "\n\n---\n\n".join(parts)


# ── Generate answer ───────────────────────────────────────────────────────────
def generate_answer(query: str, results: list, gemini) -> str:
    context  = format_context(results)
    prompt   = SYSTEM_PROMPT.format(context=context) + f"\n\nUser question: {query}"
    response = gemini.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text


# ── Print answer ──────────────────────────────────────────────────────────────
def print_answer(answer: str):
    print(f"\n{'─' * 60}")
    wrapped = textwrap.fill(
        answer,
        width=68,
        initial_indent="  ",
        subsequent_indent="  ",
    )
    print(wrapped)
    print(f"{'─' * 60}\n")


# ── Handle session commands ───────────────────────────────────────────────────
def handle_command(command: str, session: Session) -> bool:
    """
    Process /commands typed during the session.
    Returns True to continue session, False to quit.
    """
    parts = command.strip().split()
    cmd   = parts[0].lower()

    if cmd == "/help":
        print("""
  Available commands:
  /help              Show this help message
  /filter creator    Filter by creator name (e.g. /filter creator Kumar Natarajan)
  /filter category   Filter by category (e.g. /filter category Sandwich)
  /filter clear      Remove all filters
  /top-k <n>         Set number of chunks to retrieve (e.g. /top-k 8)
  /retrieve          Toggle retrieve-only mode on/off
  /status            Show current session settings
  /save              Save session trace now
  /quit              Exit and save trace
        """)

    elif cmd == "/filter":
        if len(parts) < 2:
            print("  Usage: /filter creator <name> | /filter category <name> | /filter clear")
        elif parts[1] == "clear":
            session.creator_filter  = None
            session.category_filter = None
            print("  Filters cleared.")
        elif parts[1] == "creator" and len(parts) > 2:
            session.creator_filter = " ".join(parts[2:])
            print(f"  Creator filter set: '{session.creator_filter}'")
        elif parts[1] == "category" and len(parts) > 2:
            session.category_filter = " ".join(parts[2:])
            print(f"  Category filter set: '{session.category_filter}'")
        else:
            print("  Usage: /filter creator <name> | /filter category <name> | /filter clear")

    elif cmd == "/top-k":
        if len(parts) == 2 and parts[1].isdigit():
            session.top_k = int(parts[1])
            print(f"  Top-k set to {session.top_k}")
        else:
            print("  Usage: /top-k <number>")

    elif cmd == "/retrieve":
        session.retrieve_only = not session.retrieve_only
        mode = "ON (retrieve-only)" if session.retrieve_only else "OFF (full RAG)"
        print(f"  Retrieve-only mode: {mode}")

    elif cmd == "/status":
        print(f"""
  Current session settings:
    Mode           : {'retrieve-only' if session.retrieve_only else 'full RAG'}
    Top-k          : {session.top_k}
    Creator filter : {session.creator_filter or 'none'}
    Category filter: {session.category_filter or 'none'}
    Turns so far   : {len(session.history)}
        """)

    elif cmd == "/save":
        return "save"

    elif cmd == "/quit":
        return False

    return True


# ── Save session trace ────────────────────────────────────────────────────────
def save_trace(session: Session) -> Path:
    traces_dir = Path(__file__).parent.parent / "traces"
    traces_dir.mkdir(parents=True, exist_ok=True)

    timestamp  = session.start_time.strftime("%Y%m%d_%H%M")
    trace_path = traces_dir / f"session_{timestamp}.md"

    lines = [
        f"# RAG Session Trace",
        f"",
        f"**Date:** {session.start_time.strftime('%Y-%m-%d %H:%M')}",
        f"**Collection:** {COLLECTION_NAME}",
        f"**Embedding model:** {FASTEMBED_MODEL}",
        f"**LLM:** Gemini 2.5 Flash",
        f"**Mode:** {'retrieve-only' if session.retrieve_only else 'full RAG'}",
        f"**Total turns:** {len(session.history)}",
        f"",
        f"---",
        f"",
    ]

    for i, turn in enumerate(session.history, 1):
        lines += [
            f"## Turn {i} [{turn['time']}]: {turn['query']}",
            f"",
            f"**Retrieved chunks:**",
            f"",
        ]
        for chunk in turn.get("chunks", []):
            lines.append(
                f"- [{chunk['rank']}] `{chunk['recipe_name']}` by {chunk['creator']} "
                f"— score: {chunk['score']:.4f}"
            )

        if turn.get("answer"):
            lines += [
                f"",
                f"**Answer:**",
                f"",
                f"{turn['answer']}",
            ]

        lines += [f"", f"---", f""]

    with open(trace_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return trace_path


# ── Print session header ──────────────────────────────────────────────────────
def print_header(session: Session, points_count: int):
    mode = "RETRIEVE-ONLY" if session.retrieve_only else "FULL RAG"
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║       WFPB Recipe RAG — Thankful2Plants.com                  ║
║       Ashwini Vikram | Capstone Week 1                       ║
╠══════════════════════════════════════════════════════════════╣
║  Mode       : {mode:<46} ║
║  Collection : {COLLECTION_NAME:<46} ║
║  Recipes    : {str(points_count):<46} ║
║  Top-k      : {str(session.top_k):<46} ║
╚══════════════════════════════════════════════════════════════╝
  Type your question or /help for commands. /quit to exit.
""")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    # ── Parse arguments ───────────────────────────────────────────────────────
    parser = argparse.ArgumentParser(description="Interactive WFPB Recipe RAG")
    parser.add_argument(
        "--retrieve-only",
        action="store_true",
        help="Show retrieved chunks without LLM generation",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of chunks to retrieve (default: 5)",
    )
    parser.add_argument(
        "--creator",
        type=str,
        default=None,
        help="Filter results by creator name",
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="Filter results by category (e.g. Sandwich, Salad)",
    )
    args = parser.parse_args()

    # ── Validate environment ──────────────────────────────────────────────────
    missing = []
    if not QDRANT_URL:     missing.append("QDRANT_URL")
    if not QDRANT_API_KEY: missing.append("QDRANT_API_KEY")
    if not GOOGLE_API_KEY: missing.append("GOOGLE_API_KEY")
    if missing:
        print(f"[ERROR] Missing environment variables: {', '.join(missing)}")
        sys.exit(1)

    # ── Initialize ────────────────────────────────────────────────────────────
    print("\n[INFO] Initializing... (FastEmbed model may take a moment)")
    try:
        qdrant, gemini, embedder = initialize_clients()
    except Exception as e:
        print(f"[ERROR] Initialization failed: {e}")
        sys.exit(1)

    # ── Check collection ──────────────────────────────────────────────────────
    try:
        info = qdrant.get_collection(COLLECTION_NAME)
        if info.points_count == 0:
            print("[ERROR] Collection is empty — run 03_run_indexing.py --test first.")
            sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Could not access collection '{COLLECTION_NAME}': {e}")
        sys.exit(1)

    # ── Initialize session ────────────────────────────────────────────────────
    session = Session(
        top_k           = args.top_k,
        retrieve_only   = args.retrieve_only,
        creator_filter  = args.creator,
        category_filter = args.category,
    )

    print_header(session, info.points_count)

    # ── Main interaction loop ─────────────────────────────────────────────────
    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n[Interrupted] Saving session trace...")
            break

        if not user_input:
            continue

        # Handle commands
        if user_input.startswith("/"):
            result = handle_command(user_input, session)
            if result is False:
                break
            elif result == "save":
                path = save_trace(session)
                print(f"  [OK] Trace saved: {path}")
            continue

        # ── Run RAG query ─────────────────────────────────────────────────────
        try:
            # Embed and search
            query_vector = embed_query(user_input, embedder)
            results      = search_qdrant(query_vector, qdrant, session)

            # Display chunks
            chunks = display_chunks(results, user_input)

            # Generate answer (unless retrieve-only)
            answer = None
            if not session.retrieve_only:
                print("  [Generating answer...]\n")
                answer = generate_answer(user_input, results, gemini)
                print_answer(answer)

            # Record turn
            session.add_turn(
                query  = user_input,
                chunks = chunks,
                answer = answer,
            )

        except Exception as e:
            import traceback
            print(f"\n  [ERROR] Query failed: {e}\n")
            traceback.print_exc()
            continue

    # ── Save trace on exit ────────────────────────────────────────────────────
    if session.history:
        path = save_trace(session)
        print(f"\n[OK] Session trace saved: {path}")
        print(f"     {len(session.history)} turns recorded.\n")
    else:
        print("\n[INFO] No queries recorded — no trace saved.\n")

    print("Goodbye! Review your traces in traces/ and fill in analysis/data_quality_notes.md\n")


if __name__ == "__main__":
    main()
