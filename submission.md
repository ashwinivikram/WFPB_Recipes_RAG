# Week 4 Capstone Submission

## Student Name(s)
Ashwini Vikram

## Project Title
WFPB Recipe RAG System

## Progress Recap
- **Week 1:** Built naive RAG pipeline with BGE dense embeddings. Identified that sub-recipes inside massive recipe cards diluted the embedding signal.
- **Week 2:** Added regex-based chunking strategy to explicitly break out sub-recipe component chunks from assembly instructions.
- **Week 3:** Upgraded search mechanism to a Hybrid dense+sparse pipeline with Voyage Reranking, massively improving creator/thematic discovery.
- **Key question going into Week 4:** Does the hybrid search actually improve user answers in complex sub-recipe interactions, or just fetch the keyword better?

## Golden Dataset Summary
- **Size:** 15 Q&A pairs
- **Source pipeline:** `wfpb_recipes_week3_hybrid` (Voyage-3-large + BM25) bootstrapped the answers.
- **Selection methodology:** Manually edited Gemini's generated output to be 100% strictly factual to the text. We selected chunks that possessed the direct methodology.
- **Coverage:** Tested 6 query types: sub-recipe factoids, main recipe instructions, multi-ingredient analytical, creator lookups, and wide thematic searches.

## Evaluation Methods
- **Method 1:** Deterministic Semantic Metrics (Voyage cosine similarity) -- Measures retrieval hit precision and exact-chunk matching. Cost: ~$0/run.
- **Method 2:** Decomposed LLM Judge (Gemini) -- Measures holistic text quality across Faithfulness, Relevance, and Precision. Cost: ~$0.005/run.

## Judge Design Summary
- **Metrics measured:** Faithfulness (binary), Answer Relevance (1-5), Context Precision (1-5).
- **Judge iterations:** 2 versions. v1 used holistic 1-10 scoring. v2 decomposed the score into isolated traits.
- **Key design decision:** Decomposing the evaluation logic from "how good is this?" to "does it answer the question completely?" AND "does it invent things?" prevent grade inflation.
- **Biggest judge failure you caught:** The v1 judge gave 9/10 to answers that only listed ingredients but completely excluded cooking instructions. Decomposed v2 penalized this heavily (down to a 1/5 Answer Relevance).

## Evaluation Results Summary

| Metric | Week 3 Best System | Other System(s) (Baseline) | Delta |
|--------|-------------------|-----------------|-------|
| Hit@1 (Determ) | 100% | 100% | 0 |
| Faithfulness (Judge)| 5.0 | 5.0 | 0 |
| Answer Relevance (Judge) | 3.0/5.0 | 3.5/5.0 | -0.5 |

## Triangulation Findings
- **Methods agree on:** Faithfulness (never hallucinated) and Thematic discovery (hybrid perfectly isolates broad topics).
- **Methods disagree on:** The success of sub-recipe queries. Hit@1 claims perfect retrieval, Answer Relevance claims total failure.
- **Most reliable method for your corpus:** LLM Judge (Decomposed). The string-matching deterministic method cannot recognize if instructional sentences were truncated during chunking.
- **Key insight from combining methods:** Retrieval configuration is actually perfect. We just discovered a massive flaw in the Week 2 chunk extraction pipeline that split ingredients completely away from methodologies.

## Judge Design Evolution
- **v1:** Holistic "rate 1-10" approach. Resulted in 9/10 average grade inflation even for terrible answers.
- **v2:** Decomposed approach. Answer relevance dropped from 9/10 to 3.0/5 average.
- **What this taught you:** LLMs are incredibly lazy evaluators if given broad grading rubrics. You must force them to grade singular dimensions to get mathematical value out of them.

## Key Observations
- **What did evaluation reveal about your system?** It finds exactly what you ask for, but gives answers that are half-empty due to structural index isolation.
- **What's your system's biggest remaining weakness?** Method structural completeness (merging sub-recipe assemblies back to their components).
- **What would you improve in the evaluation itself?** Adding an explicit instruction to the Judge to look for "actionable cooking steps, not just lists" for HOW_TO classification prompts.
- **CAL tradeoff for evaluation:** The $0 deterministic checks are great for testing API latencies, but practically useless for telling us if the user is happy. The $0.005 LLM evaluation is essential to trust the pipeline.

## Iteration Summary
- **Total iterations:** 2
- **Most impactful change:** Moving from holistic single-grading to multi-dimensional decomposed grading.
- **Stopping rationale:** Score variance reduced to 0, providing a perfectly reliable mathematical baseline to use to test structural pipeline patches.

## Self-Assessment

| Criteria | Score (1-5) | Notes |
|----------|-------------|-------|
| Golden dataset quality | 4 | Should have manipulated the golden chunks to explicitly include method assemblies. |
| Metrics selection and justification | 5 | Deterministic + Decomposed combinations worked perfectly. |
| Judge design and iteration | 5 | Caught the v1 inflation error immediately. |
| Triangulation depth | 5 | Identified the exact conflict between text ID matching vs semantic fulfillment. |
| Evaluation design critique | 5 | Highlighted exact questions (e.g., Q12) where failure modes clash. |
| Documentation clarity | 4 | |
