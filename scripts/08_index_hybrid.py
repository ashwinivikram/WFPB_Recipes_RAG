"""
08_index_hybrid.py
------------------
Week 3 indexing: creates wfpb_recipes_week3_hybrid collection with both
dense (Voyage voyage-3-large, 2048d) and sparse (BM25 via FastEmbed)
vectors for hybrid retrieval.

Reads data/processed/week2_chunks.json (692 chunks from Week 2).
The Week 2 collection (wfpb_recipes_week2) is left untouched so both
can be queried for side-by-side evaluation.

Collection naming:
    Week 2 sub-recipe : wfpb_recipes_week2           (untouched)
    Week 3 hybrid     : wfpb_recipes_week3_hybrid     (created here)

Usage:
    python scripts/08_index_hybrid.py
    python scripts/08_index_hybrid.py --reset   # Delete + recreate collection

Author: Ashwini Vikram
Project: WFPB Recipe RAG System — Week 3
Data Source: Thankful2Plants.com (CC BY-NC-ND 4.0)
"""

import os
import sys
import json
import argparse
import time
from pathlib import Path

import voyageai
from dotenv import load_dotenv
from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    SparseVectorParams,
    SparseVector,
    PointStruct,
    PayloadSchemaType,
)

# ── Load environment ───────────────────────────────────────────────────────────
load_dotenv()

QDRANT_URL      = os.getenv("QDRANT_URL")
QDRANT_API_KEY  = os.getenv("QDRANT_API_KEY")
VOYAGE_API_KEY  = os.getenv("VOYAGE_API_KEY")

VOYAGE_MODEL    = "voyage-3-large"
EMBEDDING_DIM   = 1024
BATCH_SIZE      = 32           # Voyage embed batch size
SPARSE_MODEL    = "Qdrant/bm25"

COLLECTION_NAME = "wfpb_recipes_week3_hybrid"

# ── Paths ──────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
CHUNKS_FILE  = PROJECT_ROOT / "data" / "processed" / "week2_chunks.json"


# ── Environment validation ─────────────────────────────────────────────────────
def validate_env():
    missing = []
    if not QDRANT_URL:     missing.append("QDRANT_URL")
    if not QDRANT_API_KEY: missing.append("QDRANT_API_KEY")
    if not VOYAGE_API_KEY or VOYAGE_API_KEY == "your_voyage_api_key_here":
        missing.append("VOYAGE_API_KEY")
    if missing:
        print(f"[ERROR] Missing or unset environment variables: {', '.join(missing)}")
        if "VOYAGE_API_KEY" in missing:
            print("        Get your key at https://dash.voyageai.com/")
            print("        Add your Voyage key as VOYAGE_API_KEY in your .env file")
        sys.exit(1)
    print("[OK] Environment variables loaded.")


# ── Qdrant helpers ─────────────────────────────────────────────────────────────
def get_qdrant_client() -> QdrantClient:
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    client.get_collections()
    print("[OK] Connected to Qdrant.")
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
        vectors_config={
            "dense": VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        },
        sparse_vectors_config={
            "sparse": SparseVectorParams(),
        },
    )
    print(f"[OK] Collection '{COLLECTION_NAME}' created.")
    print(f"     Dense: {EMBEDDING_DIM}d cosine ({VOYAGE_MODEL})")
    print(f"     Sparse: BM25 ({SPARSE_MODEL})")

    # Payload indexes for fast metadata filtering
    for field, schema in [
        ("creator",    PayloadSchemaType.KEYWORD),
        ("category",   PayloadSchemaType.KEYWORD),
        ("subcategory",PayloadSchemaType.KEYWORD),
        ("source_pdf", PayloadSchemaType.KEYWORD),
        ("chunk_type", PayloadSchemaType.KEYWORD),
    ]:
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name=field,
            field_schema=schema,
        )
    print("[OK] Payload indexes created.")


# ── Embedding ──────────────────────────────────────────────────────────────────
def embed_dense(texts: list[str], vo: voyageai.Client) -> list[list[float]]:
    """Embed texts with Voyage voyage-3-large in batches."""
    all_embeddings = []
    total = len(texts)
    print(f"\n── Dense embeddings ({VOYAGE_MODEL}) for {total} chunks ──")

    for i in range(0, total, BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        result = vo.embed(batch, model=VOYAGE_MODEL, input_type="document")
        all_embeddings.extend(result.embeddings)
        print(f"  [{i + len(batch)}/{total}] dense embedded")
        if i + BATCH_SIZE < total:
            time.sleep(0.5)  # light rate limiting

    return all_embeddings


def embed_sparse(texts: list[str], sparse_model: SparseTextEmbedding) -> list:
    """Generate BM25 sparse vectors for all texts."""
    total = len(texts)
    print(f"\n── Sparse embeddings (BM25) for {total} chunks ──")

    sparse_vecs = []
    for i in range(0, total, BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        vecs = list(sparse_model.embed(batch))
        sparse_vecs.extend(vecs)
        print(f"  [{i + len(vecs)}/{total}] sparse embedded")

    return sparse_vecs


# ── Upsert ─────────────────────────────────────────────────────────────────────
def upsert_chunks(
    client: QdrantClient,
    chunks: list[dict],
    dense_embeddings: list[list[float]],
    sparse_embeddings: list,
) -> int:
    total_upserted = 0

    for i in range(0, len(chunks), BATCH_SIZE):
        batch_chunks   = chunks[i : i + BATCH_SIZE]
        batch_dense    = dense_embeddings[i : i + BATCH_SIZE]
        batch_sparse   = sparse_embeddings[i : i + BATCH_SIZE]
        points = []

        for chunk, dense_vec, sparse_vec in zip(batch_chunks, batch_dense, batch_sparse):
            chunk_id = chunk.get("id") or (
                f"{chunk.get('recipe_name','')}__{chunk.get('creator','')}__{chunk.get('category','')}"
            )
            point_id = abs(hash(chunk_id)) % (2 ** 63)
            payload  = {k: v for k, v in chunk.items() if k != "embedding"}

            points.append(PointStruct(
                id=point_id,
                vector={
                    "dense": dense_vec,
                    "sparse": SparseVector(
                        indices=sparse_vec.indices.tolist(),
                        values=sparse_vec.values.tolist(),
                    ),
                },
                payload=payload,
            ))

        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points,
            wait=True,
        )
        total_upserted += len(batch_chunks)
        print(f"  [Upsert] {total_upserted}/{len(chunks)} points")

    return total_upserted


# ── Summary ────────────────────────────────────────────────────────────────────
def print_summary(client: QdrantClient, n_chunks: int, n_upserted: int, elapsed: float):
    try:
        info = client.get_collection(COLLECTION_NAME)
        final_count = info.points_count
    except Exception:
        final_count = "unknown"

    mins = int(elapsed // 60)
    secs = int(elapsed % 60)

    print("\n══ Week 3 Hybrid Indexing Summary ═══════════════════")
    print(f"  Collection   : {COLLECTION_NAME}")
    print(f"  Dense model  : {VOYAGE_MODEL} ({EMBEDDING_DIM}d)")
    print(f"  Sparse model : {SPARSE_MODEL} (BM25)")
    print(f"  Chunks       : {n_chunks}")
    print(f"  Points upserted : {n_upserted}")
    print(f"  Points in Qdrant: {final_count}")
    print(f"  Time elapsed : {mins}m {secs}s")
    print("══════════════════════════════════════════════════════")
    print("\n[DONE] Week 3 hybrid index ready.")
    print("       Query: python scripts/09_rag_with_rerank.py")
    print("       Eval:  python scripts/10_evaluate_week3.py\n")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Index Week 3 hybrid chunks into Qdrant")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete and recreate the collection before indexing",
    )
    args = parser.parse_args()

    print(f"\n=== 08_index_hybrid.py — Week 3 Hybrid Indexing ===\n")
    print(f"  Collection   : {COLLECTION_NAME}")
    print(f"  Dense model  : {VOYAGE_MODEL} ({EMBEDDING_DIM}d)")
    print(f"  Sparse model : {SPARSE_MODEL}")
    print(f"  Chunks file  : {CHUNKS_FILE}\n")

    validate_env()
    start = time.time()

    # ── Load chunks ───────────────────────────────────────────────────────────
    if not CHUNKS_FILE.exists():
        print(f"[ERROR] Chunks file not found: {CHUNKS_FILE}")
        print("        Run script 06 first:  python scripts/06_chunk_with_strategy.py")
        sys.exit(1)

    print(f"── Loading chunks from {CHUNKS_FILE.name} ──")
    with open(CHUNKS_FILE, encoding="utf-8") as f:
        chunks = json.load(f)

    for c in chunks:
        c.pop("embedding", None)
        c.pop("needs_embedding", None)

    n_splits = sum(1 for c in chunks if c.get("chunk_type") in ("sub", "component", "assembly"))
    print(f"  Loaded {len(chunks)} chunks ({n_splits} sub-recipe chunks from Week 2 splits).")

    # ── Connect and set up collection ─────────────────────────────────────────
    print("\n── Connecting to Qdrant ──")
    client = get_qdrant_client()
    create_collection(client, reset=args.reset)

    if not args.reset and collection_exists(client):
        info = client.get_collection(COLLECTION_NAME)
        if info.points_count > 0:
            print(f"\n[INFO] Collection already has {info.points_count} points.")
            print("       Use --reset to reindex from scratch.")
            sys.exit(0)

    # ── Embed dense ───────────────────────────────────────────────────────────
    print(f"\n── Initialising Voyage client ({VOYAGE_MODEL}) ──")
    vo = voyageai.Client(api_key=VOYAGE_API_KEY)
    print("[OK] Voyage client ready.")

    texts = [c["text"] for c in chunks]
    dense_embeddings = embed_dense(texts, vo)

    # ── Embed sparse ──────────────────────────────────────────────────────────
    print(f"\n── Initialising sparse embedder ({SPARSE_MODEL}) ──")
    sparse_model = SparseTextEmbedding(SPARSE_MODEL)
    print("[OK] Sparse embedder ready.")

    sparse_embeddings = embed_sparse(texts, sparse_model)

    # ── Upsert ────────────────────────────────────────────────────────────────
    print(f"\n── Upserting {len(chunks)} chunks to '{COLLECTION_NAME}' ──")
    n_upserted = upsert_chunks(client, chunks, dense_embeddings, sparse_embeddings)

    print_summary(client, len(chunks), n_upserted, time.time() - start)


if __name__ == "__main__":
    main()
