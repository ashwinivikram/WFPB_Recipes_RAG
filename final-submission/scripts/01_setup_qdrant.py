"""
01_setup_qdrant.py
------------------
Creates the Qdrant collection for the WFPB Recipe RAG system.
Run this ONCE before any indexing.

Usage:
    python 01_setup_qdrant.py

Author: Ashwini Vikram
Project: WFPB Recipe RAG System
Data Source: Thankful2Plants.com (CC BY-NC-ND 4.0)
"""

import os
import sys
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PayloadSchemaType,
)

#  Load environment variables 
load_dotenv()

QDRANT_URL        = os.getenv("QDRANT_URL")
QDRANT_API_KEY    = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME   = os.getenv("QDRANT_COLLECTION_PHASE1", "WFPB recipes")
EMBEDDING_DIM     = int(os.getenv("EMBEDDING_DIMENSION", "1024"))

#  Validate environment 
def validate_env():
    missing = []
    if not QDRANT_URL:
        missing.append("QDRANT_URL")
    if not QDRANT_API_KEY:
        missing.append("QDRANT_API_KEY")
    if missing:
        print(f"[ERROR] Missing environment variables: {', '.join(missing)}")
        print("        Copy .env.example to .env and fill in your values.")
        sys.exit(1)
    print("[OK] Environment variables loaded.")


#  Connect to Qdrant 
def get_client() -> QdrantClient:
    client = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
    )
    # Verify connection
    client.get_collections()
    print(f"[OK] Connected to Qdrant at {QDRANT_URL}")
    return client


#  Check if collection already exists 
def collection_exists(client: QdrantClient, name: str) -> bool:
    existing = [c.name for c in client.get_collections().collections]
    return name in existing


#  Create collection 
def create_collection(client: QdrantClient):
    """
    Creates the WFPB recipes collection with:
    - Vector config: BAAI/bge-large-en-v1.5 embeddings (1024 dimensions, cosine similarity)
    - Payload indexes: for fast metadata filtering on creator, category, source_pdf
    """

    if collection_exists(client, COLLECTION_NAME):
        print(f"[INFO] Collection '{COLLECTION_NAME}' already exists  skipping creation.")
        print("       To recreate, delete the collection in Qdrant Cloud console first.")
        return

    #  Create the collection with vector config 
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=EMBEDDING_DIM,       # 1024 for BAAI/bge-large-en-v1.5
            distance=Distance.COSINE, # Cosine similarity for semantic search
        ),
    )
    print(f"[OK] Collection '{COLLECTION_NAME}' created.")
    print(f"     Vector size: {EMBEDDING_DIM} | Distance: COSINE")

    #  Create payload indexes for fast metadata filtering 
    # These allow queries like:
    #   "filter by creator = 'Kumar Natarajan'"
    #   "filter by category = 'Sandwich'"
    # Without indexes, Qdrant scans all payloads  slow at 2000+ recipes.

    indexes = [
        ("creator",    PayloadSchemaType.KEYWORD),
        ("category",   PayloadSchemaType.KEYWORD),
        ("subcategory",PayloadSchemaType.KEYWORD),
        ("source_pdf", PayloadSchemaType.KEYWORD),
    ]

    for field_name, field_type in indexes:
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name=field_name,
            field_schema=field_type,
        )
        print(f"[OK] Payload index created: '{field_name}' ({field_type.value})")


#  Verify collection 
def verify_collection(client: QdrantClient):
    """Fetch and display collection info to confirm setup."""
    info = client.get_collection(COLLECTION_NAME)
    print("\n Collection Info ")
    print(f"  Name       : {COLLECTION_NAME}")
    print(f"  Status     : {info.status}")
    print(f"  Vector size: {info.config.params.vectors.size}")
    print(f"  Distance   : {info.config.params.vectors.distance}")
    print(f"  Points     : {info.points_count}")
    print("")


#  Main 
def main():
    print("\n=== 01_setup_qdrant.py  WFPB Recipe RAG Setup ===\n")

    validate_env()

    try:
        client = get_client()
    except Exception as e:
        print(f"[ERROR] Could not connect to Qdrant: {e}")
        print("        Check your QDRANT_URL and QDRANT_API_KEY in .env")
        sys.exit(1)

    try:
        create_collection(client)
        verify_collection(client)
    except Exception as e:
        print(f"[ERROR] Collection setup failed: {e}")
        sys.exit(1)

    print("\n[DONE] Qdrant setup complete.")
    print(f"       Collection '{COLLECTION_NAME}' is ready for indexing.")
    print("       Next step: python 02_create_pipeline.py\n")


if __name__ == "__main__":
    main()
