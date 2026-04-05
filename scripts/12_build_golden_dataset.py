"""
12_build_golden_dataset.py
--------------------------
Build a golden dataset for Week 4 evaluation.

For each question in evaluations/test_questions.json:
  1. Query the Week 3 hybrid+rerank system to get top chunks
  2. Use Gemini to generate a reference answer grounded in the retrieved context
  3. Record the top chunks as reference contexts

Saves the result to evaluations/golden_dataset.json.

Usage:
    python scripts/12_build_golden_dataset.py
    python scripts/12_build_golden_dataset.py --dry-run   # skip API calls
    python scripts/12_build_golden_dataset.py --rebuild   # overwrite existing

Author: Ashwini Vikram
Project: WFPB Recipe RAG System — Week 4
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

import voyageai
from dotenv import load_dotenv
from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import SparseVector, Prefetch, FusionQuery, Fusion
from google import genai

load_dotenv()

QDRANT_URL      = os.getenv("QDRANT_URL")
QDRANT_API_KEY  = os.getenv("QDRANT_API_KEY")
VOYAGE_API_KEY  = os.getenv("VOYAGE_API_KEY")
GOOGLE_API_KEY  = os.getenv("GOOGLE_API_KEY")

COLLECTION_W3       = "wfpb_recipes_week3_hybrid"
VOYAGE_EMBED_MODEL  = "voyage-3-large"
VOYAGE_RERANK_MODEL = "rerank-2"
SPARSE_MODEL        = "Qdrant/bm25"
RETRIEVE_COUNT      = 50   # candidates before rerank
RERANK_TOP_K        = 5    # reference contexts per question

PROJECT_ROOT    = Path(__file__).parent.parent
QUESTIONS_FILE  = PROJECT_ROOT / "evaluations" / "test_questions.json"
OUTPUT_FILE     = PROJECT_ROOT / "evaluations" / "golden_dataset.json"

# Additional question to reach 15 (covers a gap: multi-ingredient combination query)
EXTRA_QUESTIONS = [
    {
        "id": "q15",
        "question": "What recipes can I make with chickpeas and spinach together?",
        "type": "multi-ingredient-query",
        "expected_source": "recipes containing both chickpeas/chana and spinach/leafy greens",
        "hypothesis": "Should retrieve recipes where both ingredients coexist; tests multi-ingredient intersection"
    }
]

ANSWER_PROMPT = """You are an expert on Whole Food Plant-Based (WFPB) cooking.

QUESTION: {question}

RETRIEVED RECIPE INFORMATION:
{context}

Write a concise, helpful reference answer based ONLY on the information provided above.
- If the context contains a specific recipe, include the key ingredients and main steps
- If the context covers multiple recipes, summarize the options
- If the context does not contain enough information to fully answer, say so clearly
- Do not add information not present in the context
- Keep the answer under 200 words

Reference answer:"""


def validate_env():
    missing = []
    if not QDRANT_URL:     missing.append("QDRANT_URL")
    if not QDRANT_API_KEY: missing.append("QDRANT_API_KEY")
    if not VOYAGE_API_KEY: missing.append("VOYAGE_API_KEY")
    if not GOOGLE_API_KEY: missing.append("GOOGLE_API_KEY")
    if missing:
        print(f"[ERROR] Missing environment variables: {', '.join(missing)}")
        sys.exit(1)


def search_hybrid(query: str, qdrant: QdrantClient, vo: voyageai.Client,
                  sparse_model: SparseTextEmbedding, top_k: int = RERANK_TOP_K) -> list:
    """Hybrid search with Voyage reranking — same as Week 3 pipeline."""
    # Dense embed
    dense_result = vo.embed([query], model=VOYAGE_EMBED_MODEL, input_type="query")
    q_dense = dense_result.embeddings[0]

    # Sparse embed
    q_sparse_raw = list(sparse_model.embed([query]))[0]
    q_sparse = SparseVector(
        indices=q_sparse_raw.indices.tolist(),
        values=q_sparse_raw.values.tolist(),
    )

    # Hybrid RRF → 50 candidates
    candidates = qdrant.query_points(
        collection_name=COLLECTION_W3,
        prefetch=[
            Prefetch(query=q_sparse, using="sparse", limit=RETRIEVE_COUNT),
            Prefetch(query=q_dense,  using="dense",  limit=RETRIEVE_COUNT),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=RETRIEVE_COUNT,
        with_payload=True,
        with_vectors=False,
    ).points

    if not candidates:
        return []

    # Rerank → top_k
    documents = [r.payload.get("text", "") for r in candidates]
    reranked   = vo.rerank(query, documents, model=VOYAGE_RERANK_MODEL, top_k=top_k)

    results = []
    for item in reranked.results:
        candidate = candidates[item.index]
        candidate.score = item.relevance_score
        results.append(candidate)

    return results


def generate_reference_answer(question: str, chunks: list, gemini_client) -> str:
    """Use Gemini to generate a reference answer from retrieved chunks."""
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        p = chunk.payload
        name    = p.get("recipe_name", "(no name)")
        creator = p.get("creator", "")
        text    = (p.get("text") or "")[:600]
        context_parts.append(f"[Recipe {i}: {name} by {creator}]\n{text}")
    context = "\n\n".join(context_parts)

    prompt = ANSWER_PROMPT.format(question=question, context=context)
    resp = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return resp.text.strip()


def build_golden_entry(q: dict, chunks: list, reference_answer: str) -> dict:
    """Build a single golden dataset entry."""
    return {
        "id":               q["id"],
        "question":         q["question"],
        "type":             q["type"],
        "expected_source":  q.get("expected_source", ""),
        "reference_answer": reference_answer,
        "reference_chunk_ids": [
            r.payload.get("id", r.id) for r in chunks
        ],
        "reference_chunk_names": [
            r.payload.get("recipe_name", "") for r in chunks
        ],
        "reference_chunks_text": [
            {
                "recipe_name": r.payload.get("recipe_name", ""),
                "creator":     r.payload.get("creator", ""),
                "score":       round(r.score, 4),
                "text":        (r.payload.get("text") or "")[:500],
            }
            for r in chunks
        ],
        "build_timestamp": datetime.now().isoformat(),
    }


def run_build(dry_run: bool = False, rebuild: bool = False):
    print("\n=== 12_build_golden_dataset.py — Week 4 Golden Dataset Builder ===\n")

    # Load existing questions
    with open(QUESTIONS_FILE) as f:
        questions = json.load(f)

    # Add the extra question
    questions = questions + EXTRA_QUESTIONS
    print(f"Loaded {len(questions)} questions ({len(questions) - len(EXTRA_QUESTIONS)} existing + {len(EXTRA_QUESTIONS)} new).\n")

    if OUTPUT_FILE.exists() and not rebuild:
        print(f"[INFO] {OUTPUT_FILE} already exists. Use --rebuild to overwrite.")
        golden = json.loads(OUTPUT_FILE.read_text())
        print(f"[INFO] Existing dataset has {len(golden)} entries.")
        return

    if dry_run:
        for q in questions:
            print(f"  [{q['id']}] ({q['type']}) {q['question']}")
        print(f"\n[DRY RUN] Would build {len(questions)} golden entries.")
        return

    print("Initialising clients...")
    validate_env()
    qdrant       = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    vo           = voyageai.Client(api_key=VOYAGE_API_KEY)
    sparse_model = SparseTextEmbedding(SPARSE_MODEL)
    gemini       = genai.Client(api_key=GOOGLE_API_KEY)
    print("[OK] Clients ready.\n")

    golden_dataset = []

    for q in questions:
        qid      = q["id"]
        question = q["question"]
        print(f"── [{qid}] {question}")

        # Retrieve top-5 reference chunks
        chunks = search_hybrid(question, qdrant, vo, sparse_model, top_k=RERANK_TOP_K)
        chunk_names = [r.payload.get("recipe_name", "?") for r in chunks]
        print(f"  Top chunks: {chunk_names}")

        # Generate reference answer
        print(f"  Generating reference answer...")
        reference_answer = generate_reference_answer(question, chunks, gemini)
        print(f"  Reference answer ({len(reference_answer)} chars): {reference_answer[:120]}...")

        entry = build_golden_entry(q, chunks, reference_answer)
        golden_dataset.append(entry)

        time.sleep(1)  # Rate limit
        print()

    # Save
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(golden_dataset, indent=2, ensure_ascii=False))
    print(f"[DONE] Golden dataset saved → {OUTPUT_FILE}")
    print(f"       {len(golden_dataset)} entries, types: {set(e['type'] for e in golden_dataset)}")


def main():
    parser = argparse.ArgumentParser(description="Build golden dataset for Week 4 evaluation")
    parser.add_argument("--dry-run", action="store_true", help="List questions only, no API calls")
    parser.add_argument("--rebuild", action="store_true", help="Overwrite existing golden dataset")
    args = parser.parse_args()

    run_build(dry_run=args.dry_run, rebuild=args.rebuild)


if __name__ == "__main__":
    main()
