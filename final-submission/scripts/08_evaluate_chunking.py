"""
08_evaluate_chunking.py
-----------------------
Week 2 evaluation: compare mcp_phase1_baseline (Week 1 naive) vs
wfpb_recipes_week2 (Week 2 with sub-recipe splitting) using an LLM judge.

For each test question:
  1. Query both Qdrant collections (top-5 chunks each)
  2. Record retrieved chunk names and scores
  3. Ask Gemini to act as LLM judge and rate:
       - signal_pct: % of retrieved chunks that are actually relevant
       - usefulness:  1-5 scale (can the user answer their question from this?)
       - winner:      "week1", "week2", or "tie"
  4. Save per-question results to evaluations/eval_results/
  5. Print summary comparison table

Usage:
    python scripts/08_evaluate_chunking.py
    python scripts/08_evaluate_chunking.py --top-k 5  # default
    python scripts/08_evaluate_chunking.py --dry-run   # print queries only

Author: Ashwini Vikram
Project: WFPB Recipe RAG System — Week 2
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from google import genai

load_dotenv()

QDRANT_URL        = os.getenv("QDRANT_URL")
QDRANT_API_KEY    = os.getenv("QDRANT_API_KEY")
GOOGLE_API_KEY    = os.getenv("GOOGLE_API_KEY")
FASTEMBED_MODEL   = os.getenv("FASTEMBED_MODEL", "BAAI/bge-large-en-v1.5")

COLLECTION_W1     = "mcp_phase1_baseline"
COLLECTION_W2     = "wfpb_recipes_week2"

PROJECT_ROOT      = Path(__file__).parent.parent
QUESTIONS_FILE    = PROJECT_ROOT / "evaluations" / "test_questions.json"
RESULTS_DIR       = PROJECT_ROOT / "evaluations" / "eval_results"


# ── Judge prompt ──────────────────────────────────────────────────────────────
JUDGE_PROMPT = """You are an expert RAG (Retrieval-Augmented Generation) evaluator for a
Whole Food Plant-Based recipe knowledge base.

USER QUESTION:
{question}

RETRIEVED CHUNKS — SYSTEM A (Week 1 naive chunking):
{chunks_w1}

RETRIEVED CHUNKS — SYSTEM B (Week 2 with sub-recipe splitting):
{chunks_w2}

Your task: evaluate retrieval quality for EACH system. Respond in JSON with this exact structure:
{{
  "week1": {{
    "signal_pct": <integer 0-100, percentage of retrieved chunks that are relevant to the question>,
    "usefulness": <integer 1-5, can a user fully answer their question from these chunks alone?>,
    "reasoning": "<one sentence explaining your score>"
  }},
  "week2": {{
    "signal_pct": <integer 0-100>,
    "usefulness": <integer 1-5>,
    "reasoning": "<one sentence explaining your score>"
  }},
  "winner": "<'week1', 'week2', or 'tie' — which system retrieved better chunks for this question?>",
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


def embed_query(query: str, embedder: TextEmbedding) -> list[float]:
    return list(embedder.embed([query]))[0].tolist()


def search(query_vec: list[float], client: QdrantClient, collection: str, top_k: int) -> list:
    return client.query_points(
        collection_name=collection,
        query=query_vec,
        limit=top_k,
        with_payload=True,
        with_vectors=False,
    ).points


def format_chunks_for_judge(results: list) -> str:
    lines = []
    for i, r in enumerate(results, 1):
        p = r.payload
        name = p.get("recipe_name", "(no name)")
        creator = p.get("creator", "")
        score = round(r.score, 4)
        chunk_type = p.get("chunk_type", "")
        parent = p.get("parent_recipe_name", "")
        text_preview = (p.get("text") or p.get("instructions") or "")[:250]
        type_str = f" [{chunk_type}]" if chunk_type else ""
        parent_str = f" (from: {parent})" if parent and parent != name else ""
        lines.append(
            f"  Chunk {i} (score={score}): {name}{type_str}{parent_str}\n"
            f"    Creator: {creator}\n"
            f"    Preview: {text_preview[:200]}...\n"
        )
    return "\n".join(lines)


def call_judge(gemini_client, question: str, results_w1: list, results_w2: list) -> dict:
    chunks_w1_str = format_chunks_for_judge(results_w1)
    chunks_w2_str = format_chunks_for_judge(results_w2)
    prompt = JUDGE_PROMPT.format(
        question=question,
        chunks_w1=chunks_w1_str,
        chunks_w2=chunks_w2_str,
    )
    resp = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )
    try:
        return json.loads(resp.text)
    except Exception:
        # fallback: try to extract JSON from text
        import re
        m = re.search(r"\{.*\}", resp.text, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        return {"error": resp.text}


def run_evaluation(top_k: int = 5, dry_run: bool = False):
    print("\n=== 08_evaluate_chunking.py — Week 2 Evaluation ===\n")

    # Load questions
    with open(QUESTIONS_FILE) as f:
        questions = json.load(f)
    print(f"Loaded {len(questions)} test questions.\n")

    if dry_run:
        for q in questions:
            print(f"  [{q['id']}] {q['question']}")
        print("\n[DRY RUN] No queries executed.")
        return

    # Init clients
    print("Initialising clients...")
    qdrant   = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    embedder = TextEmbedding(model_name=FASTEMBED_MODEL)
    gemini   = genai.Client(api_key=GOOGLE_API_KEY)
    print("[OK] Clients ready.\n")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    all_results = []
    summary_rows = []

    for q in questions:
        qid = q["id"]
        question = q["question"]
        print(f"── [{qid}] {question} ──")

        # Embed
        qvec = embed_query(question, embedder)

        # Search both collections
        results_w1 = search(qvec, qdrant, COLLECTION_W1, top_k)
        results_w2 = search(qvec, qdrant, COLLECTION_W2, top_k)

        print(f"  W1 top: {[r.payload.get('recipe_name','?') for r in results_w1[:3]]}")
        print(f"  W2 top: {[r.payload.get('recipe_name','?') for r in results_w2[:3]]}")

        # Judge
        print("  Calling LLM judge...")
        judge = call_judge(gemini, question, results_w1, results_w2)
        time.sleep(1)  # avoid rate limits

        result = {
            "id":           qid,
            "question":     question,
            "type":         q.get("type", ""),
            "hypothesis":   q.get("hypothesis", ""),
            "top_k":        top_k,
            "week1": {
                "chunks": [
                    {
                        "rank":         i + 1,
                        "recipe_name":  r.payload.get("recipe_name", ""),
                        "chunk_type":   r.payload.get("chunk_type", ""),
                        "parent":       r.payload.get("parent_recipe_name", ""),
                        "creator":      r.payload.get("creator", ""),
                        "score":        round(r.score, 4),
                    }
                    for i, r in enumerate(results_w1)
                ],
                "judge": judge.get("week1", {}),
            },
            "week2": {
                "chunks": [
                    {
                        "rank":         i + 1,
                        "recipe_name":  r.payload.get("recipe_name", ""),
                        "chunk_type":   r.payload.get("chunk_type", ""),
                        "parent":       r.payload.get("parent_recipe_name", ""),
                        "creator":      r.payload.get("creator", ""),
                        "score":        round(r.score, 4),
                    }
                    for i, r in enumerate(results_w2)
                ],
                "judge": judge.get("week2", {}),
            },
            "winner":           judge.get("winner", "?"),
            "winner_reasoning": judge.get("winner_reasoning", ""),
            "timestamp":        datetime.now().isoformat(),
        }

        all_results.append(result)

        # Save per-question result
        per_q_file = RESULTS_DIR / f"{qid}_result.json"
        with open(per_q_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        w1j = judge.get("week1", {})
        w2j = judge.get("week2", {})
        print(f"  W1: signal={w1j.get('signal_pct','?')}% useful={w1j.get('usefulness','?')}/5")
        print(f"  W2: signal={w2j.get('signal_pct','?')}% useful={w2j.get('usefulness','?')}/5")
        print(f"  Winner: {judge.get('winner','?')} — {judge.get('winner_reasoning','')[:80]}\n")

        summary_rows.append({
            "id":           qid,
            "type":         q.get("type",""),
            "w1_signal":    w1j.get("signal_pct", 0),
            "w1_useful":    w1j.get("usefulness", 0),
            "w2_signal":    w2j.get("signal_pct", 0),
            "w2_useful":    w2j.get("usefulness", 0),
            "winner":       judge.get("winner", "?"),
        })

    # Save master results file
    master_file = RESULTS_DIR / "all_results.json"
    with open(master_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    # Print summary
    print("\n══ Evaluation Summary ════════════════════════════════")
    print(f"{'ID':<5} {'Type':<25} {'W1 Sig%':>7} {'W1 Use':>6} {'W2 Sig%':>7} {'W2 Use':>6} {'Winner':<8}")
    print("─" * 70)
    w2_wins = w1_wins = ties = 0
    for r in summary_rows:
        print(
            f"{r['id']:<5} {r['type']:<25} {r['w1_signal']:>6}% {r['w1_useful']:>6} "
            f"{r['w2_signal']:>6}% {r['w2_useful']:>6} {r['winner']:<8}"
        )
        if r["winner"] == "week2": w2_wins += 1
        elif r["winner"] == "week1": w1_wins += 1
        else: ties += 1

    n = len(summary_rows)
    avg_w1_sig = sum(r["w1_signal"] for r in summary_rows) / n
    avg_w2_sig = sum(r["w2_signal"] for r in summary_rows) / n
    avg_w1_use = sum(r["w1_useful"] for r in summary_rows) / n
    avg_w2_use = sum(r["w2_useful"] for r in summary_rows) / n

    print("─" * 70)
    print(f"{'AVG':<5} {'':<25} {avg_w1_sig:>6.1f}% {avg_w1_use:>6.2f} {avg_w2_sig:>6.1f}% {avg_w2_use:>6.2f}")
    print(f"\nWeek 2 wins: {w2_wins}  |  Week 1 wins: {w1_wins}  |  Ties: {ties}")
    print(f"[DONE] Results saved to {RESULTS_DIR}\n")


def main():
    parser = argparse.ArgumentParser(description="Week 2 chunking evaluation")
    parser.add_argument("--top-k", type=int, default=5, help="Chunks to retrieve per query")
    parser.add_argument("--dry-run", action="store_true", help="Print questions without running")
    args = parser.parse_args()
    run_evaluation(top_k=args.top_k, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
