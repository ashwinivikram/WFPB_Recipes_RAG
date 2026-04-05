"""
07_index_with_strategy.py
-------------------------
Week 2 indexing: creates a new Qdrant collection and indexes the Week 2 chunks.

Reads week2_chunks.json produced by 06_chunk_with_strategy.py,
generates embeddings for any chunks that need them, and upserts
everything into the wfpb_recipes_week2 collection.

The Week 1 naive collection (mcp_phase1_baseline) is left untouched
so that both can be queried for side-by-side evaluation in Week 2.

Collection naming:
    Week 1 naive : mcp_phase1_baseline         (untouched)
    Week 2 Week2 : wfpb_recipes_week2          (created here)

Usage:
    python scripts/07_index_with_strategy.py
    python scripts/07_index_with_strategy.py --reset   # Delete + recreate collection

Author: Ashwini Vikram
Project: WFPB Recipe RAG System — Week 2
Data Source: Thankful2Plants.com (CC BY-NC-ND 4.0)
"""

import os
import sys
import json
import argparse
import time
from pathlib import Path

from dotenv import load_dotenv
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    PayloadSchemaType,
)

# ── Load environment ──────────────────────────────────────────────────────────
load_dotenv()

QDRANT_URL      = os.getenv("QDRANT_URL")
QDRANT_API_KEY  = os.getenv("QDRANT_API_KEY")
GOOGLE_API_KEY  = os.getenv("GOOGLE_API_KEY")
FASTEMBED_MODEL = os.getenv("FASTEMBED_MODEL", "BAAI/bge-large-en-v1.5")
EMBEDDING_DIM   = int(os.getenv("EMBEDDING_DIMENSION", "1024"))
BATCH_SIZE      = int(os.getenv("FASTEMBED_BATCH_SIZE", "32"))

COLLECTION_NAME = "wfpb_recipes_week2"   # Week 2 collection — separate from Week 1 naive

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
CHUNKS_FILE  = PROJECT_ROOT / "data" / "processed" / "week2_chunks.json"


# ── Environment validation ────────────────────────────────────────────────────
def validate_env():
    missing = []
    if not QDRANT_URL:     missing.append("QDRANT_URL")
    if not QDRANT_API_KEY: missing.append("QDRANT_API_KEY")
    if missing:
        print(f"[ERROR] Missing environment variables: {', '.join(missing)}")
        sys.exit(1)
    print("[OK] Environment variables loaded.")


# ── Qdrant helpers ────────────────────────────────────────────────────────────
def get_qdrant_client() -> QdrantClient:
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    client.get_collections()
    print(f"[OK] Connected to Qdrant.")
    return client


def collection_exists(client: QdrantClient) -> bool:
    return COLLECTION_NAME in [c.name for c in client.get_collections().collections]


def create_collection(client: QdrantClient, reset: bool = False):
    if collection_exists(client):
        if reset:
            client.delete_collection(COLLECTION_NAME)
            print(f"[OK] Deleted existing collection '{COLLECTION_NAME}'.")
        else:
            print(f"[INFO] Collection '{COLLECTION_NAME}' already exists.")
            print("       Use --reset to delete and recreate it.")
            return

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=EMBEDDING_DIM,
            distance=Distance.COSINE,
        ),
    )
    print(f"[OK] Collection '{COLLECTION_NAME}' created. ({EMBEDDING_DIM}d cosine)")

    # Payload indexes for fast metadata filtering — same as Week 1 collection
    for field, schema in [
        ("creator",    PayloadSchemaType.KEYWORD),
        ("category",   PayloadSchemaType.KEYWORD),
        ("subcategory",PayloadSchemaType.KEYWORD),
        ("source_pdf", PayloadSchemaType.KEYWORD),
        ("chunk_type", PayloadSchemaType.KEYWORD),  # Week 2: filter by "main"/"sub"
    ]:
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name=field,
            field_schema=schema,
        )
    print("[OK] Payload indexes created.")


# ── Embedding ─────────────────────────────────────────────────────────────────
def embed_chunks(chunks: list[dict], embedder: TextEmbedding) -> list[dict]:
    """
    Generate embeddings for chunks that need them.

    Chunks produced by splitting have embedding=None (text changed).
    Chunks passed through unchanged can reuse their Week 1 embedding.

    For the Week 2 collection we regenerate ALL embeddings to ensure
    consistency (the embedder is the same model, so results are identical
    for unchanged chunks, but this avoids any stale-embedding edge cases).
    """
    texts  = [c["text"] for c in chunks]
    total  = len(texts)
    print(f"\n── Generating embeddings for {total} chunks ──")

    embeddings = []
    for i in range(0, total, BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        vecs  = list(embedder.embed(batch))
        embeddings.extend([v.tolist() for v in vecs])
        print(f"  [{i + len(batch)}/{total}] embedded")

    for chunk, vec in zip(chunks, embeddings):
        chunk["embedding"] = vec

    return chunks


# ── Upsert ────────────────────────────────────────────────────────────────────
def upsert_chunks(client: QdrantClient, chunks: list[dict]) -> int:
    total_upserted = 0

    for i in range(0, len(chunks), BATCH_SIZE):
        batch  = chunks[i : i + BATCH_SIZE]
        points = []

        for chunk in batch:
            # Chat entries don't have an id field — derive one from content
            chunk_id = chunk.get("id") or (
                f"{chunk.get('recipe_name','')}__{chunk.get('creator','')}__{chunk.get('category','')}"
            )
            point_id = abs(hash(chunk_id)) % (2 ** 63)
            payload  = {k: v for k, v in chunk.items() if k != "embedding"}
            points.append(PointStruct(
                id      = point_id,
                vector  = chunk["embedding"],
                payload = payload,
            ))

        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points,
            wait=True,
        )
        total_upserted += len(batch)
        print(f"  [Upsert] {total_upserted}/{len(chunks)} points")

    return total_upserted


# ── Summary ───────────────────────────────────────────────────────────────────
def print_summary(client: QdrantClient, n_input: int, n_upserted: int,
                  n_splits: int, elapsed: float):
    try:
        info = client.get_collection(COLLECTION_NAME)
        final_count = info.points_count
    except Exception:
        final_count = "unknown"

    mins = int(elapsed // 60)
    secs = int(elapsed % 60)

    print("\n══ Week 2 Indexing Summary ═══════════════════════════")
    print(f"  Collection       : {COLLECTION_NAME}")
    print(f"  Input chunks     : {n_input}  (Week 1 naive baseline)")
    print(f"  Recipe cards split: {n_splits} cards → {n_splits * 2} focused chunks")
    print(f"  Points upserted  : {n_upserted}")
    print(f"  Points in Qdrant : {final_count}")
    print(f"  Time elapsed     : {mins}m {secs}s")
    print("══════════════════════════════════════════════════════")
    print("\n[DONE] Week 2 index ready.")
    print("       Run evaluation: python scripts/08_evaluate_chunking.py")
    print("       Or query interactively — set QDRANT_COLLECTION_PHASE1=wfpb_recipes_week2")
    print("       in your .env and run python scripts/05_interactive_rag.py\n")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Index Week 2 chunks into Qdrant")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete and recreate the Week 2 collection before indexing",
    )
    args = parser.parse_args()

    print(f"\n=== 07_index_with_strategy.py — Week 2 Indexing ===\n")
    print(f"  Collection : {COLLECTION_NAME}")
    print(f"  Embedder   : {FASTEMBED_MODEL} ({EMBEDDING_DIM}d)")
    print(f"  Chunks file: {CHUNKS_FILE}\n")

    validate_env()
    start = time.time()

    # ── Load chunks produced by script 06 ────────────────────────────────────
    if not CHUNKS_FILE.exists():
        print(f"[ERROR] Chunks file not found: {CHUNKS_FILE}")
        print("        Run script 06 first:  python scripts/06_chunk_with_strategy.py")
        sys.exit(1)

    print(f"── Loading chunks from {CHUNKS_FILE.name} ──")
    with open(CHUNKS_FILE, encoding="utf-8") as f:
        raw = json.load(f)

    chunks = []
    for c in raw:
        c["embedding"] = None   # Will be (re)generated below
        c.pop("needs_embedding", None)
        chunks.append(c)

    n_splits = sum(1 for c in chunks if c.get("chunk_type") == "sub")
    print(f"  Loaded {len(chunks)} chunks ({n_splits} sub-recipe chunks from splits).")

    n_input = len(chunks)

    # ── Connect and set up collection ─────────────────────────────────────────
    print("\n── Connecting to Qdrant ──")
    client = get_qdrant_client()
    create_collection(client, reset=args.reset)

    if not args.reset and collection_exists(client):
        info = client.get_collection(COLLECTION_NAME)
        if info.points_count > 0 and not args.reset:
            print(f"\n[INFO] Collection already has {info.points_count} points.")
            print("       Use --reset to reindex from scratch.")
            sys.exit(0)

    # ── Embed ─────────────────────────────────────────────────────────────────
    print(f"\n── Initialising embedder: {FASTEMBED_MODEL} ──")
    embedder = TextEmbedding(model_name=FASTEMBED_MODEL)
    print("[OK] Embedder ready.")

    chunks = embed_chunks(chunks, embedder)

    # ── Upsert ────────────────────────────────────────────────────────────────
    print(f"\n── Upserting {len(chunks)} chunks to '{COLLECTION_NAME}' ──")
    n_upserted = upsert_chunks(client, chunks)

    print_summary(client, n_input, n_upserted, n_splits, time.time() - start)


if __name__ == "__main__":
    main()
