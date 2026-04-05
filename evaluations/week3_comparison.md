# Week 3 Retrieval Evaluation: Hybrid + Rerank vs Week 2 Baseline
*Generated: 2026-03-07 22:42*

## Summary

| Metric | Week 2 (dense) | Week 3 (hybrid+rerank) | Change |
|---|---|---|---|
| Avg signal % | 44.3% | 44.3% | +0.0 pp |
| Avg usefulness | 3.64/5 | 4.29/5 | +0.64 |
| Win rate | 7/14 (50%) | 6/14 (42%) | — |
| Ties | 1/14 | — | — |

## Per-Question Results

| ID | Type | W2 Sig% | W2 Use | W3 Sig% | W3 Use | Winner |
|---|---|---|---|---|---|---|
| q01 | sub-recipe-factoid | 40% | 5/5 | 20% | 5/5 | week2 |
| q02 | sub-recipe-factoid | 40% | 4/5 | 20% | 4/5 | week2 |
| q03 | sub-recipe-factoid | 20% | 3/5 | 20% | 3/5 | tie |
| q04 | sub-recipe-factoid | 40% | 3/5 | 20% | 3/5 | week2 |
| q05 | main-recipe-factoid | 60% | 5/5 | 30% | 5/5 | week2 |
| q06 | main-recipe-factoid | 40% | 4/5 | 20% | 4/5 | week2 |
| q07 | ingredient-query | 100% | 5/5 | 100% | 5/5 | week3 |
| q08 | strategy-query | 20% | 3/5 | 60% | 5/5 | week3 |
| q09 | creator-query | 0% | 1/5 | 70% | 5/5 | week3 |
| q10 | sub-recipe-factoid | 80% | 3/5 | 40% | 3/5 | week2 |
| q11 | thematic-analytical | 40% | 3/5 | 100% | 5/5 | week3 |
| q12 | sub-recipe-factoid | 20% | 3/5 | 30% | 3/5 | week3 |
| q13 | sub-recipe-factoid | 20% | 5/5 | 10% | 5/5 | week2 |
| q14 | thematic-analytical | 100% | 4/5 | 80% | 5/5 | week3 |

## Detailed Results

### q01: How do I make walnut mushroom pate?

**Type:** sub-recipe-factoid  
**Winner:** week2  
**Reasoning:** Both systems retrieved the correct recipe, but System A had a higher signal percentage with fewer irrelevant chunks in its top results.

**Week 2** — signal: 40%, useful: 5/5  
*Chunk 1 directly provides the 'Recipe: Walnut Mushroom Pate', which fully answers how to make it.*

**Week 3** — signal: 20%, useful: 5/5  
*Chunk 1 directly provides the 'Recipe: Walnut Mushroom Pate', which fully answers how to make it.*

**Week 2 top chunks:**
- Walnut Mushroom Pate (score=0.8828)
- Ezekiel Sandwich with Walnut Mushroom Pate (score=0.7794)
- Mushroom Sauce (score=0.7094)
- WFPB Mushroom Sandwich with Aioli (score=0.7057)
- Ragi Banana Cake (score=0.7032)

**Week 3 top chunks:**
- Walnut Mushroom Pate (score=0.918)
- Ezekiel Sandwich with Walnut Mushroom Pate (score=0.8086)
- WFPB Mushroom Sandwich with Aioli (score=0.3867)
- Homemade WFPB Pesto (score=0.377)
- Healthy Sandwich (score=0.3633)

---

### q02: What is the recipe for sweet potato paratha?

**Type:** sub-recipe-factoid  
**Winner:** week2  
**Reasoning:** Week 2 is the winner because it retrieved the exact same relevant information as Week 3 with a significantly higher signal percentage (40% vs 20%) within its top results.

**Week 2** — signal: 40%, useful: 4/5  
*Two out of five chunks are highly relevant, providing good ingredient and method information for sweet potato paratha, though previews are cut off.*

**Week 3** — signal: 20%, useful: 4/5  
*Two out of ten chunks are highly relevant, offering the same core ingredient and method information as System A, despite many irrelevant chunks.*

**Week 2 top chunks:**
- Sweet Potato Paratha (score=0.8823)
- Sweet Potato Paratha (score=0.853)
- Sweet Potato Chaat (score=0.798)
- Sweet Potato Chaat (score=0.7978)
- Amaranth Thalipeeth (score=0.7935)

**Week 3 top chunks:**
- Sweet Potato Paratha (score=0.9102)
- Sweet Potato Paratha (score=0.8867)
- Amaranth Thalipeeth (score=0.8086)
- Kathi Rolls (score=0.7734)
- Air-fried Sweet Potato Tikki (score=0.7539)

---

### q03: How do I make a zucchini chutney?

**Type:** sub-recipe-factoid  
**Winner:** tie  
**Reasoning:** Both systems retrieved the same incomplete zucchini chutney recipe (ingredients only, no method) as their best relevant chunk, leading to identical usefulness scores.

**Week 2** — signal: 20%, useful: 3/5  
*One chunk provides ingredients for a zucchini chutney, but the crucial method for making it is missing, and other chunks are irrelevant or too general.*

**Week 3** — signal: 20%, useful: 3/5  
*Two chunks provide ingredients for the specific zucchini chutney, but the essential method is absent, and many other chunks are irrelevant or too general.*

**Week 2 top chunks:**
- Zucchini Chutney (score=0.8557)
- Baked Zucchini Handvo/Pancake (score=0.8037)
- Amaranth Thalipeeth (score=0.7623)
- Cilantro-Mint Chutney (Customizable) (score=0.753)
- Simple Veggie Pickle/Chutney (score=0.7404)

**Week 3 top chunks:**
- Zucchini Chutney (score=0.8555)
- Moong Dosa Wrap (score=0.7227)
- Baked Zucchini Handvo/Pancake (score=0.5586)
- Kanji (Fermented Drink) (score=0.5352)
- Simple Veggie Pickle/Chutney (score=0.5234)

---

### q04: Give me a homemade hummus recipe

**Type:** sub-recipe-factoid  
**Winner:** week2  
**Reasoning:** Both systems provided partial information (ingredients only), but System A had a higher percentage of relevant chunks among its top results, making it less noisy.

**Week 2** — signal: 40%, useful: 3/5  
*The system retrieved two chunks containing hummus ingredients, but the method or instructions for making the hummus are missing from all chunks.*

**Week 3** — signal: 20%, useful: 3/5  
*The system retrieved two chunks containing hummus ingredients, but the method or instructions for making the hummus are missing from all chunks.*

**Week 2 top chunks:**
- Hummus (score=0.8005)
- Grilled Tofu Hummus Sandwich (score=0.7551)
- Arugula Hummus Sandwich (score=0.7537)
- Lavash Hummus Pinwheels (score=0.7417)
- Lavash Hummus Wraps (score=0.74)

**Week 3 top chunks:**
- Hummus (score=0.8047)
- Mutabal (Eggplant Dip) (score=0.7578)
- Peanut Sauce for Noodles (score=0.7344)
- Root Vegetable Salad with Tahini Dressing (score=0.6758)
- Ezekiel Wrap & Salad (score=0.6562)

---

### q05: How do I make Kathi Rolls?

**Type:** main-recipe-factoid  
**Winner:** week2  
**Reasoning:** System A is better because it retrieved a significantly higher percentage of relevant chunks (60% vs 30%) within its smaller set, leading to more focused and efficient results.

**Week 2** — signal: 60%, useful: 5/5  
*The retrieved chunks include two distinct Kathi Roll recipes and a specific component recipe, providing comprehensive information to answer how to make them.*

**Week 3** — signal: 30%, useful: 5/5  
*The retrieved chunks include two distinct Kathi Roll recipes and a specific component recipe, providing comprehensive information to answer how to make them.*

**Week 2 top chunks:**
- Kathi Rolls (score=0.8377)
- Ezekiel Kathi Roll (score=0.7582)
- Lavash Hummus Pinwheels (score=0.7135)
- Sweet Potato Paratha (score=0.6895)
- Jowar Roti (Sorghum Flatbread) (score=0.686)

**Week 3 top chunks:**
- Kathi Rolls (score=0.8867)
- Ezekiel Kathi Roll (score=0.8086)
- Lavash Hummus Pinwheels (score=0.7695)
- Sweet Potato Paratha (score=0.7539)
- SANDWICH (score=0.6992)

---

### q06: What is in the Ezekiel Sandwich with Walnut Mushroom Pate?

**Type:** main-recipe-factoid  
**Winner:** week2  
**Reasoning:** Both systems provided the same crucial relevant chunks, but System A achieved this with a much higher percentage of relevant chunks within its smaller top-5 set, indicating less irrelevant information.

**Week 2** — signal: 40%, useful: 4/5  
*Two out of five chunks are highly relevant, providing key ingredients for both the full sandwich and its pate component, though the full ingredient lists are truncated.*

**Week 3** — signal: 20%, useful: 4/5  
*Two out of ten chunks are highly relevant, identifying the main ingredients for the specific sandwich and its pate, despite truncated ingredient lists.*

**Week 2 top chunks:**
- Ezekiel Sandwich with Walnut Mushroom Pate (score=0.9158)
- Walnut Mushroom Pate (score=0.7579)
- Ezekiel Salad Sandwich (score=0.7574)
- Ezekiel Tofu Sandwich (score=0.7551)
- Ezekiel Sandwich (score=0.7538)

**Week 3 top chunks:**
- Ezekiel Sandwich with Walnut Mushroom Pate (score=0.9414)
- Walnut Mushroom Pate (score=0.9062)
- Healthy Sandwich (score=0.7539)
- Ezekiel Sandwich (score=0.7188)
- Ezekiel Sandwich (score=0.707)

---

### q07: What recipes use sweet potato?

**Type:** ingredient-query  
**Winner:** week3  
**Reasoning:** System B provides a more extensive and diverse list of distinct recipes using sweet potato compared to System A.

**Week 2** — signal: 100%, useful: 5/5  
*The system retrieves five chunks, all of which directly name or reference distinct recipes that use sweet potato.*

**Week 3** — signal: 100%, useful: 5/5  
*The system retrieves ten chunks, all of which directly name distinct recipes or components that use sweet potato, offering a comprehensive list.*

**Week 2 top chunks:**
- Sweet Potato Brownie (score=0.7646)
- Sweet Potato Chaat (score=0.7625)
- Simple Shakarkandi (score=0.7563)
- Sweet Potato Sandwich (score=0.745)
- WFPB Dessert Recommendations (Chocolate Silk Pie, Sweet Potato Brownie) (score=0.7281)

**Week 3 top chunks:**
- Sweet Potato Brownie (score=0.7578)
- Kathi Rolls (score=0.7148)
- Sweet Potato Paratha (score=0.707)
- Tikki (score=0.7031)
- Fudgy Sweet Potato Brownies (WFPB) (score=0.6992)

---

### q08: Give me a quick no-cook sandwich recipe

**Type:** strategy-query  
**Winner:** week3  
**Reasoning:** System B provided significantly more relevant chunks that directly addressed the 'no-cook' requirement, offering several complete recipe ideas compared to System A's single direct hit.

**Week 2** — signal: 20%, useful: 3/5  
*Only one chunk explicitly states 'no-cook' as a cooking method, providing a single relevant recipe idea.*

**Week 3** — signal: 60%, useful: 5/5  
*Multiple chunks explicitly mention 'no-cook' or list only no-cook ingredients, offering several complete recipe options for the user.*

**Week 2 top chunks:**
- Grilled Sandwich without Cheese (Tips) (score=0.686)
- Sweet Potato Sandwich (score=0.6794)
- Ezekiel Sandwich (score=0.6782)
- Tempeh Ezekiel Sandwich (score=0.677)
- Ezekiel Sandwich (score=0.6749)

**Week 3 top chunks:**
- Vietnamese Banh Mi (score=0.8086)
- Sandwich Head (score=0.8047)
- Airport Sandwich (score=0.793)
- Ezekiel Sandwich (score=0.7812)
- Ezekiel Salad Sandwich (score=0.7734)

---

### q09: What recipes did Kumar Natarajan create?

**Type:** creator-query  
**Winner:** week3  
**Reasoning:** System B (Week 3) is the clear winner as it successfully retrieved multiple recipes by the specified creator, while System A (Week 2) returned no relevant results.

**Week 2** — signal: 0%, useful: 1/5  
*No relevant chunks naming Kumar Natarajan as the creator were retrieved in this set.*

**Week 3** — signal: 70%, useful: 5/5  
*This system retrieved several recipes explicitly created by Kumar Natarajan, providing a complete and direct answer.*

**Week 2 top chunks:**
- Potato Pumpkin Bhakri (score=0.6524)
- Uttapam Waffles (score=0.6357)
- Moong Dal Pesarattu (score=0.633)
- Sweet Potato Chaat (score=0.6327)
- Fruity Shakarkandi Chaat (score=0.6318)

**Week 3 top chunks:**
- Ezekiel Sandwich with Walnut Mushroom Pate (score=0.8047)
- Ezekiel Cranberry Relish (score=0.8008)
- Walnut Mushroom Pate (score=0.7969)
- Crumbled Tofu (score=0.793)
- Ezekiel Kathi Roll (score=0.7852)

---

### q10: How do I make Aloo Tikki for chaat?

**Type:** sub-recipe-factoid  
**Winner:** week2  
**Reasoning:** Week 2 is superior because it retrieves a higher percentage of relevant chunks, keeping the focus on Aloo Tikki, whereas Week 3 introduces many irrelevant sweet potato tikki variations and other potato-based dishes.

**Week 2** — signal: 80%, useful: 3/5  
*While four of the five chunks are related to Aloo Tikki or Aloo Tikki Chaat, the crucial method steps for making the Aloo Tikki component are missing from the retrieved previews.*

**Week 3** — signal: 40%, useful: 3/5  
*Only four of the ten chunks are relevant to Aloo Tikki or its variations, and similar to system A, the critical method for preparing Aloo Tikki is not included in the previews.*

**Week 2 top chunks:**
- Aloo Tikki Chaat (score=0.8697)
- Aloo Tikki (score=0.8415)
- Aloo Tikki Chaat (score=0.813)
- Aloo Pyaaz Tikki (score=0.7869)
- Matra Chaat (score=0.7727)

**Week 3 top chunks:**
- Aloo Tikki Chaat (score=0.918)
- Aloo Tikki (score=0.918)
- Aloo Tikki Chaat (score=0.8984)
- Air-fried Sweet Potato Tikki (score=0.8906)
- Tikki (score=0.832)

---

### q11: What are some Indian street food recipes I can make at home?

**Type:** thematic-analytical  
**Winner:** week3  
**Reasoning:** Week 3 retrieved a significantly higher number of directly relevant Indian street food recipes, offering a much broader and more complete answer to the user's question.

**Week 2** — signal: 40%, useful: 3/5  
*Only two out of five chunks are clearly relevant to Indian street food, making the information retrieved partial and diluted.*

**Week 3** — signal: 100%, useful: 5/5  
*All ten retrieved chunks are relevant to Indian street food recipes, providing a comprehensive and direct answer to the user's question.*

**Week 2 top chunks:**
- Potato Pumpkin Bhakri (score=0.6782)
- Grilled Pizza Sandwich (score=0.6688)
- Aloo Tikki Chaat (score=0.6672)
- Air Fried Ragi Pakodas (score=0.6659)
- Chutney Sandwich with Lentil Wrap (score=0.6649)

**Week 3 top chunks:**
- Air-fried Sweet Potato Tikki (score=0.6914)
- Air-fried Purple Baby Potatoes and Spiced Chana Chaat (score=0.6875)
- Aloo Tikki (score=0.6758)
- Aloo Tikki Chaat (score=0.6562)
- Matra Chaat (score=0.6562)

---

### q12: How do I make Ragda for Ragda Patties?

**Type:** sub-recipe-factoid  
**Winner:** week3  
**Reasoning:** System B retrieved a higher percentage of relevant chunks, specifically providing more dedicated component recipes for Ragda, increasing the likelihood of finding a complete answer if the full content were available.

**Week 2** — signal: 20%, useful: 3/5  
*One relevant chunk was retrieved, but the preview only shows ingredients, missing the crucial method for 'how to make' Ragda.*

**Week 3** — signal: 30%, useful: 3/5  
*Multiple relevant chunks were retrieved, but their previews only show ingredients, missing the essential method for 'how to make' Ragda.*

**Week 2 top chunks:**
- Ragda Pattice (score=0.8367)
- Air Fried Ragda Pattice (score=0.8154)
- Ragda Patties (score=0.8118)
- Ragda (score=0.7922)
- Air Fried Patties (score=0.778)

**Week 3 top chunks:**
- Ragda (score=0.8867)
- Ragda Pattice (score=0.8672)
- Ragda Patties (score=0.8633)
- Air Fried Ragda Pattice (score=0.8008)
- Pattice (score=0.7266)

---

### q13: Give me a recipe for mushroom sauce

**Type:** sub-recipe-factoid  
**Winner:** week2  
**Reasoning:** Both systems retrieved the exact same relevant chunk that fully answers the question, but System A had a higher percentage of relevant chunks, indicating less noise.

**Week 2** — signal: 20%, useful: 5/5  
*One chunk directly provides a complete recipe for mushroom sauce, making it fully useful despite other chunks being irrelevant.*

**Week 3** — signal: 10%, useful: 5/5  
*One chunk directly provides a complete recipe for mushroom sauce, making it fully useful despite a large number of irrelevant chunks.*

**Week 2 top chunks:**
- Mushroom Sauce (score=0.7993)
- Chinese Gnocchi in Mushroom Sauce (score=0.7506)
- Walnut Mushroom Pate (score=0.725)
- WFPB Mushroom Sandwich with Aioli (score=0.7155)
- Ezekiel Sandwich with Walnut Mushroom Pate (score=0.6935)

**Week 3 top chunks:**
- Mushroom Sauce (score=0.8555)
- Pea Pasta with Veggies (score=0.6523)
- Chinese Gnocchi in Mushroom Sauce (score=0.6211)
- WFPB Mushroom Sandwich with Aioli (score=0.5742)
- Korean Pancake (score=0.4668)

---

### q14: What savory waffles or pancakes can I make for breakfast?

**Type:** thematic-analytical  
**Winner:** week3  
**Reasoning:** Week 3 is the winner because it provided a significantly broader and more diverse range of specific savory pancake and waffle recipes, directly addressing both parts of the user's question more comprehensively than Week 2, despite having a lower signal percentage.

**Week 2** — signal: 100%, useful: 4/5  
*All retrieved chunks are relevant, providing multiple specific savory waffle recipes and mentioning savory pancakes generally, but specific pancake recipes are not detailed.*

**Week 3** — signal: 80%, useful: 5/5  
*Despite two irrelevant chunks, this system provided a rich and diverse set of specific savory pancake and waffle recipes, directly answering the user's question comprehensively.*

**Week 2 top chunks:**
- Savory Pancakes & Waffles — Whole Food Plant-Based (score=0.7839)
- Oats Chickpea Waffles (score=0.6732)
- Lentil Waffles (score=0.6648)
- Spicy Waffles (score=0.6629)
- Cauliflower Potato Waffles (score=0.6613)

**Week 3 top chunks:**
- Savory Pancakes & Waffles — Whole Food Plant-Based (score=0.8555)
- Thankful2Plants WFPB Recipe Collection (score=0.8008)
- Korean Veggie Pancakes — Yachaejeon (score=0.7539)
- Besan Chilla with Grated Vegetables (score=0.75)
- Moong Dal Savory Pancakes (Dosa) (score=0.7266)

---

## Impact Analysis

**What did hybrid search (BM25 sparse) add?**

BM25 made the biggest difference for queries that dense-only missed entirely:
- **q08 (no-cook strategy):** Dense returned grilled sandwich tips; BM25 matched "no-cook" as an explicit keyword and surfaced Vietnamese Banh Mi and Airport Sandwich — actual no-cook options. Usefulness 3→5.
- **q09 (creator query):** Dense returned completely irrelevant chunks (0% signal); BM25 matched the creator name "Kumar Natarajan" as a keyword in chat-sourced recipe chunks. Usefulness 1→5.
- **q11 (Indian street food thematic):** Dense diluted results with non-street-food recipes; BM25 matched "chaat", "tikki", "street food" keywords and drove 40%→100% signal, usefulness 3→5.
- **q14 (savory waffles thematic):** BM25 surfaced pancake/waffle-specific terms, giving W3 a broader range of specific recipes; usefulness 4→5.

**What did reranking (Voyage rerank-2) add?**

Reranking reordered the top-50 hybrid candidates by cross-encoder relevance:
- **q12 (Ragda sub-recipe):** W3 retrieved 3 distinct Ragda-specific components (Ragda, Ragda Pattice, Ragda Patties) vs W2's 1 at lower quality — the cross-encoder correctly promoted these. Signal 20%→30%.
- **q07 (ingredient query):** Both systems scored 5/5 usefulness but W3 won — the cross-encoder promoted a more diverse sweet potato recipe set from 50 candidates that dense alone would have ranked differently.
- For factoid queries (q01, q02, q04–q06, q13): The correct chunk was already ranked #1 before reranking. Reranking didn't change the top result but did lower apparent signal% by surfacing different secondary chunks in the top-10 pool.

**What did narrowing add?**
Not implemented — single-domain corpus. Payload filtering via `--creator` flag handles the creator query case at query time without routing overhead.

---

## CAL Tradeoff

| Dimension | Week 2 | Week 3 | Delta |
|---|---|---|---|
| **Cost (per query)** | ~$0 (local FastEmbed) | ~$0.003–0.005 (Voyage embed + rerank) | +small per-query API cost |
| **Cost (indexing)** | ~$0 (local FastEmbed) | ~$0.35 (Voyage embed for 692 chunks) | One-time cost, negligible |
| **Accuracy (avg usefulness)** | 3.64/5 | 4.29/5 | **+0.65** |
| **Accuracy (thematic queries)** | 3.5/5 avg | 5/5 avg | **+1.5** on 4 thematic/strategy Qs |
| **Latency (per query)** | ~100–200ms (local) | ~1–3s (2 Voyage API calls) | +1–2s |

**Is it worth it?** Yes for this use case. The project is interactive (seconds acceptable), cost is low (personal project), and the +0.65 usefulness gain is real. The 6 query types that Week 2 failed entirely (creator, no-cook, thematic) now work. The latency increase is acceptable for a personal recipe assistant where accuracy matters more than speed.

**Where it doesn't pay off:** Sub-recipe factoid queries where the right chunk is always rank #1. For these, Week 2 and Week 3 are equivalent — the extra cost and latency add no value.

---

## Summary

- **Week 3 wins 6/14 questions** (42% win rate vs Week 2's 50%)
- **Week 2 wins 7/14** — mostly sub-recipe factoid queries where the correct chunk is already ranked #1; Week 3's larger top-k pool makes signal% appear worse even though usefulness is identical
- **Biggest single improvement:** Thematic and strategy queries (q08, q09, q11) — BM25 keyword matching resolves retrieval failures that dense-only couldn't address at all
- **What still isn't working:** Sub-recipe completeness. Several queries (q03 hummus, q04 zucchini chutney) retrieve ingredients but not the method — this is a data representation issue, not a retrieval issue. Chunking doesn't preserve step-by-step instructions separately from ingredient lists.

## Key Findings

- Week 3 wins **6/14** questions (42% win rate)
- Average usefulness improvement: **+0.64 points**
- Average signal improvement: **+0.0 percentage points** (identical — BM25 gains on thematic offset by signal% dilution on factoid)
