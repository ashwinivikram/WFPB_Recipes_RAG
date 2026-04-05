"""
10_evaluate_week3.py
--------------------
Week 3 evaluation: compare wfpb_recipes_week2 (Week 2 dense-only baseline)
vs wfpb_recipes_week3_hybrid (Week 3 hybrid + rerank) using an LLM judge.

For each test question:
  1. Query Week 2 collection: FastEmbed BGE-large, dense-only, top-5
  2. Query Week 3 collection: Voyage dense + BM25 sparse, hybrid top-50 → rerank top-10
  3. Ask Gemini to act as LLM judge and rate both results
  4. Save per-question results to evaluations/eval_results_week3/
  5. Write evaluations/week3_comparison.md

Usage:
    python scripts/10_evaluate_week3.py
    python scripts/10_evaluate_week3.py --top-k-w2 5    # Week 2 retrieve count
    python scripts/10_evaluate_week3.py --top-k-w3 10   # Week 3 rerank top-k
    python scripts/10_evaluate_week3.py --dry-run

Author: Ashwini Vikram
Project: WFPB Recipe RAG System — Week 3
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
from fastembed import TextEmbedding, SparseTextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import SparseVector, Prefetch, FusionQuery, Fusion
from google import genai

load_dotenv()

QDRANT_URL      = os.getenv("QDRANT_URL")
QDRANT_API_KEY  = os.getenv("QDRANT_API_KEY")
VOYAGE_API_KEY  = os.getenv("VOYAGE_API_KEY")
GOOGLE_API_KEY  = os.getenv("GOOGLE_API_KEY")
FASTEMBED_MODEL = os.getenv("FASTEMBED_MODEL", "BAAI/bge-large-en-v1.5")

COLLECTION_W2   = "wfpb_recipes_week2"
COLLECTION_W3   = "wfpb_recipes_week3_hybrid"

VOYAGE_EMBED_MODEL  = "voyage-3-large"
VOYAGE_RERANK_MODEL = "rerank-2"
SPARSE_MODEL        = "Qdrant/bm25"
RETRIEVE_COUNT_W3   = 50

PROJECT_ROOT    = Path(__file__).parent.parent
QUESTIONS_FILE  = PROJECT_ROOT / "evaluations" / "test_questions.json"
RESULTS_DIR     = PROJECT_ROOT / "evaluations" / "eval_results_week3"
COMPARISON_FILE = PROJECT_ROOT / "evaluations" / "week3_comparison.md"


# ── Judge prompt ───────────────────────────────────────────────────────────────
JUDGE_PROMPT = """You are an expert RAG evaluator for a Whole Food Plant-Based recipe knowledge base.

USER QUESTION:
{question}

RETRIEVED CHUNKS — SYSTEM A (Week 2: dense-only BGE embeddings, top-5):
{chunks_w2}

RETRIEVED CHUNKS — SYSTEM B (Week 3: hybrid dense+sparse + Voyage reranking, top-10):
{chunks_w3}

Your task: evaluate retrieval quality for EACH system. Respond in JSON with this exact structure:
{{
  "week2": {{
    "signal_pct": <integer 0-100, percentage of retrieved chunks that are relevant to the question>,
    "usefulness": <integer 1-5, can a user fully answer their question from these chunks alone?>,
    "reasoning": "<one sentence explaining your score>"
  }},
  "week3": {{
    "signal_pct": <integer 0-100>,
    "usefulness": <integer 1-5>,
    "reasoning": "<one sentence explaining your score>"
  }},
  "winner": "<'week2', 'week3', or 'tie' — which system retrieved better chunks for this question?>",
  "winner_reasoning": "<one sentence explaining why one system won or why it's a tie>"
}}

Scoring guide for usefulness:
  5 = All information needed is in the top chunks; user gets a complete, direct answer
  4 = Most information present; minor gaps
  3 = Partial — relevant chunks retrieved but important details missing or diluted
  2 = Barely useful — one marginally relevant chunk retrieved
  1 = Not useful — no relevant chunks retrieved

Be strict. If the question asks for a specific sub-recipe and the chunk contains it
buried inside a larger recipe, score usefulness as 3 or lower.
"""


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


# ── Week 2 search (dense-only, BGE) ───────────────────────────────────────────
def search_w2(query: str, qdrant: QdrantClient, embedder: TextEmbedding, top_k: int) -> list:
    q_vec = list(embedder.embed([query]))[0].tolist()
    return qdrant.query_points(
        collection_name=COLLECTION_W2,
        query=q_vec,
        limit=top_k,
        with_payload=True,
        with_vectors=False,
    ).points


# ── Week 3 search (hybrid + rerank) ───────────────────────────────────────────
def search_w3(
    query: str,
    qdrant: QdrantClient,
    vo: voyageai.Client,
    sparse_model: SparseTextEmbedding,
    top_k: int,
) -> list:
    # Dense embed
    dense_result = vo.embed([query], model=VOYAGE_EMBED_MODEL, input_type="query")
    q_dense = dense_result.embeddings[0]

    # Sparse embed
    q_sparse_raw = list(sparse_model.embed([query]))[0]
    q_sparse = SparseVector(
        indices=q_sparse_raw.indices.tolist(),
        values=q_sparse_raw.values.tolist(),
    )

    # Hybrid search → top 50
    candidates = qdrant.query_points(
        collection_name=COLLECTION_W3,
        prefetch=[
            Prefetch(query=q_sparse, using="sparse", limit=RETRIEVE_COUNT_W3),
            Prefetch(query=q_dense,  using="dense",  limit=RETRIEVE_COUNT_W3),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=RETRIEVE_COUNT_W3,
        with_payload=True,
        with_vectors=False,
    ).points

    if not candidates:
        return []

    # Rerank → top_k
    documents = [r.payload.get("text", "") for r in candidates]
    reranked   = vo.rerank(query, documents, model=VOYAGE_RERANK_MODEL, top_k=top_k)

    top_results = []
    for item in reranked.results:
        candidate = candidates[item.index]
        candidate.score = item.relevance_score
        top_results.append(candidate)

    return top_results


# ── Format for judge ───────────────────────────────────────────────────────────
def format_chunks_for_judge(results: list) -> str:
    lines = []
    for i, r in enumerate(results, 1):
        p = r.payload
        name       = p.get("recipe_name", "(no name)")
        creator    = p.get("creator", "")
        score      = round(r.score, 4)
        chunk_type = p.get("chunk_type", "")
        parent     = p.get("parent_recipe_name", "")
        text_prev  = (p.get("text") or "")[:200]
        type_str   = f" [{chunk_type}]" if chunk_type else ""
        parent_str = f" (from: {parent})" if parent and parent != name else ""
        lines.append(
            f"  Chunk {i} (score={score}): {name}{type_str}{parent_str}\n"
            f"    Creator: {creator}\n"
            f"    Preview: {text_prev}...\n"
        )
    return "\n".join(lines)


# ── LLM judge ─────────────────────────────────────────────────────────────────
def call_judge(gemini_client, question: str, results_w2: list, results_w3: list) -> dict:
    prompt = JUDGE_PROMPT.format(
        question=question,
        chunks_w2=format_chunks_for_judge(results_w2),
        chunks_w3=format_chunks_for_judge(results_w3),
    )
    resp = gemini_client.models.generate_content(
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
        return {"error": resp.text}


# ── Markdown report ────────────────────────────────────────────────────────────
def write_comparison_md(all_results: list, summary_rows: list):
    n = len(summary_rows)
    w3_wins = sum(1 for r in summary_rows if r["winner"] == "week3")
    w2_wins = sum(1 for r in summary_rows if r["winner"] == "week2")
    ties    = sum(1 for r in summary_rows if r["winner"] == "tie")

    avg_w2_sig = sum(r["w2_signal"] for r in summary_rows) / n
    avg_w3_sig = sum(r["w3_signal"] for r in summary_rows) / n
    avg_w2_use = sum(r["w2_useful"] for r in summary_rows) / n
    avg_w3_use = sum(r["w3_useful"] for r in summary_rows) / n

    lines = [
        "# Week 3 Retrieval Evaluation: Hybrid + Rerank vs Week 2 Baseline\n",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n",
        "## Summary\n\n",
        "| Metric | Week 2 (dense) | Week 3 (hybrid+rerank) | Change |\n",
        "|---|---|---|---|\n",
        f"| Avg signal % | {avg_w2_sig:.1f}% | {avg_w3_sig:.1f}% | {avg_w3_sig - avg_w2_sig:+.1f} pp |\n",
        f"| Avg usefulness | {avg_w2_use:.2f}/5 | {avg_w3_use:.2f}/5 | {avg_w3_use - avg_w2_use:+.2f} |\n",
        f"| Win rate | {w2_wins}/{n} ({100*w2_wins//n}%) | {w3_wins}/{n} ({100*w3_wins//n}%) | — |\n",
        f"| Ties | {ties}/{n} | — | — |\n\n",
        "## Per-Question Results\n\n",
        "| ID | Type | W2 Sig% | W2 Use | W3 Sig% | W3 Use | Winner |\n",
        "|---|---|---|---|---|---|---|\n",
    ]
    for r in summary_rows:
        lines.append(
            f"| {r['id']} | {r['type']} | {r['w2_signal']}% | {r['w2_useful']}/5 "
            f"| {r['w3_signal']}% | {r['w3_useful']}/5 | {r['winner']} |\n"
        )

    lines.append("\n## Detailed Results\n\n")
    for result in all_results:
        lines.append(f"### {result['id']}: {result['question']}\n\n")
        lines.append(f"**Type:** {result['type']}  \n")
        lines.append(f"**Winner:** {result['winner']}  \n")
        lines.append(f"**Reasoning:** {result['winner_reasoning']}\n\n")

        w2j = result["week2"]["judge"]
        w3j = result["week3"]["judge"]
        lines.append(f"**Week 2** — signal: {w2j.get('signal_pct','?')}%, useful: {w2j.get('usefulness','?')}/5  \n")
        lines.append(f"*{w2j.get('reasoning','')}*\n\n")
        lines.append(f"**Week 3** — signal: {w3j.get('signal_pct','?')}%, useful: {w3j.get('usefulness','?')}/5  \n")
        lines.append(f"*{w3j.get('reasoning','')}*\n\n")

        lines.append("**Week 2 top chunks:**\n")
        for c in result["week2"]["chunks"][:5]:
            lines.append(f"- {c['recipe_name']} (score={c['score']})\n")

        lines.append("\n**Week 3 top chunks:**\n")
        for c in result["week3"]["chunks"][:5]:
            lines.append(f"- {c['recipe_name']} (score={c['score']})\n")
        lines.append("\n---\n\n")

    lines.append("## Key Findings\n\n")
    lines.append(f"- Week 3 wins **{w3_wins}/{n}** questions ({100*w3_wins//n}% win rate)\n")
    lines.append(f"- Average usefulness improvement: **{avg_w3_use - avg_w2_use:+.2f} points**\n")
    lines.append(f"- Average signal improvement: **{avg_w3_sig - avg_w2_sig:+.1f} percentage points**\n")

    COMPARISON_FILE.write_text("".join(lines), encoding="utf-8")
    print(f"\n[DONE] Comparison written to {COMPARISON_FILE}")


# ── Main ───────────────────────────────────────────────────────────────────────
def run_evaluation(top_k_w2: int = 5, top_k_w3: int = 10, dry_run: bool = False):
    print("\n=== 10_evaluate_week3.py — Week 3 Evaluation ===\n")

    with open(QUESTIONS_FILE) as f:
        questions = json.load(f)
    print(f"Loaded {len(questions)} test questions.\n")

    if dry_run:
        for q in questions:
            print(f"  [{q['id']}] {q['question']}")
        print("\n[DRY RUN] No queries executed.")
        return

    print("Initialising clients...")
    qdrant       = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    embedder     = TextEmbedding(model_name=FASTEMBED_MODEL)
    vo           = voyageai.Client(api_key=VOYAGE_API_KEY)
    sparse_model = SparseTextEmbedding(SPARSE_MODEL)
    gemini       = genai.Client(api_key=GOOGLE_API_KEY)
    print("[OK] Clients ready.\n")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    all_results  = []
    summary_rows = []

    for q in questions:
        qid      = q["id"]
        question = q["question"]
        print(f"── [{qid}] {question} ──")

        results_w2 = search_w2(question, qdrant, embedder, top_k_w2)
        results_w3 = search_w3(question, qdrant, vo, sparse_model, top_k_w3)

        print(f"  W2 top: {[r.payload.get('recipe_name','?') for r in results_w2[:3]]}")
        print(f"  W3 top: {[r.payload.get('recipe_name','?') for r in results_w3[:3]]}")

        print("  Calling LLM judge...")
        judge = call_judge(gemini, question, results_w2, results_w3)
        time.sleep(1)

        result = {
            "id":           qid,
            "question":     question,
            "type":         q.get("type", ""),
            "hypothesis":   q.get("hypothesis", ""),
            "week2": {
                "chunks": [
                    {
                        "rank":        i + 1,
                        "recipe_name": r.payload.get("recipe_name", ""),
                        "chunk_type":  r.payload.get("chunk_type", ""),
                        "creator":     r.payload.get("creator", ""),
                        "score":       round(r.score, 4),
                    }
                    for i, r in enumerate(results_w2)
                ],
                "judge": judge.get("week2", {}),
            },
            "week3": {
                "chunks": [
                    {
                        "rank":        i + 1,
                        "recipe_name": r.payload.get("recipe_name", ""),
                        "chunk_type":  r.payload.get("chunk_type", ""),
                        "creator":     r.payload.get("creator", ""),
                        "score":       round(r.score, 4),
                    }
                    for i, r in enumerate(results_w3)
                ],
                "judge": judge.get("week3", {}),
            },
            "winner":           judge.get("winner", "?"),
            "winner_reasoning": judge.get("winner_reasoning", ""),
            "timestamp":        datetime.now().isoformat(),
        }

        all_results.append(result)

        per_q_file = RESULTS_DIR / f"{qid}_result.json"
        with open(per_q_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        w2j = judge.get("week2", {})
        w3j = judge.get("week3", {})
        print(f"  W2: signal={w2j.get('signal_pct','?')}% useful={w2j.get('usefulness','?')}/5")
        print(f"  W3: signal={w3j.get('signal_pct','?')}% useful={w3j.get('usefulness','?')}/5")
        print(f"  Winner: {judge.get('winner','?')} — {judge.get('winner_reasoning','')[:80]}\n")

        summary_rows.append({
            "id":        qid,
            "type":      q.get("type", ""),
            "w2_signal": w2j.get("signal_pct", 0),
            "w2_useful": w2j.get("usefulness", 0),
            "w3_signal": w3j.get("signal_pct", 0),
            "w3_useful": w3j.get("usefulness", 0),
            "winner":    judge.get("winner", "?"),
        })

    # Save master results
    master_file = RESULTS_DIR / "all_results.json"
    with open(master_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    # Print summary table
    n = len(summary_rows)
    w3_wins = sum(1 for r in summary_rows if r["winner"] == "week3")
    w2_wins = sum(1 for r in summary_rows if r["winner"] == "week2")
    ties    = sum(1 for r in summary_rows if r["winner"] == "tie")
    avg_w2_sig = sum(r["w2_signal"] for r in summary_rows) / n
    avg_w3_sig = sum(r["w3_signal"] for r in summary_rows) / n
    avg_w2_use = sum(r["w2_useful"] for r in summary_rows) / n
    avg_w3_use = sum(r["w3_useful"] for r in summary_rows) / n

    print("\n══ Week 3 Evaluation Summary ═════════════════════════")
    print(f"{'ID':<5} {'Type':<25} {'W2 Sig%':>7} {'W2 Use':>6} {'W3 Sig%':>7} {'W3 Use':>6} {'Winner':<8}")
    print("─" * 70)
    for r in summary_rows:
        print(
            f"{r['id']:<5} {r['type']:<25} {r['w2_signal']:>6}% {r['w2_useful']:>6} "
            f"{r['w3_signal']:>6}% {r['w3_useful']:>6} {r['winner']:<8}"
        )
    print("─" * 70)
    print(f"{'AVG':<5} {'':<25} {avg_w2_sig:>6.1f}% {avg_w2_use:>6.2f} {avg_w3_sig:>6.1f}% {avg_w3_use:>6.2f}")
    print(f"\nWeek 3 wins: {w3_wins}  |  Week 2 wins: {w2_wins}  |  Ties: {ties}")

    write_comparison_md(all_results, summary_rows)


def main():
    parser = argparse.ArgumentParser(description="Week 3 retrieval evaluation")
    parser.add_argument("--top-k-w2", type=int, default=5,  help="Week 2 retrieve top-k")
    parser.add_argument("--top-k-w3", type=int, default=10, help="Week 3 rerank top-k")
    parser.add_argument("--dry-run",  action="store_true",  help="Print questions only")
    args = parser.parse_args()

    validate_env()
    run_evaluation(top_k_w2=args.top_k_w2, top_k_w3=args.top_k_w3, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
