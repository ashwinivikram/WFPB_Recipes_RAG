# Week 4 Deep Analysis -- Evaluation Design Critique

## Judge Design Evolution
- **v1 (Initial Approach):** Holistic score (1-10) using a basic "rate this answer" prompt. 
- **What v1 got wrong:** Massive grade inflation. The LLM would give 9/10 as long as the recipe mentioned the name of the dish, completely failing to notice if the actual steps were hallucinated or missing.
- **Judge v2 changes:** Decomposed into Faithfulness (binary), Answer Relevance (1-5), and Context Precision (1-5).
- **Delta from v1 to v2:** Answer relevance dropped from 9/10 average to 3.00/5 average. A much more accurate reflection of the truncation issues (like the Zucchini Chutney missing its cooking instructions).

## Spot-Check: Cross-Method Disagreements

### Q[03]: Zucchini chutney
- **Method 1 (Deterministic) said:** 1.0 (Hit@1). The top chunk retrieved exactly matched the golden file chunk ID.
- **Method 2 (Decomposed Judge) said:** Answer Relevance: 1/5. "The answer fails to tell the user how to make the chutney."
- **My manual read:** The retrieved chunk contains only the ingredients for Zucchini Chutney. The cooking steps are stranded in the primary assembly chunk instead of the component chunk.
- **Which method was right?** Method 2 (LLM Judge). Just hitting the component chunk isn't enough if the chunk is semantically incomplete.
- **Why did the other method get it wrong?** Deterministic retrieval cannot measure "semantic completeness". It only confirms if the vector matching fetched the highest correlating text.

### Q[12]: Ragda pattice
- **Method 1 (Deterministic) said:** 1.0 (Hit@1). 
- **Method 2 (Decomposed Judge) said:** Answer Relevance: 1/5.
- **My manual read:** Exact same issue. Ragda pattice ingredient chunk was retrieved, but the cooking steps chunk was missing from the generated context.
- **Which method was right?** Method 2.
- **Why did the other method get it wrong?** Blind ID-matching structural limitation.

## Systematic Biases Found
- **Method 1 biases:** Extreme leniency toward textual overlap based on recipe titles, regardless of the chunk's utility. 
- **Method 2 biases:** Occasional grade deflation when a recipe genuinely doesn't have "cooking steps" (e.g., a "no-cook" strategy recipe where the whole point is throwing things in a bowl). It expected 1-2-3 ordered steps.

## Golden Dataset Quality Assessment
- **Did any golden dataset entries cause problems?** Yes. q08 (Quick no-cook sandwich) reference answer was heavily manipulated by me to be a "step-by-step", forcing the Judge to look for steps that hybrid retrieved chunks didn't possess organically.
- **How would you improve the golden dataset for the next iteration?** Add explicit "Type" labels to the JSON so the Judge dynamically alters its expectations based on if the query asks for ingredients vs method vs analytical strategy.

## Structural Limitations
- **What can this evaluation NOT measure about your system?** Speed to the end user and presentation formatting (like bolding/bullet points).
- **What would a user experience that your evaluation misses?** A user would find the 1/5 answers extremely frustrating because it stops halfway through the recipe.
- **If your evaluation says the system is "good," would you trust it in production?** Not completely. The retrieval mechanism is rock solid (100% Hit@1) but the text extraction boundary is flawed. We must fix the chunk generation script before production.
