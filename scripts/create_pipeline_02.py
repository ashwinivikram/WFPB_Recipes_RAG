"""
02_create_pipeline.py
---------------------
Builds and validates the WFPB Recipe RAG indexing pipeline.

Pipeline stages:
    1. Extract  — PDF pages → PNG images (PyMuPDF)
    2. Transform — PNG images → structured JSON (Gemini Vision API)
    3. Embed    — JSON text → vectors (BAAI/bge-large-en-v1.5 via FastEmbed)
    4. Validate — Spot-check extraction and embedding quality

Run this BEFORE 03_run_indexing.py to confirm the pipeline works
on a single document before processing all PDFs.

Usage:
    python 02_create_pipeline.py                    # Validate on 1 page
    python 02_create_pipeline.py --pdf <filename>   # Validate on specific PDF

Author: Ashwini Vikram
Project: WFPB Recipe RAG System
Data Source: Thankful2Plants.com (CC BY-NC-ND 4.0)
"""

import os
import sys
import json
import base64
import argparse
from pathlib import Path
from datetime import datetime

import fitz                         # PyMuPDF
from google import genai            # Gemini Vision
from google.genai import types as genai_types
from fastembed import TextEmbedding # BAAI/bge-large-en-v1.5
from dotenv import load_dotenv

# ── Load environment variables ────────────────────────────────────────────────
load_dotenv()

GOOGLE_API_KEY   = os.getenv("GOOGLE_API_KEY")
FASTEMBED_MODEL  = os.getenv("FASTEMBED_MODEL", "BAAI/bge-large-en-v1.5")
EMBEDDING_DIM    = int(os.getenv("EMBEDDING_DIMENSION", "1024"))
BATCH_SIZE       = int(os.getenv("FASTEMBED_BATCH_SIZE", "32"))

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT   = Path(__file__).parent.parent
DATA_RAW       = PROJECT_ROOT / "data" / "raw"
DATA_IMAGES    = PROJECT_ROOT / "data" / "raw" / "images"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DPI            = 200  # Resolution for PDF → image conversion


# ── Gemini Vision extraction prompt ───────────────────────────────────────────
EXTRACTION_PROMPT = """
You are extracting recipe information from a Whole Food Plant-Based (WFPB) recipe card image.
The recipe card is from Thankful2Plants.com by Gurmeet Manku.

Extract all visible information and return ONLY a valid JSON object with this exact structure.
Do not include any text before or after the JSON.

{
  "recipe_name": "Full name of the recipe as shown on the card",
  "creator": "Name of the recipe creator as shown on the card",
  "category": "Primary category (e.g. Sandwich, Salad, Pita Pocket, Lavash Wrap, Kathi Roll, Stuffed Paratha, Porridge)",
  "subcategory": "More specific type if shown (e.g. Ezekiel Sandwich, Open Sandwich)",
  "ingredients": {
    "whole_grains": [],
    "beans_legumes": [],
    "leafy_greens": [],
    "rainbow_veggies": [],
    "mushrooms": [],
    "nuts_seeds_avocados": [],
    "fruits": [],
    "berries": [],
    "tubers": [],
    "herbs_spices": [],
    "lime_lemon_vinegar": [],
    "sweeteners": []
  },
  "all_ingredients_flat": "Comma-separated list of ALL ingredients for easy search",
  "instructions": "Full cooking instructions exactly as shown on the card",
  "cooking_methods": ["list", "of", "methods", "e.g.", "bake", "saute", "no-cook", "blend"],
  "serving_suggestion": "Any serving notes or suggestions",
  "notes": "Any additional notes, tips, or sub-recipe names mentioned"
}

Important rules:
- If a field is not visible on the card, use an empty string "" or empty list []
- Extract creator name EXACTLY as shown (e.g. 'Dr Sirisha Potluri', 'Kumar Natarajan')
- Extract ALL ingredients even if they appear in sub-recipes on the same card
- For cooking_methods, use simple verbs: bake, saute, blend, no-cook, air-fry, grill, boil, roast
- Return ONLY the JSON object, no markdown, no explanation
"""


# ── Stage 1: PDF → Images ─────────────────────────────────────────────────────
def extract_images_from_pdf(pdf_path: Path, output_dir: Path, dpi: int = DPI) -> list[Path]:
    """
    Extract each page of a PDF as a PNG image.

    Args:
        pdf_path:   Path to the source PDF file
        output_dir: Directory to save extracted images
        dpi:        Resolution (200 DPI balances quality and file size)

    Returns:
        List of paths to extracted PNG images
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    image_paths = []

    doc = fitz.open(pdf_path)
    print(f"  [Extract] {pdf_path.name} — {len(doc)} pages")

    for page_num in range(len(doc)):
        page = doc[page_num]
        # Create a matrix for the desired DPI (72 DPI is PDF default)
        zoom = dpi / 72
        matrix = fitz.Matrix(zoom, zoom)
        pixmap = page.get_pixmap(matrix=matrix)

        image_filename = f"page_{page_num + 1:03d}.png"
        image_path = output_dir / image_filename
        pixmap.save(str(image_path))
        image_paths.append(image_path)

    doc.close()
    print(f"  [Extract] Saved {len(image_paths)} images to {output_dir}")
    return image_paths


# ── Stage 2: Image → Structured JSON (Gemini Vision) ─────────────────────────
def extract_recipe_from_image(
    image_path: Path,
    model,
    pdf_name: str,
    page_number: int,
) -> dict:
    """
    Send a recipe card image to Gemini Vision and extract structured recipe data.

    Args:
        image_path:  Path to the PNG image of the recipe card
        model:       Initialized Gemini GenerativeModel
        pdf_name:    Source PDF filename (for metadata)
        page_number: Page number within the PDF (for metadata)

    Returns:
        Structured recipe dict ready for embedding and indexing
    """
    # Read image and encode as base64
    with open(image_path, "rb") as f:
        image_data = f.read()

    image_part = {
        "mime_type": "image/png",
        "data": base64.b64encode(image_data).decode("utf-8"),
    }

    # Call Gemini Vision
    response = model.models.generate_content(
        model="gemini-2.5-flash",
        contents=[EXTRACTION_PROMPT, image_part],
        config=genai_types.GenerateContentConfig(temperature=0),  # Deterministic extraction
    )

    # Parse JSON response
    raw_text = response.text.strip()

    # Strip markdown code fences if Gemini wraps the JSON
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        raw_text = "\n".join(lines[1:-1])

    recipe_data = json.loads(raw_text)

    # ── Enrich with metadata ──────────────────────────────────────────────────
    pdf_stem = Path(pdf_name).stem
    recipe_id = f"{pdf_stem}_page_{page_number:03d}"

    recipe_data["id"]             = recipe_id
    recipe_data["source_pdf"]     = pdf_name
    recipe_data["page_number"]    = page_number
    recipe_data["source_url"]     = "https://thankful2plants.com"
    recipe_data["attribution"]    = "Thankful2Plants.com by Gurmeet Manku (CC BY-NC-ND 4.0)"
    recipe_data["extraction_date"] = datetime.now().strftime("%Y-%m-%d")
    recipe_data["image_path"]     = str(image_path)

    # ── Build the text field used for embedding ───────────────────────────────
    # This is what gets embedded — combine recipe name, creator,
    # all ingredients, and instructions into one searchable text block
    recipe_data["text"] = build_embedding_text(recipe_data)

    return recipe_data


def build_embedding_text(recipe: dict) -> str:
    """
    Construct the text string that will be embedded as a vector.

    Design decision: include recipe name, creator, all ingredients,
    and instructions. This gives the embedding model the full semantic
    context of the recipe, enabling ingredient queries, creator queries,
    and strategy queries all from the same vector.
    """
    parts = []

    if recipe.get("recipe_name"):
        parts.append(f"Recipe: {recipe['recipe_name']}")

    if recipe.get("creator"):
        parts.append(f"Creator: {recipe['creator']}")

    if recipe.get("category"):
        parts.append(f"Category: {recipe['category']}")

    if recipe.get("all_ingredients_flat"):
        parts.append(f"Ingredients: {recipe['all_ingredients_flat']}")

    if recipe.get("cooking_methods"):
        methods = ", ".join(recipe["cooking_methods"])
        parts.append(f"Cooking methods: {methods}")

    if recipe.get("instructions"):
        parts.append(f"Instructions: {recipe['instructions']}")

    if recipe.get("notes"):
        parts.append(f"Notes: {recipe['notes']}")

    return "\n".join(parts)


# ── Stage 3: Text → Embeddings (FastEmbed) ────────────────────────────────────
def create_embedding_model() -> TextEmbedding:
    """
    Initialize the FastEmbed embedding model.
    BAAI/bge-large-en-v1.5 produces 1024-dimensional vectors.
    First run will download the model (~1.2GB) — subsequent runs use cache.
    """
    print(f"  [Embed] Loading model: {FASTEMBED_MODEL}")
    model = TextEmbedding(model_name=FASTEMBED_MODEL)
    print(f"  [Embed] Model loaded. Embedding dimension: {EMBEDDING_DIM}")
    return model


def embed_text(text: str, model: TextEmbedding) -> list[float]:
    """
    Generate a single embedding vector for a text string.

    Args:
        text:  The text to embed (output of build_embedding_text)
        model: Initialized FastEmbed TextEmbedding model

    Returns:
        List of floats (length = EMBEDDING_DIM = 1024)
    """
    embeddings = list(model.embed([text]))
    return embeddings[0].tolist()


# ── Save processed recipe ─────────────────────────────────────────────────────
def save_processed_recipe(recipe: dict, output_dir: Path):
    """
    Save extracted and enriched recipe JSON to data/processed/.
    This is the checkpoint between extraction and indexing.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"recipe_{recipe['page_number']:03d}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(recipe, f, indent=2, ensure_ascii=False)

    return output_path


# ── Validation ────────────────────────────────────────────────────────────────
def validate_extraction(recipe: dict) -> list[str]:
    """
    Check extracted recipe for common quality issues.
    Returns a list of warning strings (empty = all good).
    """
    warnings = []

    if not recipe.get("recipe_name"):
        warnings.append("Missing recipe_name — may be a non-recipe page (cover, TOC)")

    if not recipe.get("creator"):
        warnings.append("Missing creator name")

    if not recipe.get("all_ingredients_flat"):
        warnings.append("No ingredients extracted — check image quality")

    if not recipe.get("instructions"):
        warnings.append("No instructions extracted — card may be image-only")

    text_len = len(recipe.get("text", ""))
    if text_len < 50:
        warnings.append(f"Very short embedding text ({text_len} chars) — extraction may have failed")

    return warnings


def validate_embedding(embedding: list[float]) -> list[str]:
    """Check embedding vector for obvious issues."""
    warnings = []

    if len(embedding) != EMBEDDING_DIM:
        warnings.append(f"Wrong embedding dimension: got {len(embedding)}, expected {EMBEDDING_DIM}")

    if all(v == 0.0 for v in embedding):
        warnings.append("All-zero embedding — model may have failed silently")

    return warnings


# ── Pipeline: single page ─────────────────────────────────────────────────────
def run_pipeline_single_page(pdf_path: Path) -> dict:
    """
    Run the full pipeline on the FIRST page of a PDF.
    Used for validation before full indexing.

    Returns dict with 'recipe', 'embedding', 'warnings'
    """
    print(f"\n── Running pipeline on: {pdf_path.name} (page 1 only) ──")

    # Stage 1: Extract image
    pdf_stem   = pdf_path.stem
    image_dir  = DATA_IMAGES / pdf_stem
    image_paths = extract_images_from_pdf(pdf_path, image_dir, dpi=DPI)

    if not image_paths:
        print("  [ERROR] No images extracted from PDF")
        return {}

    image_path = image_paths[0]  # Use first page only for validation

    # Stage 2: Gemini Vision extraction
    print(f"  [Transform] Sending {image_path.name} to Gemini Vision...")
    model = genai.Client(api_key=GOOGLE_API_KEY)

    try:
        recipe = extract_recipe_from_image(
            image_path=image_path,
            model=model,
            pdf_name=pdf_path.name,
            page_number=1,
        )
    except json.JSONDecodeError as e:
        print(f"  [ERROR] Gemini returned invalid JSON: {e}")
        print("          Check GOOGLE_API_KEY and try again.")
        return {}
    except Exception as e:
        print(f"  [ERROR] Gemini Vision call failed: {e}")
        return {}

    # Validate extraction
    extraction_warnings = validate_extraction(recipe)
    if extraction_warnings:
        for w in extraction_warnings:
            print(f"  [WARN] {w}")
    else:
        print("  [OK] Extraction quality looks good")

    # Stage 3: Embed
    print(f"  [Embed] Generating embedding for recipe text...")
    embed_model = create_embedding_model()
    embedding   = embed_text(recipe["text"], embed_model)
    recipe["embedding"] = embedding

    # Validate embedding
    embedding_warnings = validate_embedding(embedding)
    if embedding_warnings:
        for w in embedding_warnings:
            print(f"  [WARN] {w}")
    else:
        print(f"  [OK] Embedding generated — dimension: {len(embedding)}")

    # Save processed recipe
    processed_dir = DATA_PROCESSED / pdf_stem
    saved_path    = save_processed_recipe(recipe, processed_dir)
    print(f"  [OK] Saved to {saved_path}")

    return {
        "recipe":    recipe,
        "embedding": embedding,
        "warnings":  extraction_warnings + embedding_warnings,
    }


# ── Print validation report ───────────────────────────────────────────────────
def print_validation_report(result: dict):
    """Display a human-readable summary of pipeline validation."""
    if not result:
        print("\n[FAIL] Pipeline validation failed — see errors above.")
        return

    recipe = result["recipe"]

    print("\n── Validation Report ────────────────────────────────")
    print(f"  Recipe name : {recipe.get('recipe_name', 'NOT FOUND')}")
    print(f"  Creator     : {recipe.get('creator', 'NOT FOUND')}")
    print(f"  Category    : {recipe.get('category', 'NOT FOUND')}")
    print(f"  Ingredients : {recipe.get('all_ingredients_flat', 'NOT FOUND')[:80]}...")
    print(f"  Text length : {len(recipe.get('text', ''))} characters")
    print(f"  Embedding   : {len(result['embedding'])} dimensions")
    print(f"  Warnings    : {len(result['warnings'])}")

    if result["warnings"]:
        print("\n  Warnings:")
        for w in result["warnings"]:
            print(f"    ⚠ {w}")

    print("\n── Embedding text preview ───────────────────────────")
    preview = recipe.get("text", "")[:300]
    print(f"  {preview}...")
    print("─────────────────────────────────────────────────────")

    if not result["warnings"]:
        print("\n[PASS] Pipeline validation successful.")
        print("       Ready to run: python 03_run_indexing.py --test")
    else:
        print("\n[WARN] Pipeline ran with warnings — review before full indexing.")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("\n=== 02_create_pipeline.py — WFPB Recipe Pipeline Validation ===\n")

    # ── Parse arguments ───────────────────────────────────────────────────────
    parser = argparse.ArgumentParser(description="Validate the WFPB RAG indexing pipeline")
    parser.add_argument(
        "--pdf",
        type=str,
        default=None,
        help="PDF filename in data/raw/ to validate (default: first PDF found)",
    )
    args = parser.parse_args()

    # ── Validate environment ──────────────────────────────────────────────────
    if not GOOGLE_API_KEY:
        print("[ERROR] GOOGLE_API_KEY not set in .env")
        sys.exit(1)
    print("[OK] Environment variables loaded.")

    # ── Locate PDF ────────────────────────────────────────────────────────────
    if args.pdf:
        pdf_path = DATA_RAW / args.pdf
        if not pdf_path.exists():
            print(f"[ERROR] PDF not found: {pdf_path}")
            sys.exit(1)
    else:
        pdfs = list(DATA_RAW.glob("*.pdf"))
        if not pdfs:
            print(f"[ERROR] No PDF files found in {DATA_RAW}")
            print("        Add your PDFs to data/raw/ and try again.")
            sys.exit(1)
        pdf_path = sorted(pdfs)[0]
        print(f"[INFO] No --pdf specified. Using: {pdf_path.name}")

    # ── Ensure output directories exist ──────────────────────────────────────
    DATA_IMAGES.mkdir(parents=True, exist_ok=True)
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    # ── Run pipeline on single page ───────────────────────────────────────────
    result = run_pipeline_single_page(pdf_path)
    print_validation_report(result)

    print("\n[DONE] Pipeline validation complete.")
    print("       Next step: python 03_run_indexing.py --test\n")


if __name__ == "__main__":
    main()
