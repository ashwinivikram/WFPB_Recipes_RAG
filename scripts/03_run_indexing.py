"""
03_run_indexing.py
------------------
Indexes WFPB recipe cards into Qdrant.

Reads processed JSON files from data/processed/, generates embeddings
using BAAI/bge-large-en-v1.5, and upserts vectors + metadata into Qdrant.

Must run 01_setup_qdrant.py and 02_create_pipeline.py first.

Usage:
    python 03_run_indexing.py --test     # Index Week 1 PDFs (3 files)
    python 03_run_indexing.py --full     # Index all 22 PDFs
    python 03_run_indexing.py --pdf <filename>  # Index one specific PDF

Author: Ashwini Vikram
Project: WFPB Recipe RAG System
Data Source: Thankful2Plants.com (CC BY-NC-ND 4.0)
"""

import os
import sys
import json
import argparse
import time
from pathlib import Path
from datetime import datetime

import fitz                          # PyMuPDF
from google import genai             # Gemini Vision
from fastembed import TextEmbedding  # BAAI/bge-large-en-v1.5
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from dotenv import load_dotenv

# ── Import pipeline functions from 02_create_pipeline.py ─────────────────────
# We reuse extraction and embedding logic — no duplication
sys.path.insert(0, str(Path(__file__).parent))
from create_pipeline_02 import (
    extract_images_from_pdf,
    extract_recipe_from_image,
    build_embedding_text,
    embed_text,
    save_processed_recipe,
    validate_extraction,
    EXTRACTION_PROMPT,
)

# ── Load environment variables ────────────────────────────────────────────────
load_dotenv()

QDRANT_URL       = os.getenv("QDRANT_URL")
QDRANT_API_KEY   = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME  = os.getenv("QDRANT_COLLECTION_PHASE1", "WFPB recipes")
GOOGLE_API_KEY   = os.getenv("GOOGLE_API_KEY")
FASTEMBED_MODEL  = os.getenv("FASTEMBED_MODEL", "BAAI/bge-large-en-v1.5")
EMBEDDING_DIM    = int(os.getenv("EMBEDDING_DIMENSION", "1024"))
BATCH_SIZE       = int(os.getenv("FASTEMBED_BATCH_SIZE", "32"))

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT   = Path(__file__).parent.parent
DATA_RAW       = PROJECT_ROOT / "data" / "raw"
DATA_IMAGES    = PROJECT_ROOT / "data" / "raw" / "images"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"

# ── Week 1 test PDFs ──────────────────────────────────────────────────────────
# These 3 PDFs are used for --test mode (Week 1 baseline)
TEST_PDFS = [
    "Sandwiches___Pita_Pockets___Whole_Food_Plant-Based.pdf",
    "Salads___Whole_Food_Plant-Based.pdf",
    "Sweet_Porridge__Beyond_Oatmeal____Whole_Food_Plant-Based.pdf",
]


# ── Validate environment ──────────────────────────────────────────────────────
def validate_env():
    missing = []
    if not QDRANT_URL:     missing.append("QDRANT_URL")
    if not QDRANT_API_KEY: missing.append("QDRANT_API_KEY")
    if not GOOGLE_API_KEY: missing.append("GOOGLE_API_KEY")
    if missing:
        print(f"[ERROR] Missing environment variables: {', '.join(missing)}")
        sys.exit(1)
    print("[OK] Environment variables loaded.")


# ── Qdrant client ─────────────────────────────────────────────────────────────
def get_qdrant_client() -> QdrantClient:
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    client.get_collections()  # verify connection
    print(f"[OK] Connected to Qdrant — collection: '{COLLECTION_NAME}'")
    return client


# ── Check already-indexed pages ───────────────────────────────────────────────
def get_indexed_ids(client: QdrantClient) -> set[str]:
    """
    Retrieve all point IDs already in the collection.
    Used to skip pages that were successfully indexed in a previous run.
    Makes the indexing process resumable if interrupted.
    """
    indexed = set()
    offset  = None

    while True:
        result, next_offset = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=100,
            offset=offset,
            with_payload=["id"],
            with_vectors=False,
        )
        for point in result:
            if point.payload and "id" in point.payload:
                indexed.add(point.payload["id"])
        if next_offset is None:
            break
        offset = next_offset

    return indexed


# ── Process single PDF ────────────────────────────────────────────────────────
def process_pdf(
    pdf_path: Path,
    gemini_model,
    embed_model: TextEmbedding,
    indexed_ids: set[str],
) -> list[dict]:
    """
    Run the full extraction pipeline on one PDF.
    Returns list of recipe dicts ready for Qdrant upsert.

    Skips pages already indexed (resumable runs).
    Skips pages where extraction finds no recipe name (cover pages, TOC, etc).
    """
    pdf_stem   = pdf_path.stem
    image_dir  = DATA_IMAGES / pdf_stem
    processed_dir = DATA_PROCESSED / pdf_stem

    print(f"\n── Processing: {pdf_path.name} ──")

    # ── Stage 1: Extract images ───────────────────────────────────────────────
    # Check if images already extracted (skip re-extraction)
    if image_dir.exists() and any(image_dir.glob("*.png")):
        image_paths = sorted(image_dir.glob("*.png"))
        print(f"  [Extract] Found {len(image_paths)} existing images — skipping re-extraction")
    else:
        image_paths = extract_images_from_pdf(pdf_path, image_dir)

    recipes  = []
    skipped  = 0
    errors   = 0

    for image_path in image_paths:
        page_num  = int(image_path.stem.split("_")[-1])
        recipe_id = f"{pdf_stem}_page_{page_num:03d}"

        # Skip if already indexed
        if recipe_id in indexed_ids:
            skipped += 1
            continue

        # Check if already processed (JSON exists) — skip Gemini call
        json_path = processed_dir / f"recipe_{page_num:03d}.json"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                recipe = json.load(f)
            print(f"  [Load] page {page_num:03d} — loaded from processed JSON")
        else:
            # ── Stage 2: Gemini Vision extraction ────────────────────────────
            try:
                recipe = extract_recipe_from_image(
                    image_path=image_path,
                    model=gemini_model,
                    pdf_name=pdf_path.name,
                    page_number=page_num,
                )
                save_processed_recipe(recipe, processed_dir)

                # Rate limiting — Gemini free tier: 15 requests/minute
                time.sleep(1)

            except Exception as e:
                print(f"  [ERROR] page {page_num:03d} — Gemini extraction failed: {e}")
                errors += 1
                continue

        # Skip non-recipe pages (cover, TOC, section dividers)
        warnings = validate_extraction(recipe)
        if "Missing recipe_name" in " ".join(warnings):
            print(f"  [SKIP] page {page_num:03d} — no recipe found (likely cover/TOC page)")
            skipped += 1
            continue

        # ── Stage 3: Generate embedding ───────────────────────────────────────
        if "embedding" not in recipe:
            recipe["embedding"] = embed_text(recipe["text"], embed_model)
            # Save updated JSON with embedding
            save_processed_recipe(recipe, processed_dir)

        recipes.append(recipe)
        print(f"  [OK] page {page_num:03d} — '{recipe.get('recipe_name', 'Unknown')}' by {recipe.get('creator', 'Unknown')}")

    print(f"\n  Summary: {len(recipes)} recipes | {skipped} skipped | {errors} errors")
    return recipes


# ── Upsert to Qdrant ──────────────────────────────────────────────────────────
def upsert_to_qdrant(
    client: QdrantClient,
    recipes: list[dict],
    batch_size: int = BATCH_SIZE,
) -> int:
    """
    Upsert recipe vectors and metadata into Qdrant in batches.

    Each point contains:
    - id:      Numeric hash of recipe_id string (Qdrant requires int or UUID)
    - vector:  1024-dim embedding of the recipe text
    - payload: All recipe metadata for filtering and display

    Returns count of successfully upserted points.
    """
    if not recipes:
        print("  [INFO] No recipes to upsert.")
        return 0

    total_upserted = 0

    # Process in batches
    for i in range(0, len(recipes), batch_size):
        batch   = recipes[i : i + batch_size]
        points  = []

        for recipe in batch:
            # Qdrant point ID must be unsigned integer or UUID
            # Use hash of the string ID for deterministic, collision-resistant IDs
            point_id = abs(hash(recipe["id"])) % (2**63)

            # Payload — everything except the raw embedding vector
            payload = {k: v for k, v in recipe.items() if k != "embedding"}

            points.append(PointStruct(
                id      = point_id,
                vector  = recipe["embedding"],
                payload = payload,
            ))

        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points,
            wait=True,  # Wait for confirmation before continuing
        )

        total_upserted += len(batch)
        print(f"  [Upsert] Batch {i // batch_size + 1}: {len(batch)} points upserted "
              f"({total_upserted}/{len(recipes)} total)")

    return total_upserted


# ── Print indexing summary ────────────────────────────────────────────────────
def print_summary(
    pdfs_processed: list[str],
    total_recipes: int,
    total_upserted: int,
    start_time: float,
):
    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    collection_info = None
    try:
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        collection_info = client.get_collection(COLLECTION_NAME)
    except Exception:
        pass

    print("\n══ Indexing Summary ══════════════════════════════════")
    print(f"  PDFs processed : {len(pdfs_processed)}")
    for pdf in pdfs_processed:
        print(f"    • {pdf}")
    print(f"  Recipes found  : {total_recipes}")
    print(f"  Points upserted: {total_upserted}")
    if collection_info:
        print(f"  Collection total: {collection_info.points_count} points in Qdrant")
    print(f"  Time elapsed   : {minutes}m {seconds}s")
    print("══════════════════════════════════════════════════════")
    print("\n[DONE] Indexing complete.")
    print("       Next step: python 04_test_rag_system.py\n")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("\n=== 03_run_indexing.py — WFPB Recipe Indexing ===\n")

    # ── Parse arguments ───────────────────────────────────────────────────────
    parser = argparse.ArgumentParser(description="Index WFPB recipes into Qdrant")
    group  = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--test",
        action="store_true",
        help="Index Week 1 test PDFs only (3 files)",
    )
    group.add_argument(
        "--full",
        action="store_true",
        help="Index all PDFs in data/raw/",
    )
    group.add_argument(
        "--pdf",
        type=str,
        help="Index a single PDF by filename",
    )
    args = parser.parse_args()

    # ── Validate environment ──────────────────────────────────────────────────
    validate_env()
    start_time = time.time()

    # ── Determine which PDFs to process ──────────────────────────────────────
    if args.test:
        print("[MODE] --test: Indexing Week 1 PDFs (3 files)\n")
        pdf_paths = []
        for filename in TEST_PDFS:
            path = DATA_RAW / filename
            if path.exists():
                pdf_paths.append(path)
            else:
                print(f"  [WARN] Not found: {filename} — skipping")

    elif args.full:
        print("[MODE] --full: Indexing all PDFs in data/raw/\n")
        pdf_paths = sorted(DATA_RAW.glob("*.pdf"))
        if not pdf_paths:
            print(f"[ERROR] No PDFs found in {DATA_RAW}")
            sys.exit(1)
        print(f"  Found {len(pdf_paths)} PDFs:")
        for p in pdf_paths:
            print(f"    • {p.name}")

    else:  # --pdf
        pdf_path = DATA_RAW / args.pdf
        if not pdf_path.exists():
            print(f"[ERROR] PDF not found: {pdf_path}")
            sys.exit(1)
        pdf_paths = [pdf_path]
        print(f"[MODE] --pdf: Indexing {args.pdf}\n")

    if not pdf_paths:
        print("[ERROR] No valid PDFs to process.")
        sys.exit(1)

    # ── Ensure output directories exist ──────────────────────────────────────
    DATA_IMAGES.mkdir(parents=True, exist_ok=True)
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    # ── Initialize clients and models ─────────────────────────────────────────
    print("\n── Initializing clients ──────────────────────────────")
    qdrant_client = get_qdrant_client()

    gemini_model  = genai.Client(api_key=GOOGLE_API_KEY)
    print("[OK] Gemini Vision model ready.")

    embed_model   = TextEmbedding(model_name=FASTEMBED_MODEL)
    print(f"[OK] FastEmbed model ready: {FASTEMBED_MODEL}")

    # ── Get already-indexed IDs (for resumable runs) ──────────────────────────
    print("\n── Checking existing index ───────────────────────────")
    indexed_ids = get_indexed_ids(qdrant_client)
    print(f"  Already indexed: {len(indexed_ids)} points")

    # ── Process each PDF ──────────────────────────────────────────────────────
    all_recipes      = []
    pdfs_processed   = []

    for pdf_path in pdf_paths:
        recipes = process_pdf(
            pdf_path     = pdf_path,
            gemini_model = gemini_model,
            embed_model  = embed_model,
            indexed_ids  = indexed_ids,
        )
        all_recipes.extend(recipes)
        pdfs_processed.append(pdf_path.name)

    # ── Upsert all recipes to Qdrant ──────────────────────────────────────────
    print(f"\n── Upserting {len(all_recipes)} recipes to Qdrant ────")
    total_upserted = upsert_to_qdrant(qdrant_client, all_recipes)

    # ── Print summary ─────────────────────────────────────────────────────────
    print_summary(
        pdfs_processed = pdfs_processed,
        total_recipes  = len(all_recipes),
        total_upserted = total_upserted,
        start_time     = start_time,
    )


if __name__ == "__main__":
    main()
