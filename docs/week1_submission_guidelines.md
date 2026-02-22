# Week 1 Capstone Submission Guidelines

This document walks you through everything you need to submit for your Week 1 capstone deliverable. Follow it step by step.

---

## Your Week 1 Directory Structure

Your capstone repo should have a `week-1/` directory with this structure:

```
my-capstone/
└── week-1/
    ├── submission.md              # Required: your submission document
    ├── docs/
    │   └── scoping.md             # Required: problem scoping (IDENTIFY/QUALIFY/DEFINE/SCOPE)
    ├── scripts/
    │   ├── 01_setup_qdrant.py     # Required: your adapted scripts
    │   ├── 02_create_pipeline.py
    │   ├── 03_run_indexing.py
    │   ├── 04_test_rag_system.py
    │   └── 05_interactive_rag.py
    ├── data/
    │   ├── raw/                   # Your source data (excluded from submission)
    │   ├── processed/             # Cleaned data (excluded from submission)
    │   └── README.md              # Required: data sourcing documentation
    ├── traces/
    │   └── trace.md               # Required: at least 5 traced queries
    ├── analysis/
    │   └── data_quality_notes.md  # Required: corpus analysis findings
    └── .gitingestignore        # Required: tells gitingest what to skip
```

---

## Step 1: Problem Scoping

Create `week-1/docs/scoping.md` with the following sections. Each section is required.

### IDENTIFY

- What specific problem are you solving?
- Who experiences this problem?
- What capability level are you targeting? (L1: FAQ, L2: Document QA, L3: Task copilot, L4: Agentic)

Write a problem statement in one sentence. Not "I want to build a chatbot." Something like: "Engineers on my team spend 30+ minutes searching for integration examples across 200+ pages of API docs."

### QUALIFY

Answer each of these:

- Is the corpus too large for a single context window?
- Does semantic search add value over keyword matching?
- Does source attribution matter?
- Is the content domain-specific or proprietary?

If you answered yes to most, RAG is appropriate. If not, explain why you're still choosing RAG.

### DEFINE

Set initial success targets:

- Accuracy: what percentage of answers should be correct?
- Coverage: what percentage of expected questions should be answerable?
- Latency: what response time is acceptable?

For a Week 1 baseline, 60-70% accuracy and 50% coverage is reasonable. You will improve these in later weeks.

### SCOPE

- How many documents are you indexing?
- What formats (markdown, HTML, PDF, code, etc.)?
- How often does the data change?
- What is the data quality like?
- Who owns the data?

---

## Step 2: Source and Document Your Data

Create `week-1/data/README.md` documenting:

1. **Where the data came from.** URLs, APIs, internal systems, manual collection.
2. **How you extracted it.** Firecrawl, BeautifulSoup, gitingest, API calls, manual download.
3. **What preprocessing you applied.** Noise removal, format normalization, filtering, metadata enrichment.
4. **What you filtered out and why.** Lock files, configs, navigation elements, duplicates, low-quality pages.
5. **Final corpus stats.** Number of documents, total size, format breakdown.

Put your raw data in `week-1/data/raw/` and processed data in `week-1/data/processed/`. These directories are excluded from submission (too large), but the README documents what's in them.

---

## Step 3: Analyze Your Data

Create `week-1/analysis/data_quality_notes.md` with:

### Quantitative

- Total documents and total size
- Document length distribution (shortest, longest, median)
- Format breakdown
- Duplicate count (if any)

### Qualitative

- What topics are well-covered?
- What topics are missing or sparse?
- Quality observations: well-structured vs messy content
- Anything that might affect retrieval (very long docs, very short docs, mixed languages, etc.)

You can use the `data_curation/` scripts from the course to automate parts of this analysis. Adapt `1_analyze_content_quality.py` for your corpus.

---

## Step 4: Build Your Pipeline

Adapt the course scripts for your data. Your `week-1/scripts/` should contain:

| Script | What it does |
|--------|-------------|
| `01_setup_qdrant.py` | Creates your Qdrant collection with the right schema |
| `02_create_pipeline.py` | Defines your indexing pipeline (embedder + writer) |
| `03_run_indexing.py` | Indexes your documents into Qdrant |
| `04_test_rag_system.py` | Runs a test query to verify the pipeline works |
| `05_interactive_rag.py` | Interactive mode for exploring your system |

You can rename or restructure these. The requirement is that your pipeline is functional: you can index documents and run queries against them.

### What to change from the course scripts

At minimum:
- Collection name (your project, not `mcp_phase1_baseline`)
- Data paths (your data, not the MCP docs)
- System prompt (your domain, not MCP)
- Test queries (relevant to your data)

---

## Step 5: Generate Traces

Traces are the most important part of your submission. They show you've actually run the system, observed its behavior, and thought about what's working.

Create `week-1/traces/trace.md` with at least 5 queries. For each query, record:

### Trace format

```markdown
## Query [number]: [your question]

**Question:** [The exact question you asked]

**Retrieved Chunks:**
1. [source_file] (score: X.XXXX) - [first 80 chars of chunk content]
2. [source_file] (score: X.XXXX) - [first 80 chars of chunk content]
3. [source_file] (score: X.XXXX) - [first 80 chars of chunk content]
...

**Generated Answer:**
[The full answer from the LLM]

**Assessment:**
- Retrieval quality: [Good/Partial/Poor] - [why]
- Answer quality: [Good/Partial/Poor] - [why]
- Was the right context retrieved? [yes/no/partially]
- If not, what was missing?
```

### How to generate traces

**Option A: Retrieve-only mode (recommended for inspecting chunks)**

```bash
python week-1/scripts/05_interactive_rag.py --retrieve-only
```

This shows you exactly what chunks the retriever returns without LLM generation. Run your queries, copy the output, and add your assessment.

**Option B: Full RAG mode**

```bash
python week-1/scripts/05_interactive_rag.py
```

This runs the full pipeline. Copy the terminal output (query, retrieved chunks, generated answer) and add your assessment.

### What makes good traces

- Mix of query types: factual, conceptual, how-to, comparison
- At least 1-2 queries where retrieval fails or partially fails
- Honest assessments (not everything should be "Good")
- Observations about patterns: what types of queries work, what types struggle

---

## Step 6: Write Your Submission Document

Create `week-1/submission.md` using the exact template below. This is what gets graded. Every section is required.

```markdown
# Week 1 Capstone Submission

## Student Name(s)
[Full name of each team member, one per line]

## Project Title
[One-line project title]

## Problem Statement
[Your one-sentence problem statement from scoping.md]

## Data Overview
- **Corpus size:** [X documents, Y total size]
- **Data sources:** [Where you got the data]
- **Formats:** [markdown, HTML, PDF, etc.]
- **Domain:** [What the data covers]

## Data Curation Summary
- **Extraction method:** [How you got the data out of its source]
- **Preprocessing steps:** [What you cleaned, normalized, filtered]
- **Key decisions:** [What you chose to include/exclude and why]

## Pipeline Configuration
- **Vector database:** Qdrant
- **Collection name:** [your collection name]
- **Embedding model:** [model name and dimension]
- **Chunk strategy:** [how documents are chunked — for Week 1 this is likely the default splitter]
- **LLM:** [model name]
- **Documents indexed:** [count]

## Trace Summary
[Summarize your 5+ traces. What worked, what didn't, what patterns you noticed.]

| Query | Retrieval | Answer | Notes |
|-------|-----------|--------|-------|
| [query 1 short] | Good/Partial/Poor | Good/Partial/Poor | [brief note] |
| [query 2 short] | Good/Partial/Poor | Good/Partial/Poor | [brief note] |
| ... | ... | ... | ... |

## Observations
- **What types of queries work well?**
  [Your observations]
- **What types of queries struggle?**
  [Your observations]
- **Is the issue retrieval or generation?**
  [Your analysis]
- **What would you improve first?**
  [Your thinking on what to tackle in Week 2]

## Self-Assessment
Rate yourself honestly on each:

| Criteria | Score (1-5) | Notes |
|----------|-------------|-------|
| Problem scoping clarity | | |
| Data sourcing and curation | | |
| Pipeline is functional | | |
| Trace quality and depth | | |
| Observations and analysis | | |
```

---

## Step 7: Prepare Your Gitingest Ignore File

Create a `.gitingestignore` file **inside your `week-1/` directory** (not at the repo root). When you run gitingest on a subdirectory, it only reads ignore files from inside that directory.

This uses the same format as `.gitignore`. Gitingest already ignores common patterns by default (`.env`, `__pycache__`, `*.pyc`, `.venv`, `node_modules`, `.git`, `*.pkl`, build artifacts, images, etc.). You only need to add project-specific exclusions:

```
# week-1/.gitingestignore
data/raw/
data/processed/
*.parquet
*.csv
*.npy
*.bin
```

This ensures your gitingest output contains only code, documentation, traces, and analysis — the parts that matter for grading.

---

## Step 8: Install Gitingest and Generate Your Submission

Gitingest packages your code, docs, and traces into a single text file for submission.

### Install

From your capstone repo root:

```bash
uv add gitingest
```

### Generate your submission file

Run this from your capstone repo root (the directory that contains `week-1/`).

**Naming convention:** `firstname_lastname_week1_submission.txt`

Solo:
```bash
uv run gitingest week-1/ -o shivani_virdi_week1_submission.txt
```

Group (use first names of each member separated by underscores):
```bash
uv run gitingest week-1/ -o alice_bob_week1_submission.txt
```

This produces a `.txt` file in your repo root containing your directory tree followed by every included file's contents. Check the terminal output for file count and token estimate.

---

## Step 9: Run the Pre-Submission Check

Copy the prequalify script from the course repo into your capstone's `week-1/` directory:

```bash
cp /path/to/rag-accelerator-code/capstone/week1_prequalify.py week-1/prequalify.py
```

Then run it from your capstone repo root:

```bash
uv run python week-1/prequalify.py
```

This checks:
- All required files exist
- `submission.md` has all required sections and full student names
- `traces/trace.md` has at least 5 queries
- `.gitingestignore` is present
- Submission .txt follows naming convention and is between 5KB and 1MB
- No raw data files leaked into the submission
- No API keys, tokens, or passwords in the output
- No binary content or oversized files

Fix any issues it flags before submitting.

---

## Step 10: Submit

1. Go to the **#capstone** channel on Discord.

2. Upload your `week-1-submission.txt` file and tag **@Nocto**:

```
@Nocto Week 1 submission
```

3. Nocto will review your submission against the rubric and provide initial feedback. An instructor will review and finalize your grade.

---

## Grading Rubric

Your Week 1 submission is graded on:

| Criteria | Weight | What we look for |
|----------|--------|-----------------|
| **Problem Scoping** | 20% | Specific problem statement, clear IDENTIFY/QUALIFY/DEFINE/SCOPE, appropriate scope for this course |
| **Data Sourcing and Curation** | 20% | Data is sourced and documented, preprocessing steps are clear, decisions are justified |
| **Data Analysis** | 15% | Corpus is analyzed quantitatively and qualitatively, findings are documented |
| **Working Pipeline** | 20% | Pipeline runs, documents are indexed, queries return results |
| **Traces and Observations** | 25% | At least 5 traced queries with honest assessments, patterns identified, retrieval vs generation issues distinguished |

This is not about perfection. It's about demonstrating that you can scope a problem, source and prepare data, build a working baseline, and critically observe its behavior. The baseline is supposed to have issues — that's what Weeks 2-6 are for.

---

## Checklist Before Submitting

- [ ] `week-1/submission.md` is complete (all sections filled)
- [ ] `week-1/docs/scoping.md` has IDENTIFY, QUALIFY, DEFINE, SCOPE
- [ ] `week-1/data/README.md` documents sources, extraction, preprocessing
- [ ] `week-1/analysis/data_quality_notes.md` has quantitative and qualitative findings
- [ ] `week-1/scripts/` contains your adapted pipeline scripts
- [ ] `week-1/traces/trace.md` has at least 5 traced queries with assessments
- [ ] Pipeline is functional (you can run a query and get results)
- [ ] `.gitingestignore` file exists inside `week-1/` with data exclusions
- [ ] `gitingest week-1/ -o week-1-submission.txt` produces a clean output under 1MB
