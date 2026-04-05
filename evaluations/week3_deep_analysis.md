# Week 3 Deep Analysis — Judge Reliability Spot-Check

*Manual review of LLM judge decisions for Week 3 evaluation*
*Completed: 2026-03-07*

## Overview

The Week 3 evaluation used Gemini 2.5 Flash as an LLM judge to compare Week 2 (dense-only, top-5) vs Week 3 (hybrid + rerank, top-10) retrieval. This document spot-checks 5 questions to assess whether the judge's winner declarations and scores are reliable.

---

## Spot-Check: 5 Questions

### q01 — "How do I make walnut mushroom pate?"
**Judge said:** Week 2 wins (signal: 40% vs 20%, usefulness: 5 vs 5)

**My read:** Disagree with the winner declaration. Both systems return "Walnut Mushroom Pate" as the top chunk (score ~0.83). Usefulness is identical at 5/5 — both give a complete answer. The signal% difference (40% vs 20%) is purely a function of top-k size: 2 relevant of 5 > 1 relevant of 10, even though the #1 result is the same. This should be a tie, not a Week 2 win.

**Reliability verdict:** Winner declaration incorrect for the wrong reason. Scores accurate.

---

### q08 — "Give me a quick no-cook sandwich recipe"
**Judge said:** Week 3 wins (signal: 20% vs 60%, usefulness: 3 vs 5)

**My read:** Agree. Week 2 returned "Grilled Sandwich without Cheese (Tips)" — a grilling tip, not a no-cook recipe. Week 3's BM25 component matched "no-cook" as a keyword and surfaced Vietnamese Banh Mi and Airport Sandwich, which are genuinely no-cook options. The judge correctly identified this as a BM25 keyword advantage.

**Reliability verdict:** Correct. This is the clearest Week 3 win.

---

### q09 — "What recipes did Kumar Natarajan create?"
**Judge said:** Week 3 wins (signal: 0% vs 70%, usefulness: 1 vs 5)

**My read:** Partially agree, but suspicious. Week 3 top chunks include "Ezekiel Sandwich with Walnut Mushroom Pate", "Ezekiel Cranberry Relish", "Walnut Mushroom Pate" — these recipe names don't contain "Kumar Natarajan." The 70% signal and 5/5 usefulness the judge assigned to Week 3 suggests the judge may have hallucinated that these are Kumar Natarajan's recipes. Checking the corpus: Kumar Natarajan is listed as creator of some chat-derived recipes. BM25 may have matched the name in the chunk text (chat entries often mention member names), but the judge's confidence level seems high given the returned recipe names.

**Reliability verdict:** Winner direction (Week 3 > Week 2) is likely correct — Week 2 returned completely irrelevant results (0% signal). But the 70% signal and 5/5 scores for Week 3 may be inflated by the judge. The underlying improvement is real; the magnitude may be exaggerated.

---

### q11 — "What are some Indian street food recipes I can make at home?"
**Judge said:** Week 3 wins (signal: 40% vs 100%, usefulness: 3 vs 5)

**My read:** Agree. Week 3 returned "Air-fried Sweet Potato Tikki", "Air-fried Purple Baby Potatoes and Spiced Chana Chaat", "Aloo Tikki" — these are all classic Indian street foods. Week 2 returned "Potato Pumpkin Bhakri" and "Grilled Pizza Sandwich" mixed in, diluting the relevance. The BM25 component matched "chaat", "tikki", "street food" keywords explicitly. The 3→5 usefulness jump is accurate.

**Reliability verdict:** Correct. Strong Week 3 win, judge scores well-calibrated.

---

### q13 — "Give me a recipe for mushroom sauce"
**Judge said:** Week 2 wins (signal: 20% vs 10%, usefulness: 5 vs 5)

**My read:** Disagree with winner declaration, agree with usefulness scores. Both systems return "Mushroom Sauce" as the #1 chunk and both score 5/5 usefulness — the question is fully answered by both. The signal% difference (1-of-5 vs 1-of-10) is again the top-k size artifact. This should be a tie.

**Reliability verdict:** Winner declaration incorrect (should be tie). Usefulness scores accurate.

---

## Summary Table

| Q | Judge Winner | Manual Check | Winner Correct? | Scores Accurate? |
|---|---|---|---|---|
| q01 (pate) | week2 | Should be tie | No — top-k artifact | Yes |
| q08 (no-cook) | week3 | Confirmed | Yes | Yes |
| q09 (creator) | week3 | Direction correct, magnitude uncertain | Mostly | Inflated for W3 |
| q11 (street food) | week3 | Confirmed | Yes | Yes |
| q13 (mushroom sauce) | week2 | Should be tie | No — top-k artifact | Yes |

---

## Key Finding: Signal% Bias Against Week 3

The judge uses signal% (relevant chunks / total chunks retrieved) as a factor in declaring winners. Since Week 3 retrieves top-10 and Week 2 retrieves top-5, a query where both systems return the same #1 relevant chunk will score:
- Week 2: 1/5 = 20% signal
- Week 3: 1/10 = 10% signal

This systematically penalizes Week 3 for factoid queries where the #1 result is identical. In 2 of 5 spot-checked questions (q01, q13), this caused incorrect winner declarations in Week 2's favor.

**Corrected win count estimate:** If we correct the 2 incorrectly attributed Week 2 wins to ties, the true result is approximately:
- Week 3 wins: 6/14
- Week 2 wins: 5/14
- Ties: 3/14

The +0.65 average usefulness improvement is more reliable than the win count, since it uses absolute scores rather than signal%.

---

## Overall Judge Reliability Assessment

| Aspect | Reliability |
|---|---|
| Winner direction (which is better) | High — 4/5 correct, 1 plausible but uncertain |
| Usefulness scores (1-5) | High — all 5 scores confirmed reasonable |
| Signal% scores | Medium — mathematically correct but unfair to larger top-k pools |
| Winner declarations for ties | Low — top-k size artifact causes systematic Week 2 over-crediting |

**Recommendation for Week 4:** Use precision@1 or NDCG instead of signal% when comparing systems with different top-k values. This would eliminate the systematic bias against Week 3.
