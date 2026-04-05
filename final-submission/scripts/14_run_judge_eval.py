"""
14_run_judge_eval.py
--------------------
Week 4 evaluation — Method 2: Decomposed LLM judge.

For each question in evaluations/golden_dataset.json:
  1. Query Week 3 hybrid+rerank system (top-5)
  2. Generate an answer using Gemini
  3. Ask Gemini to score three dimensions separately (decomposed judging):
     • faithfulness       (1-5): Does the answer only use info from retrieved context?
     • answer_relevance   (1-5): Does the answer address what was asked?
     • context_precision  (1-5): Are the retrieved chunks actually relevant to the question?

Saves results to evaluations/method_results/decomposed_results.json

Usage:
    python scripts/14_run_judge_eval.py
    python scripts/14_run_judge_eval.py --dry-run

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

QDRANT_URL     = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

COLLECTION_W3       = "wfpb_recipes_week3_hybrid"
VOYAGE_EMBED_MODEL  = "voyage-3-large"
VOYAGE_RERANK_MODEL = "rerank-2"
SPARSE_MODEL        = "Qdrant/bm25"
RETRIEVE_COUNT      = 50

PROJECT_ROOT  = Path(__file__).parent.parent
GOLDEN_FILE   = PROJECT_ROOT / "evaluations" / "golden_dataset.json"
RESULTS_DIR   = PROJECT_ROOT / "evaluations" / "method_results"
OUTPUT_FILE   = RESULTS_DIR / "decomposed_results.json"


# ── Prompts ───────────────────────────────────────────────────────────────────
ANSWER_PROMPT = """You are a helpful WFPB recipe assistant.

QUESTION: {question}

RETRIEVED CONTEXT:
{context}

Answer the question based only on the provided context. Be concise (under 150 words)."""

FAITHFULNESS_PROMPT = """TASK: Rate the faithfulness of an answer to the provided context.
Faithfulness = the answer ONLY uses information from the context, no hallucinated facts.

QUESTION: {question}

RETRIEVED CONTEXT:
{context}

ANSWER:
{answer}

Rate faithfulness 1-5:
5 = Every claim in the answer is directly supported by the context. No hallucinations.
4 = Almost entirely grounded; one minor unsupported detail.
3 = Mostly grounded but with some information added beyond the context.
2 = Several unsupported claims or important hallucinations.
1 = Answer is mostly or entirely fabricated / contradicts the context.

Respond in JSON: {{"score": <1-5>, "reasoning": "<one sentence>"}}"""

RELEVANCE_PROMPT = """TASK: Rate how well the answer addresses the question asked.

QUESTION: {question}

ANSWER:
{answer}

Rate answer relevance 1-5:
5 = Directly and completely answers what was asked.
4 = Answers the question with minor gaps or tangents.
3 = Partially answers — addresses the question but misses important aspects.
2 = Barely relevant — the answer exists but doesn't address the core question.
1 = Off-topic — the answer does not address the question at all.

Respond in JSON: {{"score": <1-5>, "reasoning": "<one sentence>"}}"""

CONTEXT_PRECISION_PROMPT = """TASK: Rate how precise and relevant the retrieved chunks are to the question.
Context Precision = What fraction of retrieved chunks are genuinely useful for answering this question?

QUESTION: {question}

RETRIEVED CHUNKS:
{chunks_formatted}

Rate context precision 1-5:
5 = All retrieved chunks are highly relevant and useful for answering the question.
4 = Most chunks (≥80%) are relevant; 1-2 minor distractors.
3 = About half the chunks are relevant; noticeable noise.
2 = Few chunks relevant; mostly noise retrieved.
1 = No chunks retrieved are relevant to the question.

Respond in JSON: {{"score": <1-5>, "reasoning": "<one sentence>"}}"""


# ── Helpers ───────────────────────────────────────────────────────────────────
def search_hybrid(query, qdrant, vo, sparse_model, top_k=5):
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
        with_vectors=False,
    ).points

    if not candidates:
        return []

    documents = [r.payload.get("text", "") for r in candidates]
    reranked   = vo.rerank(query, documents, model=VOYAGE_RERANK_MODEL, top_k=top_k)

    results = []
    for item in reranked.results:
        candidate = candidates[item.index]
        candidate.score = item.relevance_score
        results.append(candidate)
    return results


def format_context(chunks):
    parts = []
    for i, r in enumerate(chunks, 1):
        name = r.payload.get("recipe_name", "?")
        text = (r.payload.get("text") or "")[:400]
        parts.append(f"[Chunk {i}: {name}]\n{text}")
    return "\n\n".join(parts)


def format_chunks_for_judge(chunks):
    lines = []
    for i, r in enumerate(chunks, 1):
        name    = r.payload.get("recipe_name", "?")
        creator = r.payload.get("creator", "")
        score   = round(r.score, 4)
        text    = (r.payload.get("text") or "")[:200]
        lines.append(f"Chunk {i} (score={score}): {name} by {creator}\nPreview: {text}...")
    return "\n\n".join(lines)


def call_judge_dimension(gemini, prompt: str) -> dict:
    resp = gemini.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )
    try:
        return json.loads(resp.text)
    except Exception:
        import re
        m = re.search(r"\{.*\}", resp.text, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        return {"score": 0, "reasoning": f"Parse error: {resp.text[:200]}"}


# ── Main evaluation ───────────────────────────────────────────────────────────
def run_eval(top_k: int = 5, dry_run: bool = False):
    print("\n=== 14_run_judge_eval.py — Week 4 Decomposed Judge Evaluation ===\n")

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
        print(f"\n[DRY RUN] Would evaluate {len(golden)} questions with 3 judge calls each.")
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
        print(f"── [{qid}] {question}")

        # Retrieve
        chunks = search_hybrid(question, qdrant, vo, sparse_model, top_k=top_k)
        if not chunks:
            print("  [WARN] No chunks returned.\n")
            results.append({
                "id": qid, "question": question, "type": g["type"],
                "faithfulness": 0, "answer_relevance": 0, "context_precision": 0,
                "generated_answer": "", "top_chunks": []
            })
            continue

        chunk_names = [r.payload.get("recipe_name", "?") for r in chunks]
        print(f"  Top chunks: {chunk_names}")

        # Generate answer
        context = format_context(chunks)
        answer_resp = gemini.models.generate_content(
            model="gemini-2.5-flash",
            contents=ANSWER_PROMPT.format(question=question, context=context),
        )
        generated_answer = answer_resp.text.strip()
        time.sleep(0.5)

        # Score faithfulness
        faith = call_judge_dimension(gemini, FAITHFULNESS_PROMPT.format(
            question=question, context=context, answer=generated_answer))
        time.sleep(0.5)

        # Score answer relevance
        relevance = call_judge_dimension(gemini, RELEVANCE_PROMPT.format(
            question=question, answer=generated_answer))
        time.sleep(0.5)

        # Score context precision
        ctx_prec = call_judge_dimension(gemini, CONTEXT_PRECISION_PROMPT.format(
            question=question, chunks_formatted=format_chunks_for_judge(chunks)))
        time.sleep(0.5)

        f_score = faith.get("score", 0)
        r_score = relevance.get("score", 0)
        c_score = ctx_prec.get("score", 0)

        print(f"  faithfulness={f_score}/5  relevance={r_score}/5  ctx_precision={c_score}/5\n")

        results.append({
            "id":                qid,
            "question":          question,
            "type":              g["type"],
            "faithfulness":      f_score,
            "faithfulness_reasoning": faith.get("reasoning", ""),
            "answer_relevance":  r_score,
            "answer_relevance_reasoning": relevance.get("reasoning", ""),
            "context_precision": c_score,
            "context_precision_reasoning": ctx_prec.get("reasoning", ""),
            "avg_score":         round((f_score + r_score + c_score) / 3, 2),
            "generated_answer":  generated_answer,
            "top_chunks":        [
                {"recipe_name": r.payload.get("recipe_name","?"),
                 "creator": r.payload.get("creator",""),
                 "score": round(r.score, 4)}
                for r in chunks
            ],
            "timestamp":         datetime.now().isoformat(),
        })

    # Aggregate
    n = len(results)
    avg_faith = sum(r["faithfulness"]      for r in results) / n
    avg_rel   = sum(r["answer_relevance"]  for r in results) / n
    avg_ctx   = sum(r["context_precision"] for r in results) / n
    avg_all   = (avg_faith + avg_rel + avg_ctx) / 3

    output = {
        "method":      "decomposed_llm_judge",
        "system":      COLLECTION_W3,
        "model":       "gemini-2.5-flash",
        "top_k":       top_k,
        "n_questions": n,
        "summary": {
            "avg_faithfulness":      round(avg_faith, 4),
            "avg_answer_relevance":  round(avg_rel, 4),
            "avg_context_precision": round(avg_ctx, 4),
            "avg_overall":           round(avg_all, 4),
        },
        "results":    results,
        "timestamp":  datetime.now().isoformat(),
    }

    OUTPUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"\n[DONE] Results → {OUTPUT_FILE}")
    print(f"\n┌─ Decomposed Judge Summary ──────────────────┐")
    print(f"│  Avg Faithfulness:        {avg_faith:.2f}/5")
    print(f"│  Avg Answer Relevance:    {avg_rel:.2f}/5")
    print(f"│  Avg Context Precision:   {avg_ctx:.2f}/5")
    print(f"│  Avg Overall:             {avg_all:.2f}/5")
    print(f"└─────────────────────────────────────────────┘")

    print(f"\n{'ID':<5} {'Type':<25} {'Faith':<7} {'Rel':<5} {'CtxP':<6} {'Avg'}")
    print("─" * 70)
    for r in results:
        print(f"{r['id']:<5} {r['type']:<25} {r['faithfulness']:<7} "
              f"{r['answer_relevance']:<5} {r['context_precision']:<6} {r['avg_score']}")


def main():
    parser = argparse.ArgumentParser(description="Run decomposed judge evaluation (Week 4 Method 2)")
    parser.add_argument("--top-k",   type=int, default=5,  help="Chunks to retrieve")
    parser.add_argument("--dry-run", action="store_true",  help="List questions only")
    args = parser.parse_args()
    run_eval(top_k=args.top_k, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
