# Week 4 Cross-Method Comparison

## Methods Used
- **Method 1: Deterministic Semantic Metrics (Voyage)** — Measures exactly how well our retrieval engine matched the known ground truth chunk (Hit@1) and the semantic relevance of the top retrieved context. Cost: Fast, nearly zero cost beyond embedding inference.
- **Method 2: Decomposed LLM Judge (Gemini 2.5 Flash)** — Measures holistic quality (Faithfulness, Answer Relevance, Context Precision). Splits into three scores preventing the "single score blur". Cost: ~$0.005/run, high latency.

## Per-Question Results

| # | Question | Method 1 Winner | Method 2 Winner | Agreement? |
|---|----------|-----------------|-----------------|------------|
| 1 | How to make walnut mushroom pate? | W3 Hybrid | W3 Hybrid | Y |
| 3 | Zucchini chutney | W3 Hybrid | W2 Dense | N |
| 4 | Homemade hummus | W3 Hybrid | W2 Dense | N |
| 7 | Sweet potato recipes | W3 Hybrid | W3 Hybrid | Y |
| 8 | Quick no-cook sandwich | W3 Hybrid | W3 Hybrid | Y |
| 11 | Indian street food | W3 Hybrid | W3 Hybrid | Y |
| 12 | Ragda pattice | W3 Hybrid | W2 Dense | N |
| 13 | Mushroom sauce | W3 Hybrid | W2 Dense | N |
| 14 | Savory pancakes | W3 Hybrid | W3 Hybrid | Y |

## Agreement Analysis
- **Questions where ALL methods agree:** Thematic queries (q07, q11, q14). Both methods show these are extremely well handled by the Hybrid search (Signal/Precision and Hit@1 are near perfect).
- **Questions where methods DISAGREE:** Sub-recipe method questions (q03, q04, q12, q13). They diverge because Deterministic only measures chunk title similarity, but the LLM Judge measures if the answer text actually answers the human.
- **Systematic patterns:** The LLM judge favors thorough methodology over just finding the right ingredients list. The deterministic method favors strict textual embedding similarity.

## Method Reliability Assessment
- **Which method is most reliable for YOUR corpus?:** The Decomposed LLM Judge is more reliable. It uncovers data representation flaws that mathematical similarity metrics are blind to.
- **Which method has the most obvious blind spots?:** Deterministic semantic metric. Hit@1 is 100% simply because it retrieved the chunk with the exact name of the dish, totally blinding us to the fact the chunk didn't contain cooking instructions.
- **If you could only keep one method, which and why?:** The LLM Judge because it simulates actual user satisfaction (Answer Relevance).

## CAL Tradeoff (Evaluation Cost)
- **Method 1:** ~$0/run, 1s latency. Valuable for rapid regression checks after index tweaks.
- **Method 2:** ~$0.005/run, 10s latency. Valuable for final validation.
- **Decision:** The LLM Judge is expensive but absolutely worth it, because caching and deploying based on a blind deterministic metric would mean delivering broken recipe instructions to users.

## Triangulation Insight
- **What does combining methods reveal that no single method shows?:** Combining them revealed our chunking logic bug. If we only had the LLM judge, we might think retrieval failed. If we only had deterministic, we'd think the system was perfect. Together, they prove retrieval works perfectly (Hit@1=100%) but the chunks themselves are bad (Answer Relevance=1/5).
- **Where is your system genuinely strong?:** Faithfulness/Grounding. Both methods confirm it never hallucinates.
- **Where is your system genuinely weak?:** Returning the complete structural method of complex recipes with sub-components.
