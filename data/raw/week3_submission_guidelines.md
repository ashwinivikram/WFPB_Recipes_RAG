# Week 3 Capstone Submission Guidelines

This document walks you through everything you need to submit for your Week 3 capstone deliverable. Follow it step by step.

---

## Before You Start: Clean Up Your Working Directory

Week 3 generates significant output — RAG results from multiple retrieval techniques, pairwise evaluations, file metadata JSONs, and possibly multiple experimental runs. Before structuring your submission, separate your final work from your scratch work.

### Create an Archive Folder

In your `week-3/` directory, create an `archive/` folder and move anything that isn't part of your final submission into it:

```
week-3/
├── archive/                           # Scratch pad — NOT part of submission
│   ├── old_technique_results/         # Early experiment runs
│   ├── abandoned_narrowing_attempt/   # If you tried narrowing and dropped it
│   └── notes.md                       # Rough notes, scratch thinking
├── ... (your final deliverables)
```

### Update Your .gitingestignore

Before running gitingest, make sure your `.gitingestignore` **inside `week-3/`** includes:

```
# week-3/.gitingestignore
archive/
rag_results/
data_preparation/outputs/
data/raw/
data/processed/
*.parquet
*.csv
*.npy
*.bin
__pycache__/
prequalify.py
week3_submission_guidelines.md
```

This excludes your scratch work, raw RAG result JSONs (200-250KB each — too large), file metadata outputs (500KB+), binary artifacts, and the submission tooling itself. Note that `eval_results/` is **not** excluded — your final pairwise evaluation JSON is kept as grading evidence. Gitingest runs from the `week-3/` subdirectory, so it only captures what's inside that directory.

---

## Your Week 3 Directory Structure

Your capstone repo should now have a `week-3/` directory alongside your existing weeks:

```
my-capstone/
├── week-1/                            # Week 1 (keep as-is)
├── week-2/                            # Week 2 (keep as-is)
└── week-3/
    ├── submission.md                  # Required: your submission document
    ├── docs/
    │   ├── retrieval-analysis.md      # Required: constraint and corpus assessment
    │   ├── retrieval-strategy.md      # Required: hybrid config, reranking config, narrowing decision
    │   └── iteration-log.md           # Required: what you tried, what happened, what you changed
    ├── scripts/                        # Required: your adapted retrieval scripts
    │   ├── [hybrid indexing script]   # Creates collection with dense + sparse vectors
    │   ├── [rag pipeline script]      # RAG pipeline with reranking
    │   └── [optional narrowing scripts]
    ├── evaluations/
    │   ├── eval_results/              # Required: your FINAL pairwise eval JSON (kept for grading)
    │   │   └── pairwise_eval_[techniques].json
    │   ├── week3_comparison.md        # Required: Week 2 vs Week 3 comparison with impact analysis
    │   └── week3_deep_analysis.md     # Required: judge reliability deep-dive
    ├── rag_results/                    # Your RAG output JSONs (excluded from submission)
    ├── data_preparation/               # File metadata outputs (excluded from submission)
    ├── archive/                        # Scratch pad (excluded from submission)
    └── .gitingestignore               # Required: tells gitingest what to skip
```

**Note on scripts:** You don't have to follow the exact script numbering or naming from the course (e.g., `08_index_hybrid.py`). Name them in a way that makes sense for your project. If you have custom retriever components, put them in a `retrievers/` subfolder or wherever makes sense. The requirement is that your retrieval pipeline code is present and functional.

---

## Step 1: Assess Your Retrieval Requirements

Create `week-3/docs/retrieval-analysis.md` with:

### Constraint Assessment

Answer each — your answers drive your architecture decisions:
- **Latency budget:** What response time is acceptable? (< 2s, < 5s, < 10s, doesn't matter)
- **Cost budget:** Per-query cost tolerance? (free tier only, low, moderate, flexible)
- **Accuracy criticality:** How bad is a wrong answer? (annoying, costly, dangerous, depends on use case)
- **Query volume:** Expected queries per day? (< 100, 100-1000, 1000+)

Don't just pick options — explain why. If your corpus is for internal documentation, "annoying" is different from a medical knowledge base where wrong answers are "dangerous."

### Corpus Assessment

Answer each — these determine whether narrowing is worth it:
- **Heterogeneity:** Does your corpus mix different content types? (code + docs + guides, or mostly one type)
- **Domain boundaries:** Are there clear categories or topics? How many?
- **Metadata quality:** Do you have reliable metadata (file types, categories, dates)? Could you generate it?
- **Query patterns:** What types of questions will users ask? Keyword-heavy, conceptual, mixed, code lookups?
- **Cross-document needs:** Do queries often need information from multiple documents?

If your corpus is relatively uniform (all the same type of content), say that. Not every project needs complex retrieval.

### Narrowing Assessment

Based on your answers above, assess whether narrowing makes sense:

| Criterion | Your Answer | Points Toward Narrowing? |
|-----------|-------------|-------------------------|
| Corpus is heterogeneous | | |
| Domain boundaries are clear | | |
| Quality metadata exists or can be generated | | |
| Accuracy is critical | | |
| Latency budget is flexible | | |
| Cost budget is flexible | | |

**4+ yes:** Narrowing might help. Consider metadata filtering or two-stage routing.
**Fewer than 4:** Hybrid + rerank is likely sufficient. Don't add complexity that won't pay off.

Most projects don't need narrowing. If yours doesn't, say so clearly and explain why — that's a valid and important decision.

---

## Step 2: Implement Hybrid Indexing

Create your hybrid indexing script(s) in `week-3/scripts/`.

This script creates a new collection with both dense and sparse vectors:
- **Dense vectors:** Semantic embeddings (e.g., Voyage, BGE, or whatever you used in Week 2)
- **Sparse vectors:** BM25 keyword vectors

Use your optimized chunks from Week 2 (not the naive Week 1 chunks).

After indexing, document in your strategy doc:
- Collection name and vector configuration
- Point count (should match your Week 2 chunk count)
- Both dense and sparse vectors populated
- Any metadata you indexed alongside (file paths, categories, content types)

If your embedding model or chunking changed from Week 2, explain why.

---

## Step 3: Build RAG Pipeline with Reranking

Create your RAG pipeline script(s) in `week-3/scripts/`.

Two-stage retrieval:
- **Stage 1:** Hybrid search (dense + sparse with Reciprocal Rank Fusion), retrieve a larger candidate set (e.g., top 50)
- **Stage 2:** Rerank with a reranking model (e.g., Voyage reranker, Cohere rerank, or another model), return top results to the generator

This is your new baseline. Document your configuration choices.

**You don't have to use the same reranking model from the course.** If you have access to a different reranker or want to try alternatives, that's fine. Document what you used and why.

---

## Step 4: Decide Whether to Narrow

Based on your Step 1 assessment, decide whether to implement narrowing. This is a real engineering decision — document your reasoning.

**Most projects do NOT need narrowing.** Only implement it if:
- Your corpus is heterogeneous AND
- Hybrid + rerank still has reliability issues AND
- You have good metadata or can generate it reliably

If you decide **not** to implement narrowing, that's a perfectly valid outcome. Write a clear justification in your strategy doc.

If you implement narrowing, you have options:
- **Metadata filtering:** Constrain search to specific categories based on query intent. Requires good metadata.
- **Two-stage LLM routing:** LLM selects relevant files/categories first, then searches within those. More expensive, more flexible.
- **Hybrid approach:** Route some query types through narrowing, others straight to hybrid.

If you tried narrowing and it didn't help (or hurt), that's a valuable finding. Document it. If your metadata quality wasn't good enough, explain what happened.

---

## Step 5: Evaluate Against Week 2 Baseline

**Use the same test questions from Week 2** for consistency. This is how you measure real improvement across weeks.

Run your test questions against both your Week 2 pipeline (dense-only with your chunking strategy) and your Week 3 pipeline (hybrid + rerank, and optionally narrowing).

### Run Your Evaluation

Use pairwise evaluation or your adapted evaluation approach. Save the output JSONs in `week-3/eval_results/` (they'll be excluded from the submission by gitingestignore).

**You don't have to use the same evaluation approach or LLM judge from the course.** If you want to use a different model, a different prompt structure, or a different comparison rubric, go for it. What matters is that your evaluation is reliable for your data and your questions.

### Deep Evaluate Your Judge's Output

**This is critical — same as Week 2, but now you have more techniques to compare.** Your final pairwise eval JSON is included in your submission — we can see what the judge ranked. Your job is to show you actually checked whether those rankings hold up.

Create `week-3/evaluations/week3_deep_analysis.md` with:

1. Pick 3-5 questions where the judge had a strong opinion (clear winner between techniques)
2. Read the actual retrieved chunks and generated answers yourself
3. For each: Does the pairwise ranking match what you see? Where does it diverge?
4. Look for cases where the judge missed nuance — e.g., it preferred more contexts but the extra contexts were noise, or it penalized a technique for fewer results when those results were actually more precise

**Tip:** You can use Claude (or another LLM) to help you analyze the raw results — but the quality of that analysis depends entirely on how you prompt it. What you ask the model to compare, how you frame the tradeoffs, what you tell it to look for — that's your judgment call. The prompting intuition you build here is part of what we grade.

```markdown
# Week 3 Deep Analysis — Judge Reliability

## Evaluation Setup
- Judge model: [what you used]
- Eval JSON file: [filename of the pairwise eval you're analyzing]
- Techniques compared: [e.g., Week 2 dense vs Week 3 hybrid+rerank]

## Question-by-Question Spot Check

### Q[X]: [question text]
- **Judge said:** [winner, reasoning summary]
- **My manual read:** [what you actually see in the retrieved chunks]
- **Agreement:** [agree / partially agree / disagree]
- **What the judge missed:** [specific observation]

### Q[Y]: [question text]
...

## Overall Judge Reliability
- Questions checked: [X out of Y]
- Agreement rate: [X/Y]
- Systematic biases found: [e.g., prefers technique with more results regardless of quality]
- Did the judge handle reranked results differently than non-reranked?
- Is this judge reliable enough for your comparison? [yes/no and why]

## Prompting Observations
- What worked when using LLMs to analyze results: [observations]
- What didn't work: [observations]
- How did your evaluation approach evolve from Week 2 to Week 3: [observations]
```

### Write Your Comparison

Create `week-3/evaluations/week3_comparison.md`:

```markdown
## Evaluation Approach
- Judge model: [what you used]
- Evaluation method: [pairwise, per-chunk, etc.]
- If you changed the judge or method from Week 2, why?

## Results

| # | Question | W2: Useful | W2: Relevant | W2: Noise | W3 Hybrid+Rerank: Useful | W3: Relevant | W3: Noise | Winner |
|---|----------|-----------|-------------|----------|--------------------------|-------------|----------|--------|
| 1 | [short] | X/5 | Y/5 | Z | X/5 | Y/5 | Z | [W2/W3/Tie] |
| ... | | | | | | | | |

If you implemented narrowing, add columns for the narrowed pipeline.

### Impact Analysis
- **What did hybrid search add?** Did sparse (BM25) retrieval surface results that dense-only missed?
- **What did reranking add?** How much did reranking change the ordering? Did it promote better results?
- **What did narrowing add (if implemented)?** Did filtering reduce noise? Or did it over-constrain and miss relevant results?

### CAL Tradeoff
- **Cost:** How much more expensive is your Week 3 pipeline vs Week 2? (API calls, reranking costs)
- **Accuracy:** How much better are the results? Is the improvement worth the cost?
- **Latency:** How much slower is the pipeline? Is the latency acceptable?

## Summary
- How many questions did Week 3 win on?
- Where did Week 2 actually do better (if anywhere)?
- What's the biggest single improvement?
- What still isn't working?
```

---

## Step 6: Document Your Retrieval Strategy

Create `week-3/docs/retrieval-strategy.md` with:

### Hybrid Configuration
- Embedding model: [name, dimensions]
- Sparse model: [BM25 or other]
- Fusion method: [RRF or other]
- Initial retrieval count: [e.g., top 50-100 candidates]

### Reranking Configuration
- Reranking model: [name]
- Rerank from [X] candidates to top [Y] results
- Why this model and these settings

### Narrowing Decision
- **Decision:** [Implemented / Tried and dropped / Not needed]
- **Rationale:** [Why, connected to your assessment from Step 1]
- If implemented: approach, configuration, observations, impact
- If tried and dropped: what went wrong, what you learned
- If not needed: why hybrid + rerank is sufficient for your corpus

### Pipeline Architecture Summary
Describe the full retrieval flow, e.g.:
```
Query → Dense embed + Sparse (BM25) → RRF fusion (top 50) → Voyage rerank (top 10) → LLM generation
```
Or if narrowing:
```
Query → LLM file selection (top 8-12 files) → Filtered hybrid search (top 50) → Rerank (top 10) → LLM generation
```

---

## Step 7: Iterate and Log

Create `week-3/docs/iteration-log.md`:

```markdown
## Iteration 1: [What you tried]
- Configuration: [settings]
- Result: [what happened — specific numbers]
- Observation: [what you learned]

## Iteration 2: [What you changed and why]
- Configuration: [settings]
- Result: [what happened]
- Observation: [what you learned]

## Final Configuration
- Pipeline: [full flow description]
- Settings: [final params]
- Why this is your stopping point: [explanation]

## Lessons Learned
- [What surprised you]
- [What you'd do differently]
- [What's the remaining gap for Week 4+]
```

---

## Step 8: Write Your Submission Document

Create `week-3/submission.md` using the exact template below. Every section is required.

```markdown
# Week 3 Capstone Submission

## Student Name(s)
[Full name of each team member, one per line]

## Project Title
[Same project as Week 1-2]

## Progress Recap
- **Week 1 baseline:** [brief summary of where you started]
- **Week 2 improvement:** [what changed with chunking optimization]
- **Key issue going into Week 3:** [what retrieval problem remained]

## Retrieval Assessment Summary
- **Constraint profile:** [latency/cost/accuracy summary in your own words]
- **Corpus characteristics:** [heterogeneity, boundaries, metadata quality]
- **Narrowing decision:** [implemented / tried and dropped / not needed — and why]

## Retrieval Configuration
- **Hybrid search:** [embedding model] (dense) + [sparse model] (sparse), [fusion method]
- **Initial retrieval:** top [X] candidates
- **Reranking:** [model name], rerank to top [Y]
- **Narrowing:** [approach if implemented, or "Not implemented — [reason]"]
- **Collection name:** [name]
- **Total indexed chunks:** [count]

## Evaluation Approach
- **Judge model:** [what you used]
- **Method:** [pairwise, per-chunk, hybrid, etc.]
- **Changes from Week 2 or course default:** [if any, and why]

## Evaluation Summary

| Metric | Week 2 (Dense) | Week 3 (Hybrid + Rerank) | Change |
|--------|----------------|--------------------------|--------|
| Avg usefulness | | | |
| Avg relevance | | | |
| Total noise chunks | | | |
| Questions won | | | |

## Judge Reliability Assessment
- **Spot-checked questions:** [which ones]
- **Agreement with manual review:** [summary]
- **Judge weaknesses found:** [if any]

## Key Observations
- **What impact did hybrid search have?** [Your observations]
- **What impact did reranking have?** [Your observations]
- **What impact did narrowing have (if applicable)?** [Your observations]
- **Where does the system still struggle?** [Your observations]
- **CAL tradeoff:** [Cost vs Accuracy vs Latency — is it worth it?]
- **What would you improve next?** [Your thinking on Week 4+]

## Iteration Summary
- **Total iterations:** [count]
- **Most impactful change:** [what made the biggest difference]
- **Stopping rationale:** [why you stopped where you did]

## Self-Assessment

| Criteria | Score (1-5) | Notes |
|----------|-------------|-------|
| Retrieval analysis depth | | |
| Hybrid implementation quality | | |
| Reranking integration | | |
| Evaluation thoroughness | | |
| Judge reliability check | | |
| Documentation clarity | | |
```

---

## Step 9: Generate and Validate Your Submission

From your capstone repo root (the directory that contains `week-3/`):

```bash
uv run gitingest week-3/ -o firstname_lastname_week3_submission.txt
```

This only captures files inside `week-3/`. Make sure your `archive/`, `rag_results/`, `data_preparation/outputs/`, prequalify script, and guidelines doc are in `.gitingestignore` so they don't bloat the output. Note: `eval_results/` is intentionally **not** excluded — your final pairwise eval JSON stays in the submission.

Then run the prequalify check:

```bash
uv run python week-3/prequalify.py
```

Fix any issues it flags before submitting.

---

## Step 10: Submit

1. Go to the **#capstone** channel on Discord.
2. Upload your `.txt` file and tag **@Nocto**:

```
@Nocto Week 3 submission
```

3. Nocto will validate and confirm receipt. An instructor will review and provide feedback.

---

## Grading Rubric

| Criteria | Weight | What we look for |
|----------|--------|-----------------|
| **Retrieval Analysis** | 15% | Constraints and corpus assessed honestly, narrowing decision justified with reasoning |
| **Hybrid + Rerank Implementation** | 20% | Working hybrid search with reranking, correct configuration, code is present |
| **Evaluation Quality** | 25% | Same test questions reused from Week 2, honest comparison with Week 2, patterns identified |
| **Judge Reliability** | 15% | Evidence of checking the judge's work against raw results, awareness of evaluation limitations |
| **Strategy Documentation** | 10% | Configuration documented, decisions explained, CAL tradeoff discussed |
| **Iteration & Improvement** | 15% | Evidence of systematic experimentation, clear progression from Week 2, stopping point justified |

This is about layering retrieval techniques systematically, measuring their impact honestly, and learning to evaluate your own evaluations. Show your thinking.

---

## Checklist Before Submitting

- [ ] `archive/` folder created for scratch work
- [ ] `.gitingestignore` includes: `archive/`, `rag_results/`, `data_preparation/outputs/`, `*.npy`, `prequalify.py`, `week3_submission_guidelines.md`
- [ ] `week-3/submission.md` is complete (all sections filled)
- [ ] `week-3/docs/retrieval-analysis.md` has constraint, corpus, and narrowing assessments
- [ ] `week-3/docs/retrieval-strategy.md` has hybrid config, reranking config, narrowing decision, pipeline architecture
- [ ] `week-3/docs/iteration-log.md` documents your experiments
- [ ] `week-3/evaluations/eval_results/` has your FINAL pairwise eval JSON (kept for grading)
- [ ] `week-3/evaluations/week3_comparison.md` has per-question comparison, impact analysis, and CAL tradeoff
- [ ] `week-3/evaluations/week3_deep_analysis.md` has judge reliability spot-check with specific questions
- [ ] `week-3/scripts/` contains your retrieval pipeline scripts
- [ ] Same test questions from Week 2 are reused
- [ ] Prequalify script passes with no errors
