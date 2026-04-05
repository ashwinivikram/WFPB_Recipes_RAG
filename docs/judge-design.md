# Judge Design Document

## Metrics Selection
We evaluate using two primary dimensions:
1. **Answer Quality (LLM Judge):** 
   - *Faithfulness*: Does the LLM output invent ingredients? (Critical for dietary constraints).
   - *Answer Relevance*: Does it successfully provide a methodology, or does it stop abruptly?
2. **Retrieval Quality (Deterministic):**
   - *Contextual Precision*: Did the Hybrid pipeline put the objectively correct recipe vector in the #1 position?

## Judge Rubric / Criteria
The decomposed LLM Judge is given the following rubric:
- **Faithfulness (Pass/Fail):** If the answer recommends an ingredient NOT in the context chunk, fail.
- **Answer Relevance (1-5):** 1 is an unhelpful list format when asked for a method. 5 is a step-by-step resolution.
- **Context Precision (1-5):** How much noise is present alongside the answer.

## Judge Prompt Evolution

## Judge v1: Holistic Prompt
- Result: 9/10 average score.
- Problem: Grade inflation. The system simply matched keywords between the question and the output without analyzing structure.

## Judge v2: Decomposed Traits
- Result: 3.0/5 average score.
- Delta: Massive penalization on questions 03, 04, 12, and 13.
- Reason: The LLM could finally isolate "Relevance" (method instructions) from "Precision" (vocabulary overlap). We proved that our system actually struggles with ingredient-method separation.
