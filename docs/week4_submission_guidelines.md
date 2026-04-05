# Week 4 Capstone Submission Guidelines

This document walks you through everything you need to submit for your Week 4 capstone deliverable. Follow it step by step.

---

## Before You Start: Clean Up Your Working Directory

Week 4 generates a lot of evaluation output: golden dataset drafts, RAG results from multiple systems, evaluation JSONs from multiple methods, intermediate metric files. Before structuring your submission, separate your final work from your scratch work.

### Create an Archive Folder

In your `week-4/` directory, create an `archive/` folder and move anything that isn't part of your final submission into it:

```
week-4/
├── archive/                           # Scratch pad -- NOT part of submission
│   ├── early_judge_prompts/           # First attempts at judge design
│   ├── old_eval_runs/                 # Evaluation runs you iterated past
│   └── notes.md                       # Rough notes, scratch thinking
├── ... (your final deliverables)
```

### Update Your .gitingestignore

Before running gitingest, make sure your `.gitingestignore` **inside `week-4/`** includes:

```
# week-4/.gitingestignore
archive/
rag_results/
*.pkl
*.npy
*.bin
*.csv
*.parquet
data/raw/
data/processed/
__pycache__/
prequalify.py
week4_submission_guidelines.md
```

This excludes your scratch work, raw RAG result JSONs (200-400KB each), cached embeddings, binary artifacts, and the submission tooling itself. Note that `eval_results/` is **not** excluded -- your final evaluation outputs are kept as grading evidence. Gitingest runs from the `week-4/` subdirectory, so it only captures what's inside that directory.

---

## Your Week 4 Directory Structure

Your capstone repo should now have a `week-4/` directory alongside your existing weeks:

```
my-capstone/
├── week-1/                            # Week 1 (keep as-is)
├── week-2/                            # Week 2 (keep as-is)
├── week-3/                            # Week 3 (keep as-is)
└── week-4/
    ├── submission.md                  # Required: your submission document
    ├── docs/
    │   ├── evaluation-strategy.md     # Required: why these methods, golden dataset approach, judge design
    │   ├── judge-design.md            # Required: your judge rubric, criteria, prompt evolution
    │   └── iteration-log.md           # Required: what you tried, changed, and learned
    ├── scripts/                        # Required: your evaluation pipeline scripts
    │   ├── [evaluation scripts]       # Your adapted evaluation runners
    │   └── [golden dataset scripts]   # Golden dataset builder (if any)
    ├── evaluations/
    │   ├── golden_dataset.json        # Required: 8-15 bootstrapped Q&A pairs with selection rationale
    │   ├── eval_results/              # Required: final eval outputs from each method (kept for grading)
    │   │   ├── [method1_results].json
    │   │   ├── [method2_results].json
    │   │   └── [method3_results].json
    │   ├── week4_comparison.md        # Required: cross-method agreement/disagreement analysis
    │   └── week4_deep_analysis.md     # Required: judge design critique + triangulation findings
    ├── archive/                        # Your scratch pad (excluded from submission)
    └── .gitingestignore               # Required: tells gitingest what to skip
```

**Note on scripts:** You don't have to follow the exact script naming from the course. Name them in a way that makes sense for your project. The requirement is that your evaluation pipeline code is present and functional.

---

## Step 1: Build Your Golden Dataset

Create `week-4/evaluations/golden_dataset.json` with 8-15 bootstrapped Q&A pairs.

This is not a test set you write from scratch. You bootstrap it from your best Week 3 system's actual outputs:

1. Run your best Week 3 pipeline on your test questions
2. For each question, examine the retrieved contexts and generated answer
3. Select and edit the reference answer (ground it in actual contexts, remove hallucinations)
4. Select reference contexts (3-5 most relevant chunks, ordered by relevance)
5. Document your selection rationale for each entry

Each entry should include:
- **Question text** (same questions from Weeks 2-3 for continuity)
- **Reference answer** (grounded, edited, no hallucinations)
- **Reference contexts** (3-5 chunks with metadata, ordered by relevance)
- **Selection rationale** (why these contexts, which system produced them, what you edited)

The quality of your golden dataset directly determines how meaningful your evaluation results are. A sloppy golden dataset produces noise. A carefully curated one reveals real system behavior.

---

## Step 2: Design Your Evaluation Judge

This is the core meta-skill of Week 4. You're not just running evaluations. You're designing the measurement instrument itself.

Create `week-4/docs/judge-design.md` documenting your judge design:

### Metrics Selection

Which metrics are you measuring, and why?

For **answer quality**, consider:
- Faithfulness (are claims grounded in retrieved contexts?)
- Completeness (does the answer cover what the reference covers?)
- Claim-level decomposition vs holistic scoring

For **retrieval quality**, consider:
- Contextual precision (are retrieved contexts relevant? position-weighted?)
- Contextual recall (does the retrieval cover all claims in the reference?)
- Deterministic metrics (P@k, R@k, MRR, NDCG) vs LLM-judged

Don't just list metrics. Explain why each one matters for YOUR corpus and YOUR use case. If you drop a metric, explain why it doesn't apply.

### Judge Rubric / Criteria

Document the actual criteria your judge uses to evaluate. This is the rubric you're giving to the LLM (or computing deterministically):

- What constitutes a "supported" claim? (verbatim quote required? paraphrase OK? threshold?)
- What constitutes a "relevant" context? (semantic threshold? LLM judgment? both?)
- How do you handle partial matches?
- How do you handle ties?

If you adapted the course's decomposed judge, document WHAT you changed and WHY.

### Judge Prompt Evolution

Document how your judge prompt changed across iterations:

```markdown
## Judge v1: [what the initial prompt looked like]
- Result: [what it got wrong]
- Problem: [why it failed -- e.g., grade inflation, missed nuance, too strict]

## Judge v2: [what you changed]
- Result: [what improved, what still failed]
- Delta: [specific score differences on the same questions]

## Judge v3 (final): [what you changed]
- Result: [current behavior]
- Delta: [specific improvements from v2]
```

The delta between runs is the evidence of thoughtful judge design. If your judge worked perfectly on v1, either your corpus is unusually clean or you're not looking closely enough.

---

## Step 3: Run Multiple Evaluation Methods

Run at least two distinct evaluation methods against your golden dataset. The course teaches three:

1. **Decomposed Judge** (answer faithfulness + completeness via claim extraction)
2. **Retrieval Judge** (contextual precision + recall, deterministic + LLM layers)
3. **Semantic Metrics** (P@k, R@k, MRR, NDCG via embedding similarity)

You can also use DeepEval or another framework as one of your methods. What matters is that you have at least two methods that measure different things, so you can triangulate.

Save all evaluation outputs in `week-4/evaluations/eval_results/`. These are grading evidence.

For each method, document:
- What it measures (answer quality? retrieval quality? both?)
- Cost per evaluation run
- Known limitations for your corpus

---

## Step 4: Triangulate Across Methods

Create `week-4/evaluations/week4_comparison.md`:

This is where the meta-skill shows. Don't just report numbers. Find where methods agree and where they disagree, and explain what that means.

```markdown
# Week 4 Cross-Method Comparison

## Methods Used
- Method 1: [name, what it measures, cost]
- Method 2: [name, what it measures, cost]
- Method 3 (if applicable): [name, what it measures, cost]

## Per-Question Results

| # | Question | Method 1 Winner | Method 2 Winner | Method 3 Winner | Agreement? |
|---|----------|-----------------|-----------------|-----------------|------------|
| 1 | [short]  | [technique]     | [technique]     | [technique]     | [Y/N]      |
| ... |        |                 |                 |                 |            |

## Agreement Analysis
- Questions where ALL methods agree: [which ones, what this tells you]
- Questions where methods DISAGREE: [which ones, why they diverge]
- Systematic patterns: [does one method always favor a particular technique? why?]

## Method Reliability Assessment
- Which method is most reliable for YOUR corpus? [with evidence]
- Which method has the most obvious blind spots? [what does it miss?]
- If you could only keep one method, which and why?

## CAL Tradeoff (Evaluation Cost)
- Method 1: [cost/run, latency, value provided]
- Method 2: [cost/run, latency, value provided]
- Is the most expensive method worth the cost difference?

## Triangulation Insight
- What does combining methods reveal that no single method shows?
- Where is your system genuinely strong? (all methods agree it's good)
- Where is your system genuinely weak? (all methods agree it's bad)
- Where is the evaluation itself uncertain? (methods disagree)
```

---

## Step 5: Deep Analysis -- Judge Design Critique

Create `week-4/evaluations/week4_deep_analysis.md`:

This builds on Weeks 2-3's spot-checking but goes deeper. You're not just checking if the judge is right. You're evaluating the evaluation itself.

```markdown
# Week 4 Deep Analysis -- Evaluation Design Critique

## Judge Design Evolution
- Judge v1 prompt: [summary of initial approach]
- What v1 got wrong: [specific examples with question IDs]
- Judge v2 changes: [what you modified and why]
- Delta from v1 to v2: [specific score changes on same questions]
- Judge v3 (final): [if applicable]

## Spot-Check: Cross-Method Disagreements

Pick 3-5 questions where your evaluation methods DISAGREE. For each:

### Q[X]: [question text]
- **Method 1 said:** [result + reasoning]
- **Method 2 said:** [result + reasoning]
- **My manual read:** [what you see in the actual chunks and answers]
- **Which method was right?** [with evidence]
- **Why did the other method get it wrong?** [structural limitation]

## Systematic Biases Found
- Method 1 biases: [e.g., "semantic metrics too strict on paraphrases"]
- Method 2 biases: [e.g., "LLM judge favors longer answers"]
- Judge prompt biases: [e.g., "claim extractor splits compound statements inconsistently"]

## Golden Dataset Quality Assessment
- Did any golden dataset entries cause problems? [wrong reference, missing context]
- How would you improve the golden dataset for the next iteration?

## Structural Limitations
- What can this evaluation NOT measure about your system?
- What would a user experience that your evaluation misses?
- If your evaluation says the system is "good," would you trust it in production? Why or why not?
```

---

## Step 6: Document Your Evaluation Strategy

Create `week-4/docs/evaluation-strategy.md`:

```markdown
# Evaluation Strategy

## Evaluation Methods Selected
- Method 1: [name] -- measures [what], chosen because [why for this corpus]
- Method 2: [name] -- measures [what], chosen because [why for this corpus]
- Method 3: [name] -- measures [what], chosen because [why for this corpus]

## Golden Dataset Methodology
- Source: [which Week 3 pipeline(s) produced the initial answers]
- Size: [X Q&A pairs]
- Selection criteria: [how you chose which contexts to keep]
- Editing approach: [what you changed in the generated answers and why]
- Coverage: [do these questions cover your system's main use cases?]

## Metrics Justification
For each metric measured:
- What it tells you about your system
- What it CANNOT tell you
- Why it matters for your specific use case

## Methods Considered But Not Used
- [Method]: [why you didn't use it -- cost? doesn't apply? redundant?]

## Known Limitations
- What your evaluation can't measure
- What would need to change for production-grade evaluation
```

---

## Step 7: Iterate and Log

Create `week-4/docs/iteration-log.md`:

```markdown
## Iteration 1: [What you tried -- e.g., "Initial judge design with holistic scoring"]
- Configuration: [judge prompt, metrics, threshold]
- Result: [what happened -- scores, patterns, failures]
- Observation: [what you learned about the judge or the evaluation]

## Iteration 2: [What you changed and why -- e.g., "Switched to claim-level decomposition"]
- Configuration: [changes made]
- Result: [what improved, what didn't]
- Delta: [specific score differences from Iteration 1]
- Observation: [what you learned]

## Iteration 3: [What you changed -- e.g., "Added few-shot examples to reduce grade inflation"]
- Configuration: [changes made]
- Result: [what improved]
- Delta: [specific score differences from Iteration 2]
- Observation: [what you learned]

## Final Configuration
- Judge prompt: [version number, key design decisions]
- Metrics: [which ones, thresholds]
- Golden dataset: [size, methodology]
- Why this is your stopping point: [evidence-based]

## Lessons Learned
- What surprised you about evaluation design
- What you'd do differently
- What's the remaining gap for the final capstone
```

---

## Step 8: Write Your Submission Document

Create `week-4/submission.md` using the exact template below. Every section is required.

```markdown
# Week 4 Capstone Submission

## Student Name(s)
[Full name of each team member, one per line]

## Project Title
[Same project as Weeks 1-3]

## Progress Recap
- **Week 1:** [data scoping baseline]
- **Week 2:** [chunking optimization result]
- **Week 3:** [retrieval improvement result]
- **Key question going into Week 4:** [what needed measuring, what was uncertain]

## Golden Dataset Summary
- **Size:** [X Q&A pairs]
- **Source pipeline:** [which Week 3 system(s) bootstrapped from]
- **Selection methodology:** [how you curated entries]
- **Coverage:** [what aspects of your system these questions test]

## Evaluation Methods
- **Method 1:** [name] -- [what it measures, cost/run]
- **Method 2:** [name] -- [what it measures, cost/run]
- **Method 3 (if applicable):** [name] -- [what it measures, cost/run]

## Judge Design Summary
- **Metrics measured:** [faithfulness, completeness, precision, recall, etc.]
- **Judge iterations:** [how many versions, what changed]
- **Key design decision:** [the most important choice you made in judge design]
- **Biggest judge failure you caught:** [what the judge got wrong and how you fixed it]

## Evaluation Results Summary

| Metric | Week 3 Best System | Other System(s) | Delta |
|--------|-------------------|-----------------|-------|
| [metric 1] | | | |
| [metric 2] | | | |
| [metric 3] | | | |

## Triangulation Findings
- **Methods agree on:** [where your system is strong/weak]
- **Methods disagree on:** [where evaluation is uncertain]
- **Most reliable method for your corpus:** [which one and why]
- **Key insight from combining methods:** [what no single method showed alone]

## Judge Design Evolution
- **v1:** [initial approach, what it got wrong]
- **v2:** [what changed, delta in scores]
- **v3 (if applicable):** [what changed, delta in scores]
- **What this taught you:** [meta-lesson about evaluation design]

## Key Observations
- **What did evaluation reveal about your system?** [genuine findings]
- **What's your system's biggest remaining weakness?** [honest assessment]
- **What would you improve in the evaluation itself?** [evaluation design, not system design]
- **CAL tradeoff for evaluation:** [which methods are worth the cost?]

## Iteration Summary
- **Total iterations:** [count]
- **Most impactful change:** [what made the biggest difference to evaluation quality]
- **Stopping rationale:** [why you stopped where you did]

## Self-Assessment

| Criteria | Score (1-5) | Notes |
|----------|-------------|-------|
| Golden dataset quality | | |
| Metrics selection and justification | | |
| Judge design and iteration | | |
| Triangulation depth | | |
| Evaluation design critique | | |
| Documentation clarity | | |
```

---

## Step 9: Generate and Validate Your Submission

From your capstone repo root (the directory that contains `week-4/`):

```bash
uv run gitingest week-4/ -o firstname_lastname_week4_submission.txt
```

This only captures files inside `week-4/`. Make sure your `archive/`, `rag_results/`, prequalify script, and guidelines doc are in `.gitingestignore` so they don't bloat the output. Note: `eval_results/` is intentionally **not** excluded -- your final evaluation JSONs stay in the submission as grading evidence.

Then run the prequalify check:

```bash
uv run python week-4/prequalify.py
```

Fix any issues it flags before submitting.

---

## Step 10: Submit

1. Go to the **#capstone** channel on Discord.
2. Upload your `.txt` file and tag **@Nocto**:

```
@Nocto Week 4 submission
```

3. Nocto will validate and confirm receipt. An instructor will review and provide feedback.

---

## Grading Rubric

| Criteria | Weight | What we look for |
|----------|--------|-----------------|
| **Golden Dataset Quality** | 15% | Bootstrapped from real system output, selection criteria documented, reference answers grounded in contexts, rationale per entry |
| **Metrics and Judge Design** | 25% | Metrics justified for corpus, judge rubric documented, judge prompt iterated with documented deltas between versions |
| **Evaluation Execution** | 15% | 2-3 methods run cleanly, results saved, cost documented, scripts present |
| **Triangulation and Analysis** | 25% | Cross-method agreement/disagreement analyzed, systematic patterns found, insight from combining methods, CAL tradeoff for evaluation itself |
| **Evaluation Design Critique** | 10% | Spot-checked disagreements with manual reading, structural biases identified, limitations acknowledged, golden dataset quality questioned |
| **Iteration and Progression** | 10% | W3-to-W4 narrative, judge evolved across iterations with evidence, stopping rationale evidence-based |

This is about designing and critiquing measurement systems, not just running them. The judge design evolution (v1 to v2 to v3 with specific deltas) is the strongest signal of understanding. Show your thinking.

---

## Checklist Before Submitting

- [ ] `archive/` folder created for scratch work
- [ ] `.gitingestignore` includes: `archive/`, `rag_results/`, `*.pkl`, `*.npy`, `prequalify.py`, `week4_submission_guidelines.md`
- [ ] `week-4/submission.md` is complete (all sections filled)
- [ ] `week-4/docs/evaluation-strategy.md` has methods selected, golden dataset methodology, metrics justification
- [ ] `week-4/docs/judge-design.md` has metrics, rubric/criteria, prompt evolution with deltas
- [ ] `week-4/docs/iteration-log.md` documents at least 2 iterations with score deltas
- [ ] `week-4/evaluations/golden_dataset.json` has 8-15 Q&A pairs with selection rationale
- [ ] `week-4/evaluations/eval_results/` has final evaluation outputs from each method (kept for grading)
- [ ] `week-4/evaluations/week4_comparison.md` has per-question cross-method comparison and triangulation
- [ ] `week-4/evaluations/week4_deep_analysis.md` has judge evolution deltas, spot-checked disagreements, structural biases
- [ ] `week-4/scripts/` contains your evaluation pipeline scripts
- [ ] Same test questions from Weeks 2-3 are reused
- [ ] Prequalify script passes with no errors
