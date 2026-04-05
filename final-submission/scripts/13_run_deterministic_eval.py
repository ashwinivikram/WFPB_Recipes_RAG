"""
13_run_deterministic_eval.py
----------------------------
Week 4 evaluation — Method 1: Deterministic semantic metrics.

For each question in evaluations/golden_dataset.json:
  1. Query the Week 3 hybrid+rerank system (top-5)
  2. Compute:
     • context_hit_at_1  — Is the top retrieved chunk in the reference chunk list?
     • context_relevance — Cosine similarity between query embedding and top chunk embedding
     • answer_rouge1_f1  — Token overlap (ROUGE-1 F1) between LLM answer and reference answer

Saves results to evaluations/method_results/deterministic_results.json

Usage:
    python scripts/13_run_deterministic_eval.py
    python scripts/13_run_deterministic_eval.py --dry-run
    python scripts/13_run_deterministic_eval.py --top-k 5

Author: Ashwini Vikram
Project: WFPB Recipe RAG System — Week 4
"""

import os
import sys
import json
import time
import math
import argparse
from pathlib import Path
from datetime import datetime
from collections import Counter

import voyageai
from dotenv import load_dotenv
from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import SparseVector, Prefetch, FusionQuery, Fusion
from google import genai

load_dotenv()

QDRANT_URL     = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

COLLECTION_W3       = "wfpb_recipes_week3_hybrid"
VOYAGE_EMBED_MODEL  = "voyage-3-large"
VOYAGE_RERANK_MODEL = "rerank-2"
SPARSE_MODEL        = "Qdrant/bm25"
RETRIEVE_COUNT      = 50

PROJECT_ROOT    = Path(__file__).parent.parent
GOLDEN_FILE     = PROJECT_ROOT / "evaluations" / "golden_dataset.json"
RESULTS_DIR     = PROJECT_ROOT / "evaluations" / "method_results"
OUTPUT_FILE     = RESULTS_DIR / "deterministic_results.json"


# ── ROUGE-1 F1 (minimal, no dependencies) ────────────────────────────────────
def tokenize(text: str) -> list[str]:
    return text.lower().split()

def rouge1_f1(hypothesis: str, reference: str) -> float:
    hyp_tokens = tokenize(hypothesis)
    ref_tokens = tokenize(reference)
    if not hyp_tokens or not ref_tokens:
        return 0.0
    hyp_counts = Counter(hyp_tokens)
    ref_counts = Counter(ref_tokens)
    overlap = sum((hyp_counts & ref_counts).values())
    precision = overlap / len(hyp_tokens)
    recall    = overlap / len(ref_tokens)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


# ── Cosine similarity ─────────────────────────────────────────────────────────
def cosine_sim(a: list[float], b: list[float]) -> float:
    dot   = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ── Hybrid search (same as Week 3 pipeline) ───────────────────────────────────
def search_hybrid(query: str, qdrant: QdrantClient, vo: voyageai.Client,
                  sparse_model: SparseTextEmbedding, top_k: int) -> tuple[list, list[float]]:
    """Returns (top_results, query_dense_embedding)."""
    dense_result = vo.embed([query], model=VOYAGE_EMBED_MODEL, input_type="query")
    q_dense = dense_result.embeddings[0]

    q_sparse_raw = list(sparse_model.embed([query]))[0]
    q_sparse = SparseVector(
        indices=q_sparse_raw.indices.tolist(),
        values=q_sparse_raw.values.tolist(),
    )

    candidates = qdrant.query_points(
        collection_name=COLLECTION_W3,
        prefetch=[
            Prefetch(query=q_sparse, using="sparse", limit=RETRIEVE_COUNT),
            Prefetch(query=q_dense,  using="dense",  limit=RETRIEVE_COUNT),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=RETRIEVE_COUNT,
        with_payload=True,
        with_vectors=True,
    ).points

    if not candidates:
        return [], q_dense

    documents = [r.payload.get("text", "") for r in candidates]
    reranked   = vo.rerank(query, documents, model=VOYAGE_RERANK_MODEL, top_k=top_k)

    results = []
    for item in reranked.results:
        candidate = candidates[item.index]
        candidate.score = item.relevance_score
        results.append(candidate)

    return results, q_dense


# ── Get top-chunk embedding ───────────────────────────────────────────────────
def get_chunk_embedding(chunk, vo: voyageai.Client) -> list[float]:
    """Embed the top chunk text for cosine similarity computation."""
    text = (chunk.payload.get("text") or "")[:1000]
    result = vo.embed([text], model=VOYAGE_EMBED_MODEL, input_type="document")
    return result.embeddings[0]


# ── Generate answer from retrieved context ────────────────────────────────────
ANSWER_PROMPT = """You are a helpful WFPB recipe assistant.

QUESTION: {question}

RETRIEVED CONTEXT:
{context}

Answer the question based only on the provided context. Be concise (under 150 words)."""

def generate_answer(question: str, chunks: list, gemini_client) -> str:
    context = "\n\n".join(
        f"[{r.payload.get('recipe_name','?')}]: {(r.payload.get('text') or '')[:400]}"
        for r in chunks
    )
    resp = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=ANSWER_PROMPT.format(question=question, context=context),
    )
    return resp.text.strip()


# ── Main evaluation ───────────────────────────────────────────────────────────
def run_eval(top_k: int = 5, dry_run: bool = False):
    print("\n=== 13_run_deterministic_eval.py — Week 4 Deterministic Metrics ===\n")

    if not GOLDEN_FILE.exists():
        print(f"[ERROR] Golden dataset not found: {GOLDEN_FILE}")
        print("Run: python scripts/12_build_golden_dataset.py")
        sys.exit(1)

    with open(GOLDEN_FILE) as f:
        golden = json.load(f)
    print(f"Loaded {len(golden)} golden questions.\n")

    if dry_run:
        for g in golden:
            print(f"  [{g['id']}] ({g['type']}) {g['question']}")
        print(f"\n[DRY RUN] Would evaluate {len(golden)} questions.")
        return

    print("Initialising clients...")
    qdrant       = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    vo           = voyageai.Client(api_key=VOYAGE_API_KEY)
    sparse_model = SparseTextEmbedding(SPARSE_MODEL)
    gemini       = genai.Client(api_key=GOOGLE_API_KEY)
    print("[OK] Clients ready.\n")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    for g in golden:
        qid      = g["id"]
        question = g["question"]
        ref_names = set(g.get("reference_chunk_names", []))
        ref_answer = g.get("reference_answer", "")
        print(f"── [{qid}] {question}")

        # Retrieve
        chunks, q_embed = search_hybrid(question, qdrant, vo, sparse_model, top_k=top_k)

        if not chunks:
            print("  [WARN] No chunks returned.\n")
            results.append({
                "id": qid, "question": question, "type": g["type"],
                "context_hit_at_1": 0, "context_relevance": 0.0, "answer_rouge1_f1": 0.0,
                "top_chunk_name": None, "generated_answer": ""
            })
            continue

        top_chunk = chunks[0]
        top_chunk_name = top_chunk.payload.get("recipe_name", "?")

        # Metric 1: context hit@1
        hit_at_1 = 1 if top_chunk_name in ref_names else 0

        # Metric 2: context relevance (cosine similarity query ↔ top chunk)
        chunk_embed = get_chunk_embedding(top_chunk, vo)
        ctx_relevance = round(cosine_sim(q_embed, chunk_embed), 4)

        # Metric 3: answer ROUGE-1 F1
        print(f"  Generating answer for ROUGE comparison...")
        generated = generate_answer(question, chunks, gemini)
        rouge = round(rouge1_f1(generated, ref_answer), 4)

        print(f"  Top chunk: {top_chunk_name}  hit@1={hit_at_1}  ctx_rel={ctx_relevance:.4f}  rouge1={rouge:.4f}\n")

        results.append({
            "id":                qid,
            "question":          question,
            "type":              g["type"],
            "context_hit_at_1":  hit_at_1,
            "context_relevance": ctx_relevance,
            "answer_rouge1_f1":  rouge,
            "top_chunk_name":    top_chunk_name,
            "reference_chunks":  list(ref_names),
            "generated_answer":  generated,
            "timestamp":         datetime.now().isoformat(),
        })
        time.sleep(1)

    # Aggregate
    n = len(results)
    avg_hit    = sum(r["context_hit_at_1"] for r in results) / n
    avg_rel    = sum(r["context_relevance"] for r in results) / n
    avg_rouge  = sum(r["answer_rouge1_f1"] for r in results) / n

    output = {
        "method":     "deterministic_semantic",
        "system":     COLLECTION_W3,
        "top_k":      top_k,
        "n_questions": n,
        "summary": {
            "avg_context_hit_at_1":  round(avg_hit, 4),
            "avg_context_relevance": round(avg_rel, 4),
            "avg_answer_rouge1_f1":  round(avg_rouge, 4),
        },
        "results":    results,
        "timestamp":  datetime.now().isoformat(),
    }

    OUTPUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"\n[DONE] Results → {OUTPUT_FILE}")
    print(f"\n┌─ Deterministic Summary ─────────────────────┐")
    print(f"│  Avg Context Hit@1:       {avg_hit:.1%}")
    print(f"│  Avg Context Relevance:   {avg_rel:.4f}")
    print(f"│  Avg Answer ROUGE-1 F1:   {avg_rouge:.4f}")
    print(f"└─────────────────────────────────────────────┘")

    # Per-question table
    print(f"\n{'ID':<5} {'Type':<25} {'Hit@1':<7} {'CtxRel':<8} {'ROUGE':<8} {'Top Chunk'}")
    print("─" * 90)
    for r in results:
        print(f"{r['id']:<5} {r['type']:<25} {r['context_hit_at_1']:<7} "
              f"{r['context_relevance']:<8.4f} {r['answer_rouge1_f1']:<8.4f} {r['top_chunk_name']}")


def main():
    parser = argparse.ArgumentParser(description="Run deterministic evaluation (Week 4 Method 1)")
    parser.add_argument("--top-k",   type=int, default=5,  help="Number of chunks to retrieve")
    parser.add_argument("--dry-run", action="store_true",  help="List questions only")
    args = parser.parse_args()
    run_eval(top_k=args.top_k, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
